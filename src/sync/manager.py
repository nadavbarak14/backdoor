"""
Sync Manager Module

Orchestrates sync operations across adapters, coordinating entity syncers,
deduplication services, and tracking to import data from external sources.

Usage:
    from src.sync.manager import SyncManager
    from src.sync.adapters.base import BaseLeagueAdapter

    # Initialize manager
    manager = SyncManager(
        db=db_session,
        adapters={"winner": winner_adapter},
        config=sync_config
    )

    # Sync a season's games
    sync_log = await manager.sync_season(
        source="winner",
        season_external_id="2024-25",
        include_pbp=True
    )

    # Sync a single game
    sync_log = await manager.sync_game(
        source="winner",
        game_external_id="12345"
    )
"""

import traceback
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.league import Season
from src.models.sync import SyncLog
from src.services.sync_service import SyncLogService
from src.sync.adapters.base import BaseLeagueAdapter
from src.sync.config import SyncConfig
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities import GameSyncer, TeamSyncer
from src.sync.player_info import PlayerInfoService
from src.sync.tracking import SyncTracker
from src.sync.types import RawPlayerInfo, RawTeam


class SyncManager:
    """
    Orchestrates sync operations across adapters.

    Coordinates entity syncers, deduplication services, sync tracking,
    and logging to import data from external sources into the database.

    Attributes:
        db: SQLAlchemy Session for database operations.
        adapters: Dict mapping source names to adapter instances.
        config: SyncConfig controlling which sources are enabled.
        sync_log_service: Service for tracking sync operations.
        tracker: SyncTracker for tracking synced games.
        team_matcher: TeamMatcher for team deduplication.
        player_deduplicator: PlayerDeduplicator for player deduplication.
        game_syncer: GameSyncer for game/boxscore/pbp syncing.
        team_syncer: TeamSyncer for team/roster syncing.

    Example:
        >>> manager = SyncManager(
        ...     db=db_session,
        ...     adapters={"winner": winner_adapter},
        ...     config=sync_config
        ... )
        >>> sync_log = await manager.sync_season("winner", "2024-25")
    """

    def __init__(
        self,
        db: Session,
        adapters: dict[str, BaseLeagueAdapter],
        config: SyncConfig,
        player_info_service: PlayerInfoService | None = None,
    ) -> None:
        """
        Initialize the SyncManager.

        Args:
            db: SQLAlchemy database session.
            adapters: Dict mapping source names to BaseLeagueAdapter instances.
            config: SyncConfig controlling source enablement.
            player_info_service: Optional PlayerInfoService for player info updates.

        Example:
            >>> manager = SyncManager(
            ...     db=db_session,
            ...     adapters={"winner": winner_adapter, "euroleague": euro_adapter},
            ...     config=SyncConfig.from_settings()
            ... )
        """
        self.db = db
        self.adapters = adapters
        self.config = config
        self.player_info_service = player_info_service

        # Initialize services
        self.sync_log_service = SyncLogService(db)
        self.tracker = SyncTracker(db)
        self.team_matcher = TeamMatcher(db)
        self.player_deduplicator = PlayerDeduplicator(db)

        # Initialize entity syncers
        self.game_syncer = GameSyncer(db, self.team_matcher, self.player_deduplicator)
        self.team_syncer = TeamSyncer(db, self.team_matcher, self.player_deduplicator)

    def _get_adapter(self, source: str) -> BaseLeagueAdapter:
        """
        Get adapter for a source, validating it's enabled.

        Args:
            source: The data source name.

        Returns:
            The BaseLeagueAdapter for the source.

        Raises:
            ValueError: If source not found or not enabled.
        """
        if source not in self.adapters:
            raise ValueError(f"Unknown source: {source}")

        if not self.config.is_source_enabled(source):
            raise ValueError(f"Source {source} is not enabled")

        return self.adapters[source]

    async def sync_season(
        self,
        source: str,
        season_external_id: str,
        include_pbp: bool = True,
    ) -> SyncLog:
        """
        Sync all games for a season.

        Fetches the schedule, filters to unsynced final games, and syncs
        each game with box score and optionally play-by-play data.

        Args:
            source: The data source name (e.g., "winner").
            season_external_id: External ID of the season to sync.
            include_pbp: Whether to sync play-by-play data.

        Returns:
            SyncLog with sync operation results.

        Example:
            >>> sync_log = await manager.sync_season(
            ...     source="winner",
            ...     season_external_id="2024-25",
            ...     include_pbp=True
            ... )
            >>> print(f"Synced {sync_log.records_created} games")
        """
        adapter = self._get_adapter(source)

        # Find or create internal season
        season = self._get_or_create_season(source, season_external_id)

        # Start sync log
        sync_log = self.sync_log_service.start_sync(
            source=source,
            entity_type="season",
            season_id=season.id,
        )

        records_processed = 0
        records_created = 0
        records_updated = 0
        records_skipped = 0

        try:
            # Sync teams first
            await self._sync_teams_for_season(adapter, season, source)

            # Get schedule
            games = await adapter.get_schedule(season_external_id)

            # Filter to final games
            final_games = [g for g in games if adapter.is_game_final(g)]

            # Get unsynced games
            all_external_ids = [g.external_id for g in final_games]
            unsynced_ids = self.tracker.get_unsynced_games(source, all_external_ids)
            unsynced_games = [g for g in final_games if g.external_id in unsynced_ids]

            records_skipped = len(final_games) - len(unsynced_games)
            records_processed = len(final_games)

            # Sync each unsynced game
            for raw_game in unsynced_games:
                try:
                    game = self.game_syncer.sync_game(raw_game, season.id, source)

                    # Sync box score
                    boxscore = await adapter.get_game_boxscore(raw_game.external_id)
                    self.game_syncer.sync_boxscore(boxscore, game, source)

                    # Sync PBP if requested
                    if include_pbp:
                        try:
                            pbp_events = await adapter.get_game_pbp(
                                raw_game.external_id
                            )
                            self.game_syncer.sync_pbp(pbp_events, game, source)
                        except Exception:
                            # PBP is optional, don't fail the whole sync
                            pass

                    # Mark as synced
                    self.tracker.mark_game_synced(source, raw_game.external_id, game.id)
                    records_created += 1
                    self.db.commit()

                except Exception as e:
                    # Log error but continue with other games
                    self.db.rollback()
                    records_skipped += 1
                    # Could log individual failures here
                    print(f"Error syncing game {raw_game.external_id}: {e}")

            # Complete sync log
            return self.sync_log_service.complete_sync(
                sync_id=sync_log.id,
                records_processed=records_processed,
                records_created=records_created,
                records_updated=records_updated,
                records_skipped=records_skipped,
            )

        except Exception as e:
            self.db.rollback()
            return self.sync_log_service.fail_sync(
                sync_id=sync_log.id,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()},
            )

    async def sync_season_with_progress(
        self,
        source: str,
        season_external_id: str,
        include_pbp: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Sync all games for a season with progress events.

        Async generator that yields progress events during the sync.
        Use this method for streaming endpoints that need real-time feedback.

        Args:
            source: The data source name (e.g., "winner").
            season_external_id: External ID of the season to sync.
            include_pbp: Whether to sync play-by-play data.

        Yields:
            Dict with event data for SSE streaming:
            - start: {"event": "start", "phase": "games", "total": N}
            - progress: {"event": "progress", "current": N, "total": M, "game_id": "X", "status": "syncing"}
            - synced: {"event": "synced", "game_id": "X"}
            - error: {"event": "error", "game_id": "X", "error": "message"}
            - complete: {"event": "complete", "sync_log": {...}}

        Example:
            >>> async for event in manager.sync_season_with_progress("winner", "2024-25"):
            ...     print(f"{event['event']}: {event}")
        """
        adapter = self._get_adapter(source)

        # Find or create internal season
        season = self._get_or_create_season(source, season_external_id)

        # Start sync log
        sync_log = self.sync_log_service.start_sync(
            source=source,
            entity_type="season",
            season_id=season.id,
        )

        records_processed = 0
        records_created = 0
        records_updated = 0
        records_skipped = 0

        try:
            # Sync teams first
            await self._sync_teams_for_season(adapter, season, source)

            # Get schedule
            games = await adapter.get_schedule(season_external_id)

            # Filter to final games
            final_games = [g for g in games if adapter.is_game_final(g)]

            # Get unsynced games
            all_external_ids = [g.external_id for g in final_games]
            unsynced_ids = self.tracker.get_unsynced_games(source, all_external_ids)
            unsynced_games = [g for g in final_games if g.external_id in unsynced_ids]

            records_skipped = len(final_games) - len(unsynced_games)
            records_processed = len(final_games)

            # Emit start event
            yield {
                "event": "start",
                "phase": "games",
                "total": len(unsynced_games),
                "skipped": records_skipped,
            }

            # Sync each unsynced game
            for idx, raw_game in enumerate(unsynced_games, start=1):
                # Emit progress event
                yield {
                    "event": "progress",
                    "current": idx,
                    "total": len(unsynced_games),
                    "game_id": raw_game.external_id,
                    "status": "syncing",
                }

                try:
                    game = self.game_syncer.sync_game(raw_game, season.id, source)

                    # Sync box score
                    boxscore = await adapter.get_game_boxscore(raw_game.external_id)
                    self.game_syncer.sync_boxscore(boxscore, game, source)

                    # Sync PBP if requested
                    if include_pbp:
                        try:
                            pbp_events = await adapter.get_game_pbp(
                                raw_game.external_id
                            )
                            self.game_syncer.sync_pbp(pbp_events, game, source)
                        except Exception:
                            # PBP is optional, don't fail the whole sync
                            pass

                    # Mark as synced
                    self.tracker.mark_game_synced(source, raw_game.external_id, game.id)
                    records_created += 1
                    self.db.commit()

                    # Emit synced event
                    yield {
                        "event": "synced",
                        "game_id": raw_game.external_id,
                    }

                except Exception as e:
                    # Log error but continue with other games
                    self.db.rollback()
                    records_skipped += 1

                    # Emit error event
                    yield {
                        "event": "error",
                        "game_id": raw_game.external_id,
                        "error": str(e),
                    }

            # Complete sync log
            final_sync_log = self.sync_log_service.complete_sync(
                sync_id=sync_log.id,
                records_processed=records_processed,
                records_created=records_created,
                records_updated=records_updated,
                records_skipped=records_skipped,
            )

            # Emit complete event
            yield {
                "event": "complete",
                "sync_log": {
                    "id": str(final_sync_log.id),
                    "status": final_sync_log.status,
                    "records_processed": final_sync_log.records_processed,
                    "records_created": final_sync_log.records_created,
                    "records_updated": final_sync_log.records_updated,
                    "records_skipped": final_sync_log.records_skipped,
                },
            }

        except Exception as e:
            self.db.rollback()
            failed_sync_log = self.sync_log_service.fail_sync(
                sync_id=sync_log.id,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()},
            )

            # Emit error event for fatal failure
            yield {
                "event": "complete",
                "sync_log": {
                    "id": str(failed_sync_log.id),
                    "status": failed_sync_log.status,
                    "error_message": failed_sync_log.error_message,
                    "records_processed": failed_sync_log.records_processed,
                    "records_created": failed_sync_log.records_created,
                    "records_skipped": failed_sync_log.records_skipped,
                },
            }

    async def sync_game(
        self,
        source: str,
        game_external_id: str,
        include_pbp: bool = True,
    ) -> SyncLog:
        """
        Sync a single game with box score and optionally PBP.

        Args:
            source: The data source name.
            game_external_id: External ID of the game to sync.
            include_pbp: Whether to sync play-by-play data.

        Returns:
            SyncLog with sync operation results.

        Example:
            >>> sync_log = await manager.sync_game(
            ...     source="winner",
            ...     game_external_id="12345"
            ... )
        """
        adapter = self._get_adapter(source)

        # Start sync log
        sync_log = self.sync_log_service.start_sync(
            source=source,
            entity_type="game",
        )

        try:
            # Check if already synced
            existing_game = self.tracker.get_game_by_external_id(
                source, game_external_id
            )
            if existing_game:
                return self.sync_log_service.complete_sync(
                    sync_id=sync_log.id,
                    records_processed=1,
                    records_created=0,
                    records_updated=0,
                    records_skipped=1,
                )

            # Fetch box score (contains game info)
            boxscore = await adapter.get_game_boxscore(game_external_id)
            raw_game = boxscore.game

            # Get season from schedule or use first available
            seasons = await adapter.get_seasons()
            if not seasons:
                raise ValueError("No seasons available")

            season = self._get_or_create_season(source, seasons[0].external_id)

            # Sync teams if needed
            home_team_raw = RawTeam(
                external_id=raw_game.home_team_external_id,
                name=f"Team {raw_game.home_team_external_id}",
            )
            away_team_raw = RawTeam(
                external_id=raw_game.away_team_external_id,
                name=f"Team {raw_game.away_team_external_id}",
            )

            self.team_syncer.sync_team_season(home_team_raw, season.id, source)
            self.team_syncer.sync_team_season(away_team_raw, season.id, source)

            # Sync game
            game = self.game_syncer.sync_game(raw_game, season.id, source)

            # Sync box score
            self.game_syncer.sync_boxscore(boxscore, game, source)

            # Sync PBP if requested
            if include_pbp:
                try:
                    pbp_events = await adapter.get_game_pbp(game_external_id)
                    self.game_syncer.sync_pbp(pbp_events, game, source)
                except Exception:
                    pass  # PBP is optional

            # Mark as synced
            self.tracker.mark_game_synced(source, game_external_id, game.id)
            self.db.commit()

            # Update sync log with game_id
            sync_log.game_id = game.id
            self.db.commit()

            return self.sync_log_service.complete_sync(
                sync_id=sync_log.id,
                records_processed=1,
                records_created=1,
                records_updated=0,
                records_skipped=0,
            )

        except Exception as e:
            self.db.rollback()
            return self.sync_log_service.fail_sync(
                sync_id=sync_log.id,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()},
            )

    async def sync_teams(
        self,
        source: str,
        season_external_id: str,
    ) -> SyncLog:
        """
        Sync team rosters for a season.

        Fetches teams and creates/updates team and roster records.

        Args:
            source: The data source name.
            season_external_id: External ID of the season.

        Returns:
            SyncLog with sync operation results.

        Example:
            >>> sync_log = await manager.sync_teams("winner", "2024-25")
        """
        adapter = self._get_adapter(source)

        # Get or create season
        season = self._get_or_create_season(source, season_external_id)

        # Start sync log
        sync_log = self.sync_log_service.start_sync(
            source=source,
            entity_type="teams",
            season_id=season.id,
        )

        records_created = 0
        records_updated = 0

        try:
            # Get teams
            teams = await adapter.get_teams(season_external_id)

            for raw_team in teams:
                # Check if team already exists for this source
                existing = self.team_matcher.get_by_external_id(
                    source, raw_team.external_id
                )

                # Sync team with season
                self.team_syncer.sync_team_season(raw_team, season.id, source)

                if existing:
                    records_updated += 1
                else:
                    records_created += 1

            self.db.commit()

            return self.sync_log_service.complete_sync(
                sync_id=sync_log.id,
                records_processed=len(teams),
                records_created=records_created,
                records_updated=records_updated,
                records_skipped=0,
            )

        except Exception as e:
            self.db.rollback()
            return self.sync_log_service.fail_sync(
                sync_id=sync_log.id,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()},
            )

    async def sync_player_info(
        self,
        team_id: UUID,
        season_id: UUID,
    ) -> SyncLog:
        """
        Update player info for a team roster.

        Uses PlayerInfoService to fetch and merge player biographical
        data from all available sources.

        Args:
            team_id: UUID of the team.
            season_id: UUID of the season.

        Returns:
            SyncLog with sync operation results.

        Example:
            >>> sync_log = await manager.sync_player_info(team.id, season.id)
        """
        if not self.player_info_service:
            raise ValueError("PlayerInfoService not configured")

        # Start sync log
        sync_log = self.sync_log_service.start_sync(
            source="aggregated",
            entity_type="player_info",
            season_id=season_id,
        )

        records_updated = 0

        try:
            # Get players on team roster
            from src.models.player import Player, PlayerTeamHistory

            stmt = (
                select(Player)
                .join(PlayerTeamHistory)
                .where(
                    PlayerTeamHistory.team_id == team_id,
                    PlayerTeamHistory.season_id == season_id,
                )
            )
            players = list(self.db.scalars(stmt).all())

            for player in players:
                changes = await self.player_info_service.update_player_from_sources(
                    player
                )
                if changes:
                    records_updated += 1

            self.db.commit()

            return self.sync_log_service.complete_sync(
                sync_id=sync_log.id,
                records_processed=len(players),
                records_created=0,
                records_updated=records_updated,
                records_skipped=len(players) - records_updated,
            )

        except Exception as e:
            self.db.rollback()
            return self.sync_log_service.fail_sync(
                sync_id=sync_log.id,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()},
            )

    async def sync_player_bio_from_roster(
        self,
        source: str,
        team_id: UUID,
        team_external_id: str,
        season_id: UUID,
    ) -> SyncLog:
        """
        Sync player biographical data by matching to team roster.

        This method:
        1. Gets players from the database for the given team/season
        2. Fetches the team roster from the source (e.g., basket.co.il)
        3. Matches players by name
        4. Fetches player profiles and updates bio data

        The source must have lang=en enabled for English name matching.

        Args:
            source: The data source name (e.g., "winner").
            team_id: Internal UUID of the team.
            team_external_id: External team ID for roster fetching.
            season_id: Internal UUID of the season.

        Returns:
            SyncLog with sync operation results.

        Example:
            >>> sync_log = await manager.sync_player_bio_from_roster(
            ...     source="winner",
            ...     team_id=team.id,
            ...     team_external_id="100",
            ...     season_id=season.id
            ... )
        """
        adapter = self._get_adapter(source)

        # Start sync log
        sync_log = self.sync_log_service.start_sync(
            source=source,
            entity_type="player_bio",
            season_id=season_id,
        )

        records_processed = 0
        records_updated = 0

        try:
            from src.models.player import Player, PlayerTeamHistory

            # Get players with their team history for this team/season
            stmt = (
                select(Player, PlayerTeamHistory)
                .join(PlayerTeamHistory)
                .where(
                    PlayerTeamHistory.team_id == team_id,
                    PlayerTeamHistory.season_id == season_id,
                )
            )
            results = list(self.db.execute(stmt).all())

            if not results:
                return self.sync_log_service.complete_sync(
                    sync_id=sync_log.id,
                    records_processed=0,
                    records_created=0,
                    records_updated=0,
                    records_skipped=0,
                )

            records_processed = len(results)

            # Fetch team roster from source
            roster = await adapter.get_team_roster(team_external_id)

            if not roster:
                # No roster available, skip
                return self.sync_log_service.complete_sync(
                    sync_id=sync_log.id,
                    records_processed=records_processed,
                    records_created=0,
                    records_updated=0,
                    records_skipped=records_processed,
                )

            # Build lookup by normalized name and compact name
            roster_by_name: dict[str, tuple[str, RawPlayerInfo | None]] = {}
            roster_by_compact: dict[str, tuple[str, RawPlayerInfo | None]] = {}
            for player_id, name, info in roster:
                normalized = self._normalize_name(name)
                roster_by_name[normalized] = (player_id, info)
                compact = self._normalize_name_compact(name)
                roster_by_compact[compact] = (player_id, info)

            # Match and update each player
            for player, history in results:
                normalized_name = self._normalize_name(player.full_name)
                match = roster_by_name.get(normalized_name)

                if not match:
                    # Try compact name matching (handles "DJKennedy" vs "DJ Kennedy")
                    compact_name = self._normalize_name_compact(player.full_name)
                    match = roster_by_compact.get(compact_name)

                if not match:
                    # Try partial matching (last name only)
                    match = self._find_partial_match(player, roster_by_name)

                if match:
                    roster_player_id, player_info = match
                    updated = self._update_player_bio(
                        player, history, roster_player_id, player_info, source
                    )
                    if updated:
                        records_updated += 1

            self.db.commit()

            return self.sync_log_service.complete_sync(
                sync_id=sync_log.id,
                records_processed=records_processed,
                records_created=0,
                records_updated=records_updated,
                records_skipped=records_processed - records_updated,
            )

        except Exception as e:
            self.db.rollback()
            return self.sync_log_service.fail_sync(
                sync_id=sync_log.id,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()},
            )

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for matching.

        - Lowercases
        - Removes extra spaces
        - Strips trailing position patterns (F-, G-, F-C, G-F, etc.)
        - Strips trailing "Captain|" or similar suffixes
        """
        import re

        normalized = " ".join(name.lower().split())

        # Remove trailing position patterns like "f-", "g-", "f-c", "g-f", "c"
        # These patterns appear when names were incorrectly parsed
        normalized = re.sub(r"\s+(f-c|g-f|f-|g-|c|f|g|pg|sg|sf|pf)$", "", normalized)

        # Remove trailing "captain|" or similar
        normalized = re.sub(r"\s*captain\|?\s*$", "", normalized)

        return normalized

    def _normalize_name_compact(self, name: str) -> str:
        """Normalize name to compact form (no spaces, no punctuation) for fuzzy matching."""
        import re

        # First do standard normalization
        normalized = self._normalize_name(name)
        # Remove all spaces, dots, apostrophes for compact comparison
        return re.sub(r"[\s.'\"-]", "", normalized)

    def _find_partial_match(
        self,
        player: Any,
        roster_by_name: dict[str, tuple[str, Any]],
    ) -> tuple[str, Any] | None:
        """
        Try to find a match using partial name matching.

        Attempts:
        1. Match by last name only
        2. Match by first initial + last name
        """
        last_name = self._normalize_name(player.last_name)
        first_initial = player.first_name[0].lower() if player.first_name else ""

        for full_name, match_data in roster_by_name.items():
            # Check if last names match
            name_parts = full_name.split()
            if len(name_parts) >= 1:
                roster_last = name_parts[-1]
                if roster_last == last_name:
                    # Additional check: first initial if available
                    if len(name_parts) >= 2:
                        roster_first = name_parts[0]
                        if roster_first.startswith(first_initial):
                            return match_data
                    else:
                        return match_data

        return None

    def _update_player_bio(
        self,
        player: Any,
        history: Any,
        external_id: str,
        player_info: Any | None,
        source: str,
    ) -> bool:
        """
        Update a player's bio data, team history, and external_id.

        Updates both Player fields and PlayerTeamHistory.position.

        Returns True if any field was updated.
        """
        updated = False

        # Update external_id if not already set for this source
        external_ids = player.external_ids or {}
        if source not in external_ids:
            external_ids[source] = external_id
            player.external_ids = external_ids
            updated = True

        # Update bio fields if we have player_info
        if player_info:
            # Update Player.position
            if player_info.position and not player.position:
                player.position = player_info.position
                updated = True

            # Update PlayerTeamHistory.position (always update if different)
            if player_info.position and history.position != player_info.position:
                history.position = player_info.position
                updated = True

            if player_info.height_cm and not player.height_cm:
                player.height_cm = player_info.height_cm
                updated = True
            if player_info.birth_date and not player.birth_date:
                player.birth_date = player_info.birth_date
                updated = True

        return updated

    async def sync_all_player_bios(
        self,
        source: str,
        season_id: UUID,
    ) -> SyncLog:
        """
        Sync player bio data for all teams in a season.

        Fetches rosters and bio data for all teams, matching players
        by English name.

        Args:
            source: The data source name (e.g., "winner").
            season_id: Internal UUID of the season.

        Returns:
            SyncLog with aggregated sync results.

        Example:
            >>> sync_log = await manager.sync_all_player_bios("winner", season.id)
        """
        from src.models.team import Team, TeamSeason

        self._get_adapter(source)

        # Start sync log
        sync_log = self.sync_log_service.start_sync(
            source=source,
            entity_type="player_bio_all",
            season_id=season_id,
        )

        total_processed = 0
        total_updated = 0

        try:
            # Get all teams for the season
            stmt = (
                select(Team, TeamSeason.external_id)
                .join(TeamSeason, Team.id == TeamSeason.team_id)
                .where(TeamSeason.season_id == season_id)
            )
            teams = list(self.db.execute(stmt).all())

            for team, team_external_id in teams:
                if not team_external_id:
                    continue
                try:
                    result = await self.sync_player_bio_from_roster(
                        source=source,
                        team_id=team.id,
                        team_external_id=team_external_id,
                        season_id=season_id,
                    )
                    total_processed += result.records_processed or 0
                    total_updated += result.records_updated or 0
                except Exception:
                    # Continue with other teams if one fails
                    continue

            self.db.commit()

            return self.sync_log_service.complete_sync(
                sync_id=sync_log.id,
                records_processed=total_processed,
                records_created=0,
                records_updated=total_updated,
                records_skipped=total_processed - total_updated,
            )

        except Exception as e:
            self.db.rollback()
            return self.sync_log_service.fail_sync(
                sync_id=sync_log.id,
                error_message=str(e),
                error_details={"traceback": traceback.format_exc()},
            )

    def get_sync_status(self) -> dict[str, Any]:
        """
        Get current sync status for all sources.

        Returns status information including enabled sources, running syncs,
        and latest sync info for each source.

        Returns:
            Dict with sync status information.

        Example:
            >>> status = manager.get_sync_status()
            >>> for source in status["sources"]:
            ...     print(f"{source['name']}: {source['enabled']}")
        """
        sources: list[dict[str, Any]] = []

        for source_name in self.adapters:
            source_config = self.config.get_source_config(source_name)
            enabled = self.config.is_source_enabled(source_name)

            # Get latest sync for this source
            latest_sync = self.sync_log_service.get_latest_by_source(
                source_name, "season"
            )
            latest_game_sync = self.sync_log_service.get_latest_by_source(
                source_name, "game"
            )

            # Get running syncs
            running = self.sync_log_service.get_running_syncs(source_name)

            sources.append(
                {
                    "name": source_name,
                    "enabled": enabled,
                    "auto_sync_enabled": (
                        source_config.auto_sync_enabled if source_config else False
                    ),
                    "sync_interval_minutes": (
                        source_config.sync_interval_minutes if source_config else 60
                    ),
                    "running_syncs": len(running),
                    "latest_season_sync": (
                        {
                            "id": str(latest_sync.id),
                            "status": latest_sync.status,
                            "started_at": (
                                latest_sync.started_at.isoformat()
                                if latest_sync.started_at
                                else None
                            ),
                            "records_processed": latest_sync.records_processed,
                            "records_created": latest_sync.records_created,
                        }
                        if latest_sync
                        else None
                    ),
                    "latest_game_sync": (
                        {
                            "id": str(latest_game_sync.id),
                            "status": latest_game_sync.status,
                            "started_at": (
                                latest_game_sync.started_at.isoformat()
                                if latest_game_sync.started_at
                                else None
                            ),
                        }
                        if latest_game_sync
                        else None
                    ),
                }
            )

        return {
            "sources": sources,
            "total_running_syncs": sum(s["running_syncs"] for s in sources),
        }

    async def _sync_teams_for_season(
        self,
        adapter: BaseLeagueAdapter,
        season: Season,
        source: str,
    ) -> None:
        """Sync teams for a season before syncing games."""
        teams = await adapter.get_teams(season.name)

        for raw_team in teams:
            self.team_syncer.sync_team_season(raw_team, season.id, source)

        self.db.flush()

    def _get_or_create_season(self, source: str, season_external_id: str) -> Season:
        """
        Get or create a Season for the given external ID.

        Args:
            source: The data source name.
            season_external_id: External season identifier (e.g., "2024-25").

        Returns:
            Season model instance.
        """
        from datetime import date

        from src.models.league import League

        # Try to find existing season by name
        stmt = select(Season).where(Season.name == season_external_id)
        season = self.db.scalars(stmt).first()
        if season:
            return season

        # Create league if needed
        league_code = source.upper()
        stmt = select(League).where(League.code == league_code)
        league = self.db.scalars(stmt).first()

        if not league:
            # Infer country from source
            countries = {"winner": "Israel", "euroleague": "Europe", "nba": "USA"}
            league = League(
                name=f"{source.title()} League",
                code=league_code,
                country=countries.get(source, "Unknown"),
            )
            self.db.add(league)
            self.db.flush()

        # Parse season dates from name (e.g., "2024-25")
        try:
            parts = season_external_id.split("-")
            start_year = int(parts[0])
            if len(parts) > 1:
                end_year_short = int(parts[1])
                # Handle two-digit year
                if end_year_short < 100:
                    century = (start_year // 100) * 100
                    end_year = century + end_year_short
                else:
                    end_year = end_year_short
            else:
                end_year = start_year + 1
        except (ValueError, IndexError):
            start_year = date.today().year
            end_year = start_year + 1

        # Create season
        season = Season(
            league_id=league.id,
            name=season_external_id,
            start_date=date(start_year, 9, 1),
            end_date=date(end_year, 6, 30),
            is_current=True,
        )
        self.db.add(season)
        self.db.flush()

        return season
