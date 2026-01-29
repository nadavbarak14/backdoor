"""
Player Syncer Module

Provides functionality to sync player data from external sources to the database.
Uses PlayerDeduplicator to find or create players while avoiding duplicates.

Players are ONLY created from roster data (which has names).
Boxscore/PBP data matches players by jersey number - never creates new players.

Usage:
    from src.sync.entities.player import PlayerSyncer
    from src.sync.deduplication import PlayerDeduplicator

    deduplicator = PlayerDeduplicator(db_session)
    syncer = PlayerSyncer(db_session, deduplicator)

    # Sync a player from roster info (creates player with name)
    player = syncer.sync_player(raw_player_info, team_id, source)

    # Match player from boxscore by jersey (never creates, returns None if not found)
    player = syncer.sync_player_from_stats(raw_stats, team_id, season_id, source)
"""

from uuid import UUID

from sqlalchemy.orm import Session

from src.models.player import Player
from src.sync.deduplication import PlayerDeduplicator
from src.sync.types import RawPlayerInfo, RawPlayerStats


class PlayerSyncer:
    """
    Syncs player data from external sources to the database.

    Uses PlayerDeduplicator to ensure players are not duplicated across
    different data sources. Handles both full player info and minimal
    data from box score stats.

    Attributes:
        db: SQLAlchemy Session for database operations.
        deduplicator: PlayerDeduplicator for finding/creating players.

    Example:
        >>> syncer = PlayerSyncer(db_session, player_deduplicator)
        >>> player = syncer.sync_player(raw_player_info, team.id, "winner")
        >>> print(player.full_name)
    """

    def __init__(self, db: Session, deduplicator: PlayerDeduplicator) -> None:
        """
        Initialize the player syncer.

        Args:
            db: SQLAlchemy database session.
            deduplicator: PlayerDeduplicator instance for deduplication.

        Example:
            >>> syncer = PlayerSyncer(db_session, player_deduplicator)
        """
        self.db = db
        self.deduplicator = deduplicator

    def sync_player(
        self,
        raw: RawPlayerInfo,
        team_id: UUID | None,
        source: str,
    ) -> Player:
        """
        Sync a player from raw player info to the database.

        Uses the deduplicator to find an existing player or create a new one.
        The deduplicator handles matching by external ID, team roster, or
        biographical data.

        Args:
            raw: Raw player info from external source.
            team_id: Optional UUID of the team for roster-based matching.
            source: The data source name (e.g., "winner", "euroleague").

        Returns:
            The found or created Player entity.

        Example:
            >>> player = syncer.sync_player(
            ...     raw=RawPlayerInfo(
            ...         external_id="p123",
            ...         first_name="LeBron",
            ...         last_name="James",
            ...         birth_date=date(1984, 12, 30)
            ...     ),
            ...     team_id=lakers.id,
            ...     source="winner"
            ... )
        """
        return self.deduplicator.find_or_create_player(
            source=source,
            external_id=raw.external_id,
            player_data=raw,
            team_id=team_id,
        )

    def sync_player_from_stats(
        self,
        raw: RawPlayerStats,
        team_id: UUID,
        season_id: UUID,
        source: str | None = None,
    ) -> Player | None:
        """
        Find or create a player from boxscore stats.

        Matching priority:
        1. External ID match (exact, fast)
        2. Team roster name match (prevents cross-league duplicates)
        3. Birthdate + name similarity (fuzzy, cross-source matching)
        4. Jersey number match (fallback for roster-based sources)
        5. Create new player (only if all matching fails)

        Args:
            raw: Raw player stats from a box score.
            team_id: UUID of the team.
            season_id: UUID of the season.
            source: Optional data source name for external_id matching.

        Returns:
            The matched or created Player, or None if cannot match/create.

        Example:
            >>> player = syncer.sync_player_from_stats(
            ...     raw=raw_player_stats,
            ...     team_id=team.id,
            ...     season_id=season.id,
            ...     source="euroleague",
            ... )
        """
        # Try to find/create by external_id first (e.g., Euroleague)
        if source and raw.player_external_id:
            player = self.deduplicator.get_by_external_id(
                source, raw.player_external_id
            )
            if player:
                return player

            # If we have a name, try multiple matching strategies
            if raw.player_name:
                # Parse name format ("LASTNAME, FIRSTNAME" -> "FIRSTNAME LASTNAME")
                full_name = self._parse_player_name(raw.player_name)

                # Strategy 1: Check team roster for existing player with same name
                matched = self.deduplicator.match_player_on_team(
                    team_id=team_id,
                    player_name=full_name,
                    source=source,
                )
                if matched:
                    # Found existing player on team - add external_id and return
                    return self.deduplicator.merge_external_id(
                        matched, source, raw.player_external_id
                    )

                # Strategy 2: Match by birthdate + name similarity
                # This catches players who exist in DB from other sources
                if raw.birth_date:
                    matched = self.deduplicator.match_player_by_birthdate(
                        birth_date=raw.birth_date,
                        player_name=full_name,
                        source=source,
                        similarity_threshold=0.8,
                    )
                    if matched:
                        return self.deduplicator.merge_external_id(
                            matched, source, raw.player_external_id
                        )

                # No match found - create new player
                return self._create_player_from_stats(raw, team_id, source, season_id)

        # Fall back to jersey matching (e.g., Winner league with rosters)
        if raw.jersey_number:
            return self.deduplicator.match_player_by_jersey(
                team_id=team_id,
                season_id=season_id,
                jersey_number=raw.jersey_number,
            )

        return None

    def _parse_player_name(self, name: str) -> str:
        """
        Parse player name from various formats to "FIRSTNAME LASTNAME".

        Handles formats:
        - "LASTNAME, FIRSTNAME" -> "FIRSTNAME LASTNAME"
        - "FIRSTNAME LASTNAME" -> "FIRSTNAME LASTNAME" (unchanged)

        Args:
            name: Player name in various formats.

        Returns:
            Name in "FIRSTNAME LASTNAME" format.

        Example:
            >>> syncer._parse_player_name("DOWNTIN, JEFF")
            'JEFF DOWNTIN'
            >>> syncer._parse_player_name("Jeff Downtin")
            'Jeff Downtin'
        """
        if "," in name:
            parts = name.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
            return f"{first_name} {last_name}".strip()
        return name

    def _create_player_from_stats(
        self,
        raw: RawPlayerStats,
        team_id: UUID,
        source: str,
        season_id: UUID | None = None,
    ) -> Player:
        """
        Create a new player from boxscore stats data.

        Args:
            raw: Raw player stats containing name and external_id.
            team_id: UUID of the team.
            source: Data source name.
            season_id: Optional UUID of the season for team history.

        Returns:
            The newly created Player entity.
        """
        # Parse name to get first/last components
        name = raw.player_name or ""
        first_name = ""
        last_name = ""

        if "," in name:
            # Format: "LASTNAME, FIRSTNAME"
            parts = name.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Format: "FIRSTNAME LASTNAME"
            parts = name.split()
            if parts:
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        player = Player(
            first_name=first_name,
            last_name=last_name,
            birth_date=raw.birth_date,  # Save birthdate if available
            external_ids={source: raw.player_external_id},
        )
        self.db.add(player)
        self.db.flush()

        # Create team history if we have season_id
        if season_id:
            from src.models.player import PlayerTeamHistory

            history = PlayerTeamHistory(
                player_id=player.id,
                team_id=team_id,
                season_id=season_id,
            )
            self.db.add(history)
            self.db.flush()

        return player

    def get_by_external_id(self, source: str, external_id: str) -> Player | None:
        """
        Get a player by their external ID for a specific source.

        Args:
            source: The data source name.
            external_id: The external ID from the source.

        Returns:
            The Player if found, None otherwise.

        Example:
            >>> player = syncer.get_by_external_id("winner", "p123")
        """
        return self.deduplicator.get_by_external_id(source, external_id)
