"""
Player Service Module

Provides business logic for player operations in the Basketball Analytics Platform.

This module exports:
    - PlayerService: CRUD and query operations for players

Usage:
    from src.services.player import PlayerService

    service = PlayerService(db_session)
    player = service.get_by_external_id("nba", "2544")
    if player:
        history = service.get_team_history(player.id)

The service handles all player-related business logic including filtering,
external ID lookups, team history management, and team associations.
"""

from uuid import UUID

from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.types import String

from src.models.league import Season
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team
from src.schemas.player import PlayerCreate, PlayerFilter, PlayerUpdate
from src.services.base import BaseService


class PlayerService(BaseService[Player]):
    """
    Service for player-related business operations.

    Extends BaseService with player-specific methods including filtering
    by various criteria, external ID lookups, and team history management.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The Player model class.

    Example:
        >>> service = PlayerService(db_session)
        >>> player = service.get_with_history(player_id)
        >>> if player:
        ...     for history in player.team_histories:
        ...         print(f"{history.team.name}: {history.season.name}")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the player service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = PlayerService(db_session)
        """
        super().__init__(db, Player)

    def get_with_history(self, player_id: UUID) -> Player | None:
        """
        Retrieve a player with team history eagerly loaded.

        Loads the player with all related team_histories, and for each
        history entry, loads the associated team and season.

        Args:
            player_id: UUID of the player.

        Returns:
            The Player with team_histories loaded, or None if not found.

        Example:
            >>> player = service.get_with_history(player_id)
            >>> if player:
            ...     for h in player.team_histories:
            ...         print(f"{h.team.name} ({h.season.name})")
        """
        stmt = (
            select(Player)
            .options(
                joinedload(Player.team_histories)
                .joinedload(PlayerTeamHistory.team),
                joinedload(Player.team_histories)
                .joinedload(PlayerTeamHistory.season),
            )
            .where(Player.id == player_id)
        )
        return self.db.scalars(stmt).unique().first()

    def get_filtered(
        self, filter_params: PlayerFilter, skip: int = 0, limit: int = 100
    ) -> tuple[list[Player], int]:
        """
        Retrieve players with filtering and pagination.

        Supports filtering by team, season, position, nationality, and
        name search. Returns both the players and total count for pagination.

        Args:
            filter_params: PlayerFilter schema with filter criteria.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 100.

        Returns:
            Tuple of (list of players, total count matching filters).

        Example:
            >>> from src.schemas.player import PlayerFilter
            >>> filters = PlayerFilter(position="PG", search="Curry")
            >>> players, total = service.get_filtered(filters, skip=0, limit=10)
            >>> print(f"Found {total} point guards matching 'Curry'")
        """
        stmt = select(Player)

        if filter_params.team_id or filter_params.season_id:
            stmt = stmt.join(PlayerTeamHistory)

            if filter_params.team_id:
                stmt = stmt.where(
                    PlayerTeamHistory.team_id == filter_params.team_id
                )

            if filter_params.season_id:
                stmt = stmt.where(
                    PlayerTeamHistory.season_id == filter_params.season_id
                )

            stmt = stmt.distinct()

        if filter_params.position:
            stmt = stmt.where(Player.position == filter_params.position)

        if filter_params.nationality:
            stmt = stmt.where(Player.nationality == filter_params.nationality)

        if filter_params.search:
            search_term = f"%{filter_params.search}%"
            stmt = stmt.where(
                or_(
                    Player.first_name.ilike(search_term),
                    Player.last_name.ilike(search_term),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        players = list(self.db.scalars(stmt).all())

        return players, total

    def get_by_external_id(self, source: str, external_id: str) -> Player | None:
        """
        Find a player by their external provider ID.

        Uses JSON field query to match provider-specific identifiers
        stored in the external_ids column.

        Args:
            source: The data provider name (e.g., "nba", "euroleague").
            external_id: The ID from the external provider.

        Returns:
            The Player if found, None otherwise.

        Example:
            >>> player = service.get_by_external_id("nba", "2544")
            >>> if player:
            ...     print(player.full_name)  # "LeBron James"
        """
        # Use json_extract for SQLite compatibility (also works with PostgreSQL)
        stmt = select(Player).where(
            cast(
                func.json_extract(Player.external_ids, f"$.{source}"),
                String
            ) == external_id
        )
        return self.db.scalars(stmt).first()

    def create_player(self, data: PlayerCreate) -> Player:
        """
        Create a new player from a Pydantic schema.

        Args:
            data: PlayerCreate schema with validated player data.

        Returns:
            The newly created Player entity.

        Example:
            >>> from src.schemas.player import PlayerCreate
            >>> from datetime import date
            >>> data = PlayerCreate(
            ...     first_name="LeBron",
            ...     last_name="James",
            ...     birth_date=date(1984, 12, 30),
            ...     position="SF",
            ...     external_ids={"nba": "2544"}
            ... )
            >>> player = service.create_player(data)
        """
        player_data = data.model_dump()
        if player_data.get("external_ids") is None:
            player_data["external_ids"] = {}
        return self.create(player_data)

    def update_player(self, player_id: UUID, data: PlayerUpdate) -> Player | None:
        """
        Update an existing player from a Pydantic schema.

        Args:
            player_id: UUID of the player to update.
            data: PlayerUpdate schema with fields to update.

        Returns:
            The updated Player if found, None otherwise.

        Example:
            >>> from src.schemas.player import PlayerUpdate
            >>> data = PlayerUpdate(position="PF")
            >>> player = service.update_player(player_id, data)
        """
        return self.update(player_id, data.model_dump(exclude_unset=True))

    def add_to_team(
        self,
        player_id: UUID,
        team_id: UUID,
        season_id: UUID,
        jersey_number: int | None = None,
        position: str | None = None,
    ) -> PlayerTeamHistory | None:
        """
        Add a player to a team for a specific season.

        Creates a PlayerTeamHistory entry. If an entry already exists
        for this player/team/season combination, returns the existing entry.

        Args:
            player_id: UUID of the player.
            team_id: UUID of the team.
            season_id: UUID of the season.
            jersey_number: Optional jersey number for this team/season.
            position: Optional position for this team/season.

        Returns:
            The PlayerTeamHistory entry, or None if player/team/season not found.

        Example:
            >>> history = service.add_to_team(
            ...     player_id=lebron_id,
            ...     team_id=lakers_id,
            ...     season_id=season_2024_id,
            ...     jersey_number=23,
            ...     position="SF"
            ... )
        """
        existing_stmt = select(PlayerTeamHistory).where(
            PlayerTeamHistory.player_id == player_id,
            PlayerTeamHistory.team_id == team_id,
            PlayerTeamHistory.season_id == season_id,
        )
        existing = self.db.scalars(existing_stmt).first()
        if existing:
            return existing

        player = self.get_by_id(player_id)
        if player is None:
            return None

        team_stmt = select(Team).where(Team.id == team_id)
        team = self.db.scalars(team_stmt).first()
        if team is None:
            return None

        season_stmt = select(Season).where(Season.id == season_id)
        season = self.db.scalars(season_stmt).first()
        if season is None:
            return None

        history = PlayerTeamHistory(
            player_id=player_id,
            team_id=team_id,
            season_id=season_id,
            jersey_number=jersey_number,
            position=position,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def get_team_history(self, player_id: UUID) -> list[PlayerTeamHistory]:
        """
        Get all team history entries for a player.

        Returns PlayerTeamHistory entries with team and season relationships loaded.

        Args:
            player_id: UUID of the player.

        Returns:
            List of PlayerTeamHistory entries with team and season loaded.

        Example:
            >>> history = service.get_team_history(player_id)
            >>> for entry in history:
            ...     print(f"{entry.team.name} ({entry.season.name})")
        """
        stmt = (
            select(PlayerTeamHistory)
            .options(
                joinedload(PlayerTeamHistory.team),
                joinedload(PlayerTeamHistory.season),
            )
            .where(PlayerTeamHistory.player_id == player_id)
        )
        return list(self.db.scalars(stmt).unique().all())
