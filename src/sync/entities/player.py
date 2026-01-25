"""
Player Syncer Module

Provides functionality to sync player data from external sources to the database.
Uses PlayerDeduplicator to find or create players while avoiding duplicates.

Usage:
    from src.sync.entities.player import PlayerSyncer
    from src.sync.deduplication import PlayerDeduplicator

    deduplicator = PlayerDeduplicator(db_session)
    syncer = PlayerSyncer(db_session, deduplicator)

    # Sync a player from raw info
    player = syncer.sync_player(raw_player_info, team_id, source)

    # Sync from box score stats (creates basic player record)
    player = syncer.sync_player_from_stats(raw_player_stats, team_id, source)
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
        team_id: UUID | None,
        source: str,
    ) -> Player:
        """
        Sync a player from box score stats to the database.

        Creates a RawPlayerInfo from the limited data available in stats.
        This is used when syncing box scores where only basic player info
        is available.

        Args:
            raw: Raw player stats from a box score.
            team_id: Optional UUID of the team for roster-based matching.
            source: The data source name.

        Returns:
            The found or created Player entity.

        Example:
            >>> player = syncer.sync_player_from_stats(
            ...     raw=raw_player_stats,
            ...     team_id=team.id,
            ...     source="winner"
            ... )
        """
        # Parse name into first/last
        name_parts = raw.player_name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Create minimal player info from stats
        player_info = RawPlayerInfo(
            external_id=raw.player_external_id,
            first_name=first_name,
            last_name=last_name,
            birth_date=None,
            height_cm=None,
            position=None,
        )

        return self.deduplicator.find_or_create_player(
            source=source,
            external_id=raw.player_external_id,
            player_data=player_info,
            team_id=team_id,
        )

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
