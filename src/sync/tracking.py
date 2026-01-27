"""
Sync Tracking Module

Provides functionality to track which games have been synced from external
sources to avoid re-syncing. Uses the Game.external_ids JSON field to store
mappings between external provider IDs and internal UUIDs.

Usage:
    from src.sync.tracking import SyncTracker

    tracker = SyncTracker(db_session)

    # Check if a game is already synced
    if tracker.is_game_synced("winner", "game-123"):
        print("Game already synced")

    # Get list of unsynced games
    unsynced = tracker.get_unsynced_games("winner", ["game-1", "game-2", "game-3"])

    # Mark a game as synced
    tracker.mark_game_synced("winner", "game-123", game_uuid)
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.game import Game


class SyncTracker:
    """
    Tracks synced games to prevent duplicate syncing.

    Uses the Game.external_ids JSON field to determine which games
    have already been synced from a specific source.

    Attributes:
        db: SQLAlchemy database session

    Example:
        >>> tracker = SyncTracker(db_session)
        >>> tracker.is_game_synced("winner", "game-123")
        False
        >>> tracker.mark_game_synced("winner", "game-123", game.id)
        >>> tracker.is_game_synced("winner", "game-123")
        True
    """

    def __init__(self, db: Session):
        """
        Initialize SyncTracker.

        Args:
            db: SQLAlchemy database session for queries

        Example:
            >>> from src.core.database import get_db
            >>> db = next(get_db())
            >>> tracker = SyncTracker(db)
        """
        self.db = db

    def is_game_synced(self, source: str, external_id: str) -> bool:
        """
        Check if a game with the given external ID has been synced.

        Args:
            source: Name of the sync source (e.g., "winner", "euroleague")
            external_id: External game ID from the source

        Returns:
            True if a game exists with this external ID, False otherwise

        Example:
            >>> tracker.is_game_synced("winner", "game-123")
            True
        """
        game = self._find_game_by_external_id(source, external_id)
        return game is not None

    def get_unsynced_games(self, source: str, external_ids: list[str]) -> list[str]:
        """
        Filter a list of external IDs to only those not yet synced.

        Args:
            source: Name of the sync source
            external_ids: List of external game IDs to check

        Returns:
            List of external IDs that have not been synced yet

        Example:
            >>> tracker.get_unsynced_games("winner", ["g1", "g2", "g3"])
            ["g2", "g3"]  # If only g1 was previously synced
        """
        if not external_ids:
            return []

        synced_ids = self._get_synced_external_ids(source, external_ids)
        return [eid for eid in external_ids if eid not in synced_ids]

    def mark_game_synced(self, source: str, external_id: str, game_id: UUID) -> None:
        """
        Mark a game as synced by updating its external_ids field.

        This method updates an existing game's external_ids JSON field
        to include the mapping for the given source. If the game already
        has an entry for this source, it will be updated.

        Args:
            source: Name of the sync source
            external_id: External game ID from the source
            game_id: Internal UUID of the game in our database

        Raises:
            ValueError: If no game exists with the given game_id

        Example:
            >>> tracker.mark_game_synced("winner", "game-123", game.id)
        """
        stmt = select(Game).where(Game.id == game_id)
        game = self.db.execute(stmt).scalar_one_or_none()

        if game is None:
            raise ValueError(f"Game with id {game_id} not found")

        # Update external_ids (create new dict to trigger SQLAlchemy change detection)
        new_external_ids = dict(game.external_ids)
        new_external_ids[source] = external_id
        game.external_ids = new_external_ids
        self.db.flush()

    def get_game_by_external_id(self, source: str, external_id: str) -> Game | None:
        """
        Get the internal game record for an external ID.

        Args:
            source: Name of the sync source
            external_id: External game ID from the source

        Returns:
            Game model instance if found, None otherwise

        Example:
            >>> game = tracker.get_game_by_external_id("winner", "game-123")
            >>> if game:
            ...     print(f"Found game: {game.id}")
        """
        return self._find_game_by_external_id(source, external_id)

    def get_external_id(self, game: Game, source: str) -> str | None:
        """
        Get the external ID for a game from a specific source.

        Args:
            game: Game model instance
            source: Name of the sync source

        Returns:
            External ID if present, None otherwise

        Example:
            >>> external_id = tracker.get_external_id(game, "winner")
            >>> print(external_id)
            "game-123"
        """
        return game.external_ids.get(source)

    def _find_game_by_external_id(self, source: str, external_id: str) -> Game | None:
        """
        Find a game by its external ID from a specific source.

        Uses JSON containment query to search the external_ids field.

        Args:
            source: Name of the sync source
            external_id: External game ID to find

        Returns:
            Game if found, None otherwise
        """
        # Query games where external_ids contains the source->external_id mapping
        # SQLite JSON support: use json_extract
        stmt = select(Game).where(Game.external_ids[source].as_string() == external_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def _get_synced_external_ids(
        self, source: str, external_ids: list[str]
    ) -> set[str]:
        """
        Get set of external IDs that are already synced.

        Args:
            source: Name of the sync source
            external_ids: List of external IDs to check

        Returns:
            Set of external IDs that exist in the database
        """
        synced: set[str] = set()

        # Query all games that have external_ids for this source
        stmt = select(Game).where(Game.external_ids[source].as_string().isnot(None))
        games = self.db.execute(stmt).scalars().all()

        for game in games:
            ext_id = game.external_ids.get(source)
            if ext_id in external_ids:
                synced.add(ext_id)

        return synced

    def has_pbp(self, game_id: UUID) -> bool:
        """
        Check if a game has play-by-play events.

        Args:
            game_id: Internal UUID of the game

        Returns:
            True if the game has at least one PBP event
        """
        from src.models.play_by_play import PlayByPlayEvent

        stmt = (
            select(PlayByPlayEvent.id)
            .where(PlayByPlayEvent.game_id == game_id)
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def get_games_without_pbp(
        self, source: str, external_ids: list[str]
    ) -> list[tuple[str, Game]]:
        """
        Get games that exist but don't have PBP.

        Args:
            source: Name of the sync source
            external_ids: List of external IDs to check

        Returns:
            List of (external_id, Game) tuples for games without PBP
        """
        result = []

        stmt = select(Game).where(Game.external_ids[source].as_string().isnot(None))
        games = self.db.execute(stmt).scalars().all()

        for game in games:
            ext_id = game.external_ids.get(source)
            if ext_id in external_ids and not self.has_pbp(game.id):
                result.append((ext_id, game))

        return result
