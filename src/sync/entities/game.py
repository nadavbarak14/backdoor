"""
Game Syncer Module

Provides functionality to sync game data including box scores and play-by-play
events from external sources to the database.

Usage:
    from src.sync.entities.game import GameSyncer

    syncer = GameSyncer(db, team_matcher, player_deduplicator)

    # Sync a game
    game = syncer.sync_game(raw_game, season_id, source)

    # Sync box score
    syncer.sync_boxscore(raw_boxscore, game)

    # Sync play-by-play
    syncer.sync_pbp(raw_events, game, source)
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats, TeamGameStats
from src.models.play_by_play import PlayByPlayEvent, PlayByPlayEventLink
from src.sync.canonical.entities import (
    CanonicalGame,
    CanonicalPBPEvent,
    CanonicalPlayerStats,
)
from src.sync.deduplication import PlayerDeduplicator, TeamMatcher
from src.sync.entities.player import PlayerSyncer
from src.sync.entities.team import TeamSyncer
from src.sync.types import RawBoxScore, RawGame, RawPBPEvent, RawPlayerStats


class GameSyncer:
    """
    Syncs game data including box scores and play-by-play to the database.

    Handles the full lifecycle of game data import:
    - Creating/updating Game records
    - Creating PlayerGameStats from box scores
    - Creating TeamGameStats aggregations
    - Creating PlayByPlayEvent records with links

    Attributes:
        db: SQLAlchemy Session for database operations.
        team_syncer: TeamSyncer for team operations.
        player_syncer: PlayerSyncer for player operations.

    Example:
        >>> syncer = GameSyncer(db, team_matcher, player_deduplicator)
        >>> game = syncer.sync_game(raw_game, season.id, "winner")
        >>> syncer.sync_boxscore(raw_boxscore, game)
    """

    def __init__(
        self,
        db: Session,
        team_matcher: TeamMatcher,
        player_deduplicator: PlayerDeduplicator,
    ) -> None:
        """
        Initialize the game syncer.

        Args:
            db: SQLAlchemy database session.
            team_matcher: TeamMatcher for team deduplication.
            player_deduplicator: PlayerDeduplicator for player matching.

        Example:
            >>> syncer = GameSyncer(db_session, team_matcher, player_deduplicator)
        """
        self.db = db
        self.team_syncer = TeamSyncer(db, team_matcher, player_deduplicator)
        self.player_syncer = PlayerSyncer(db, player_deduplicator)

    def sync_game(
        self,
        raw: RawGame,
        season_id: UUID,
        source: str,
    ) -> Game:
        """
        Sync a game record from raw data.

        .. deprecated::
            Use sync_game_from_canonical() instead. Convert RawGame using
            raw_game_to_canonical() from src.sync.raw_to_canonical.

        Creates or updates a Game record. If the game already exists
        (matched by external_id), updates its status and scores.

        Args:
            raw: Raw game data from external source.
            season_id: UUID of the season this game belongs to.
            source: The data source name (e.g., "winner", "euroleague").

        Returns:
            The created or updated Game entity.

        Example:
            >>> game = syncer.sync_game(raw_game, season.id, "winner")
            >>> print(f"Game: {game.home_team.name} vs {game.away_team.name}")
        """
        # Get or create teams
        home_team = self.team_syncer.get_by_external_id(
            source, raw.home_team_external_id
        )
        away_team = self.team_syncer.get_by_external_id(
            source, raw.away_team_external_id
        )

        if not home_team or not away_team:
            raise ValueError(
                f"Teams not found for game {raw.external_id}. "
                "Ensure teams are synced first."
            )

        # Check if game already exists
        existing = self._get_by_external_id(source, raw.external_id)
        if existing:
            return self._update_game(existing, raw)

        # Create new game
        # raw.status is already a GameStatus enum - TypeDecorator handles DB conversion
        game = Game(
            season_id=season_id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            game_date=raw.game_date,
            status=raw.status,
            home_score=raw.home_score,
            away_score=raw.away_score,
            external_ids={source: raw.external_id},
        )

        self.db.add(game)
        self.db.flush()
        return game

    def sync_boxscore(
        self,
        raw: RawBoxScore,
        game: Game,
        source: str | None = None,
    ) -> tuple[list[PlayerGameStats], list[TeamGameStats]]:
        """
        Sync box score data for a game.

        .. deprecated::
            Use sync_boxscore_from_canonical() instead. Convert RawBoxScore using
            raw_boxscore_to_canonical_stats() from src.sync.raw_to_canonical.

        Creates PlayerGameStats for all players and TeamGameStats
        for both teams. Players are matched by external_id or jersey number.

        Args:
            raw: Raw box score data from external source.
            game: The Game entity to sync stats for.
            source: Optional data source name for player matching.

        Returns:
            Tuple of (player_stats, team_stats) lists.

        Example:
            >>> player_stats, team_stats = syncer.sync_boxscore(
            ...     raw_boxscore, game, source="euroleague"
            ... )
        """
        player_stats: list[PlayerGameStats] = []
        team_stats: list[TeamGameStats] = []

        # Delete existing stats for this game (re-sync)
        self._delete_game_stats(game.id)

        # Sync home team players
        home_player_stats = self._sync_team_player_stats(
            raw.home_players,
            game=game,
            team_id=game.home_team_id,
            source=source,
        )
        player_stats.extend(home_player_stats)

        # Sync away team players
        away_player_stats = self._sync_team_player_stats(
            raw.away_players,
            game=game,
            team_id=game.away_team_id,
            source=source,
        )
        player_stats.extend(away_player_stats)

        # Create team stats
        home_team_stats = self._create_team_stats(
            game=game,
            team_id=game.home_team_id,
            player_stats=home_player_stats,
            is_home=True,
        )
        team_stats.append(home_team_stats)

        away_team_stats = self._create_team_stats(
            game=game,
            team_id=game.away_team_id,
            player_stats=away_player_stats,
            is_home=False,
        )
        team_stats.append(away_team_stats)

        self.db.flush()
        return player_stats, team_stats

    def sync_game_from_canonical(
        self,
        canonical: CanonicalGame,
        season_id: UUID,
    ) -> Game:
        """
        Sync a game record from canonical data.

        Creates or updates a Game record from validated canonical data.
        The canonical game has already been validated by the converter.

        Args:
            canonical: CanonicalGame from converter.
            season_id: UUID of the season this game belongs to.

        Returns:
            The created or updated Game entity.

        Raises:
            ValueError: If teams not found in database.

        Example:
            >>> game = syncer.sync_game_from_canonical(canonical_game, season.id)
        """
        # Get teams by external_id
        home_team = self.team_syncer.get_by_external_id(
            canonical.source, canonical.home_team_external_id
        )
        away_team = self.team_syncer.get_by_external_id(
            canonical.source, canonical.away_team_external_id
        )

        if not home_team or not away_team:
            raise ValueError(
                f"Teams not found for game {canonical.external_id}. "
                "Ensure teams are synced first."
            )

        # Check if game already exists
        existing = self._get_by_external_id(canonical.source, canonical.external_id)
        if existing:
            # Update existing game
            existing.status = canonical.status
            existing.home_score = canonical.home_score
            existing.away_score = canonical.away_score
            self.db.flush()
            return existing

        # Create new game
        game = Game(
            season_id=season_id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            game_date=canonical.game_date,
            status=canonical.status,
            home_score=canonical.home_score,
            away_score=canonical.away_score,
            external_ids={canonical.source: canonical.external_id},
        )

        self.db.add(game)
        self.db.flush()
        return game

    def sync_boxscore_from_canonical(
        self,
        player_stats_list: list[CanonicalPlayerStats],
        game: Game,
        source: str,
    ) -> tuple[list[PlayerGameStats], list[TeamGameStats]]:
        """
        Sync box score from canonical player stats.

        Creates PlayerGameStats for all players using validated canonical data.
        Minutes are already in seconds from the canonical format.

        Args:
            player_stats_list: List of CanonicalPlayerStats from converter.
            game: The Game entity to sync stats for.
            source: Data source name for player matching.

        Returns:
            Tuple of (player_stats, team_stats) lists.

        Example:
            >>> player_stats, team_stats = syncer.sync_boxscore_from_canonical(
            ...     canonical_stats, game, "euroleague"
            ... )
        """
        # Delete existing stats for this game (re-sync)
        self._delete_game_stats(game.id)

        player_stats: list[PlayerGameStats] = []
        home_player_stats: list[PlayerGameStats] = []
        away_player_stats: list[PlayerGameStats] = []

        for canonical in player_stats_list:
            # Resolve team_id from external_id
            team = self.team_syncer.get_by_external_id(
                source, canonical.team_external_id
            )
            if not team:
                continue

            team_id = team.id
            is_home = team_id == game.home_team_id

            # Match or create player
            player = self.player_syncer.sync_player_from_stats_canonical(
                canonical=canonical,
                team_id=team_id,
                season_id=game.season_id,
                source=source,
            )

            if player is None:
                continue

            stats = PlayerGameStats(
                game_id=game.id,
                player_id=player.id,
                team_id=team_id,
                minutes_played=canonical.minutes_seconds,  # Already in seconds
                is_starter=canonical.is_starter,
                points=canonical.points,
                field_goals_made=canonical.field_goals_made,
                field_goals_attempted=canonical.field_goals_attempted,
                two_pointers_made=canonical.two_pointers_made,
                two_pointers_attempted=canonical.two_pointers_attempted,
                three_pointers_made=canonical.three_pointers_made,
                three_pointers_attempted=canonical.three_pointers_attempted,
                free_throws_made=canonical.free_throws_made,
                free_throws_attempted=canonical.free_throws_attempted,
                offensive_rebounds=canonical.offensive_rebounds,
                defensive_rebounds=canonical.defensive_rebounds,
                total_rebounds=canonical.total_rebounds,
                assists=canonical.assists,
                turnovers=canonical.turnovers,
                steals=canonical.steals,
                blocks=canonical.blocks,
                personal_fouls=canonical.personal_fouls,
                plus_minus=canonical.plus_minus,
            )

            self.db.add(stats)
            player_stats.append(stats)

            if is_home:
                home_player_stats.append(stats)
            else:
                away_player_stats.append(stats)

        # Create team stats
        team_stats: list[TeamGameStats] = []

        home_team_stats = self._create_team_stats(
            game=game,
            team_id=game.home_team_id,
            player_stats=home_player_stats,
            is_home=True,
        )
        team_stats.append(home_team_stats)

        away_team_stats = self._create_team_stats(
            game=game,
            team_id=game.away_team_id,
            player_stats=away_player_stats,
            is_home=False,
        )
        team_stats.append(away_team_stats)

        self.db.flush()
        return player_stats, team_stats

    def sync_pbp_from_canonical(
        self,
        events: list[CanonicalPBPEvent],
        game: Game,
        source: str,
    ) -> list[PlayByPlayEvent]:
        """
        Sync play-by-play events from canonical data.

        Creates PlayByPlayEvent records from validated canonical events.
        Uses canonical event types and subtypes directly.

        Args:
            events: List of CanonicalPBPEvent from converter.
            game: The Game entity to sync events for.
            source: The data source name.

        Returns:
            List of created PlayByPlayEvent entities.

        Example:
            >>> pbp_events = syncer.sync_pbp_from_canonical(
            ...     canonical_events, game, "euroleague"
            ... )
        """
        # Delete existing PBP for this game (re-sync)
        self._delete_game_pbp(game.id)

        # Map event_number to PlayByPlayEvent for linking
        event_map: dict[int, PlayByPlayEvent] = {}
        pbp_events: list[PlayByPlayEvent] = []

        for canonical in events:
            # Resolve team_id
            team_id = self._resolve_team_id_canonical(
                canonical.team_external_id, game, source
            )
            # Resolve player_id
            player_id = self._resolve_player_id_canonical(
                canonical.player_external_id, team_id, source
            )

            # Build event subtype from canonical shot_type, rebound_type, etc.
            event_subtype = None
            if canonical.shot_type:
                event_subtype = canonical.shot_type.value
            elif canonical.rebound_type:
                event_subtype = canonical.rebound_type.value
            elif canonical.foul_type:
                event_subtype = canonical.foul_type.value
            elif canonical.turnover_type:
                event_subtype = canonical.turnover_type.value

            event = PlayByPlayEvent(
                game_id=game.id,
                event_number=canonical.event_number,
                period=canonical.period,
                clock=canonical.clock_seconds,
                event_type=canonical.event_type,
                event_subtype=event_subtype,
                player_id=player_id,
                team_id=team_id,
                success=canonical.success,
                coord_x=canonical.coord_x,
                coord_y=canonical.coord_y,
            )

            self.db.add(event)
            event_map[canonical.event_number] = event
            pbp_events.append(event)

        # Flush to get IDs for linking
        self.db.flush()

        # Create event links
        for canonical in events:
            if canonical.related_event_ids:
                source_event = event_map.get(canonical.event_number)
                if not source_event:
                    continue

                for related_num in canonical.related_event_ids:
                    related_event = event_map.get(related_num)
                    if related_event:
                        link = PlayByPlayEventLink(
                            event_id=source_event.id,
                            related_event_id=related_event.id,
                        )
                        self.db.add(link)

        self.db.flush()
        return pbp_events

    def _resolve_team_id_canonical(
        self,
        team_external_id: str | None,
        game: Game,
        source: str,
    ) -> UUID:
        """Resolve team ID from canonical external ID."""
        if team_external_id:
            if team_external_id == "home":
                return game.home_team_id
            if team_external_id == "away":
                return game.away_team_id

            team = self.team_syncer.get_by_external_id(source, team_external_id)
            if team:
                return team.id

        return game.home_team_id

    def _resolve_player_id_canonical(
        self,
        player_external_id: str | None,
        team_id: UUID,
        source: str,
    ) -> UUID | None:
        """Resolve player ID from canonical external ID."""
        from src.models.player import Player

        if player_external_id:
            stmt = select(Player).where(
                Player.external_ids[source].as_string() == player_external_id
            )
            player = self.db.scalars(stmt).first()
            if player:
                return player.id

        return None

    def sync_pbp(
        self,
        events: list[RawPBPEvent],
        game: Game,
        source: str,
    ) -> list[PlayByPlayEvent]:
        """
        Sync play-by-play events for a game.

        .. deprecated::
            Use sync_pbp_from_canonical() instead. Convert RawPBPEvent list using
            raw_pbp_list_to_canonical() from src.sync.raw_to_canonical.

        Creates PlayByPlayEvent records and links related events
        (e.g., assists to made shots).

        Args:
            events: List of raw PBP events from external source.
            game: The Game entity to sync events for.
            source: The data source name.

        Returns:
            List of created PlayByPlayEvent entities.

        Example:
            >>> pbp_events = syncer.sync_pbp(raw_events, game, "winner")
            >>> print(f"Synced {len(pbp_events)} events")
        """
        # Delete existing PBP for this game (re-sync)
        self._delete_game_pbp(game.id)

        # Map event_number to PlayByPlayEvent for linking
        event_map: dict[int, PlayByPlayEvent] = {}
        pbp_events: list[PlayByPlayEvent] = []

        for raw_event in events:
            # Get team and player IDs
            team_id = self._resolve_team_id(raw_event.team_external_id, game, source)
            player_id = self._resolve_player_id(
                raw_event.player_external_id,
                raw_event.player_name,
                team_id,
                source,
            )

            # raw_event.event_type is now an EventType enum
            # TypeDecorator handles conversion to string for storage
            event = PlayByPlayEvent(
                game_id=game.id,
                event_number=raw_event.event_number,
                period=raw_event.period,
                clock=raw_event.clock,
                event_type=raw_event.event_type,
                event_subtype=raw_event.event_subtype,
                player_id=player_id,
                team_id=team_id,
                success=raw_event.success,
                coord_x=raw_event.coord_x,
                coord_y=raw_event.coord_y,
            )

            self.db.add(event)
            event_map[raw_event.event_number] = event
            pbp_events.append(event)

        # Flush to get IDs for linking
        self.db.flush()

        # Create event links
        for raw_event in events:
            if raw_event.related_event_numbers:
                source_event = event_map.get(raw_event.event_number)
                if not source_event:
                    continue

                for related_num in raw_event.related_event_numbers:
                    related_event = event_map.get(related_num)
                    if related_event:
                        link = PlayByPlayEventLink(
                            event_id=source_event.id,
                            related_event_id=related_event.id,
                        )
                        self.db.add(link)

        self.db.flush()
        return pbp_events

    def _get_by_external_id(self, source: str, external_id: str) -> Game | None:
        """Find a game by external ID."""
        stmt = select(Game).where(Game.external_ids[source].as_string() == external_id)
        return self.db.scalars(stmt).first()

    def _update_game(self, game: Game, raw: RawGame) -> Game:
        """Update an existing game with new data."""
        # raw.status is already a GameStatus enum - TypeDecorator handles DB conversion
        game.status = raw.status
        game.home_score = raw.home_score
        game.away_score = raw.away_score
        self.db.flush()
        return game

    def _delete_game_stats(self, game_id: UUID) -> None:
        """Delete existing stats for a game."""
        # Delete player stats
        self.db.execute(
            PlayerGameStats.__table__.delete().where(PlayerGameStats.game_id == game_id)
        )
        # Delete team stats
        self.db.execute(
            TeamGameStats.__table__.delete().where(TeamGameStats.game_id == game_id)
        )

    def _delete_game_pbp(self, game_id: UUID) -> None:
        """Delete existing PBP events for a game."""
        # Get event IDs first
        stmt = select(PlayByPlayEvent.id).where(PlayByPlayEvent.game_id == game_id)
        event_ids = list(self.db.scalars(stmt).all())

        if event_ids:
            # Delete links
            self.db.execute(
                PlayByPlayEventLink.__table__.delete().where(
                    PlayByPlayEventLink.event_id.in_(event_ids)
                )
            )
            self.db.execute(
                PlayByPlayEventLink.__table__.delete().where(
                    PlayByPlayEventLink.related_event_id.in_(event_ids)
                )
            )

        # Delete events
        self.db.execute(
            PlayByPlayEvent.__table__.delete().where(PlayByPlayEvent.game_id == game_id)
        )

    def _sync_team_player_stats(
        self,
        player_stats: list[RawPlayerStats],
        game: Game,
        team_id: UUID,
        source: str | None = None,
    ) -> list[PlayerGameStats]:
        """Sync player stats for one team."""
        result: list[PlayerGameStats] = []

        for raw in player_stats:
            # Match or create player from stats
            player = self.player_syncer.sync_player_from_stats(
                raw=raw,
                team_id=team_id,
                season_id=game.season_id,
                source=source,
            )

            if player is None:
                # Could not match/create player - skip their stats
                continue

            stats = PlayerGameStats(
                game_id=game.id,
                player_id=player.id,
                team_id=team_id,
                minutes_played=raw.minutes_played,
                is_starter=raw.is_starter,
                points=raw.points,
                field_goals_made=raw.field_goals_made,
                field_goals_attempted=raw.field_goals_attempted,
                two_pointers_made=raw.two_pointers_made,
                two_pointers_attempted=raw.two_pointers_attempted,
                three_pointers_made=raw.three_pointers_made,
                three_pointers_attempted=raw.three_pointers_attempted,
                free_throws_made=raw.free_throws_made,
                free_throws_attempted=raw.free_throws_attempted,
                offensive_rebounds=raw.offensive_rebounds,
                defensive_rebounds=raw.defensive_rebounds,
                total_rebounds=raw.total_rebounds,
                assists=raw.assists,
                turnovers=raw.turnovers,
                steals=raw.steals,
                blocks=raw.blocks,
                personal_fouls=raw.personal_fouls,
                plus_minus=raw.plus_minus,
                efficiency=raw.efficiency,
            )

            self.db.add(stats)
            result.append(stats)

        return result

    def _create_team_stats(
        self,
        game: Game,
        team_id: UUID,
        player_stats: list[PlayerGameStats],
        is_home: bool,
    ) -> TeamGameStats:
        """Aggregate player stats into team stats."""
        team_stats = TeamGameStats(
            game_id=game.id,
            team_id=team_id,
            is_home=is_home,
            points=sum(p.points for p in player_stats),
            field_goals_made=sum(p.field_goals_made for p in player_stats),
            field_goals_attempted=sum(p.field_goals_attempted for p in player_stats),
            two_pointers_made=sum(p.two_pointers_made for p in player_stats),
            two_pointers_attempted=sum(p.two_pointers_attempted for p in player_stats),
            three_pointers_made=sum(p.three_pointers_made for p in player_stats),
            three_pointers_attempted=sum(
                p.three_pointers_attempted for p in player_stats
            ),
            free_throws_made=sum(p.free_throws_made for p in player_stats),
            free_throws_attempted=sum(p.free_throws_attempted for p in player_stats),
            offensive_rebounds=sum(p.offensive_rebounds for p in player_stats),
            defensive_rebounds=sum(p.defensive_rebounds for p in player_stats),
            total_rebounds=sum(p.total_rebounds for p in player_stats),
            assists=sum(p.assists for p in player_stats),
            turnovers=sum(p.turnovers for p in player_stats),
            steals=sum(p.steals for p in player_stats),
            blocks=sum(p.blocks for p in player_stats),
            personal_fouls=sum(p.personal_fouls for p in player_stats),
        )

        self.db.add(team_stats)
        return team_stats

    def _resolve_team_id(
        self,
        team_external_id: str | None,
        game: Game,
        source: str,
    ) -> UUID:
        """Resolve team ID from external ID or game context."""
        if team_external_id:
            # Handle "home"/"away" values from segevstats PBP
            if team_external_id == "home":
                return game.home_team_id
            if team_external_id == "away":
                return game.away_team_id

            # Try to find by external ID
            team = self.team_syncer.get_by_external_id(source, team_external_id)
            if team:
                return team.id

        # Default to home team if can't resolve
        return game.home_team_id

    def _resolve_player_id(
        self,
        player_external_id: str | None,
        player_name: str | None,
        team_id: UUID,
        source: str,
    ) -> UUID | None:
        """Resolve player ID from external ID or name."""
        from src.models.player import Player

        # First try by external ID
        if player_external_id:
            stmt = select(Player).where(
                Player.external_ids[source].as_string() == player_external_id
            )
            player = self.db.scalars(stmt).first()
            if player:
                return player.id

        # Fall back to name matching
        if not player_name:
            return None

        from src.sync.deduplication.normalizer import normalize_name

        stmt = (
            select(PlayerGameStats.player_id)
            .where(PlayerGameStats.team_id == team_id)
            .distinct()
        )
        player_ids = list(self.db.scalars(stmt).all())

        if not player_ids:
            return None

        for pid in player_ids:
            stmt = select(Player).where(Player.id == pid)
            player = self.db.scalars(stmt).first()
            if player and normalize_name(player.full_name) == normalize_name(
                player_name
            ):
                return player.id

        return None
