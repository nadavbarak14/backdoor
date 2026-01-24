"""
Game Service Module

Provides business logic for game operations in the Basketball Analytics Platform.

This module exports:
    - GameService: CRUD and query operations for games

Usage:
    from src.services.game import GameService

    service = GameService(db_session)
    game = service.get_with_box_score(game_id)
    if game:
        print(f"Home: {game.home_score}, Away: {game.away_score}")

The service handles all game-related business logic including filtering,
box score loading, external ID lookups, and score updates.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.types import String

from src.models.game import Game, PlayerGameStats, TeamGameStats
from src.schemas.game import GameCreate, GameFilter, GameStatus, GameUpdate
from src.services.base import BaseService


class GameService(BaseService[Game]):
    """
    Service for game-related business operations.

    Extends BaseService with game-specific methods including filtering
    by various criteria, box score loading, external ID lookups,
    and score updates.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The Game model class.

    Example:
        >>> service = GameService(db_session)
        >>> game = service.get_with_box_score(game_id)
        >>> if game:
        ...     print(f"Final: {game.home_score} - {game.away_score}")
        ...     for stats in game.player_game_stats:
        ...         print(f"{stats.player.first_name}: {stats.points} pts")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the game service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = GameService(db_session)
        """
        super().__init__(db, Game)

    def get_with_box_score(self, game_id: UUID) -> Game | None:
        """
        Retrieve a game with all box score data eagerly loaded.

        Loads the game with team stats, player stats, and related entities
        (teams, players) in a single query using joins.

        Args:
            game_id: UUID of the game.

        Returns:
            The Game with all stats loaded, or None if not found.

        Example:
            >>> game = service.get_with_box_score(game_id)
            >>> if game:
            ...     for ts in game.team_game_stats:
            ...         print(f"{ts.team.name}: {ts.points} pts")
            ...     for ps in game.player_game_stats:
            ...         print(f"{ps.player.first_name}: {ps.points} pts")
        """
        stmt = (
            select(Game)
            .options(
                joinedload(Game.home_team),
                joinedload(Game.away_team),
                joinedload(Game.season),
                joinedload(Game.team_game_stats).joinedload(TeamGameStats.team),
                joinedload(Game.player_game_stats).joinedload(PlayerGameStats.player),
                joinedload(Game.player_game_stats).joinedload(PlayerGameStats.team),
            )
            .where(Game.id == game_id)
        )
        return self.db.scalars(stmt).unique().first()

    def get_filtered(
        self, filter_params: GameFilter, skip: int = 0, limit: int = 50
    ) -> tuple[list[Game], int]:
        """
        Retrieve games with filtering and pagination.

        Supports filtering by season, team (home or away), date range,
        and status. Returns both the games and total count for pagination.

        Args:
            filter_params: GameFilter schema with filter criteria.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 50.

        Returns:
            Tuple of (list of games, total count matching filters).

        Example:
            >>> from src.schemas.game import GameFilter, GameStatus
            >>> from datetime import date
            >>> filters = GameFilter(
            ...     season_id=season_uuid,
            ...     team_id=lakers_uuid,
            ...     status=GameStatus.FINAL
            ... )
            >>> games, total = service.get_filtered(filters, skip=0, limit=10)
            >>> print(f"Found {total} completed games for the Lakers")
        """
        stmt = select(Game).options(
            joinedload(Game.home_team),
            joinedload(Game.away_team),
        )

        if filter_params.season_id:
            stmt = stmt.where(Game.season_id == filter_params.season_id)

        if filter_params.team_id:
            stmt = stmt.where(
                or_(
                    Game.home_team_id == filter_params.team_id,
                    Game.away_team_id == filter_params.team_id,
                )
            )

        if filter_params.start_date:
            start_datetime = datetime.combine(
                filter_params.start_date, datetime.min.time()
            )
            stmt = stmt.where(Game.game_date >= start_datetime)

        if filter_params.end_date:
            end_datetime = datetime.combine(filter_params.end_date, datetime.max.time())
            stmt = stmt.where(Game.game_date <= end_datetime)

        if filter_params.status:
            stmt = stmt.where(Game.status == filter_params.status.value)

        # Order by game date descending (most recent first)
        stmt = stmt.order_by(Game.game_date.desc())

        # Count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)
        games = list(self.db.scalars(stmt).unique().all())

        return games, total

    def get_by_team(
        self,
        team_id: UUID,
        season_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Game], int]:
        """
        Retrieve games for a specific team.

        Returns games where the team played as either home or away.
        Optionally filtered by season.

        Args:
            team_id: UUID of the team.
            season_id: Optional UUID of the season to filter by.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 50.

        Returns:
            Tuple of (list of games, total count).

        Example:
            >>> games, total = service.get_by_team(
            ...     team_id=lakers_id,
            ...     season_id=season_2024_id,
            ...     skip=0,
            ...     limit=10
            ... )
            >>> print(f"Found {total} games for Lakers in this season")
        """
        stmt = (
            select(Game)
            .options(
                joinedload(Game.home_team),
                joinedload(Game.away_team),
            )
            .where(
                or_(
                    Game.home_team_id == team_id,
                    Game.away_team_id == team_id,
                )
            )
        )

        if season_id:
            stmt = stmt.where(Game.season_id == season_id)

        stmt = stmt.order_by(Game.game_date.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        games = list(self.db.scalars(stmt).unique().all())

        return games, total

    def get_by_external_id(self, source: str, external_id: str) -> Game | None:
        """
        Find a game by its external provider ID.

        Uses JSON field query to match provider-specific identifiers
        stored in the external_ids column.

        Args:
            source: The data provider name (e.g., "winner", "nba").
            external_id: The ID from the external provider.

        Returns:
            The Game if found, None otherwise.

        Example:
            >>> game = service.get_by_external_id("winner", "12345")
            >>> if game:
            ...     print(f"Found game: {game.home_team.name} vs {game.away_team.name}")
        """
        stmt = (
            select(Game)
            .options(
                joinedload(Game.home_team),
                joinedload(Game.away_team),
            )
            .where(
                cast(func.json_extract(Game.external_ids, f"$.{source}"), String)
                == external_id
            )
        )
        return self.db.scalars(stmt).unique().first()

    def create_game(self, data: GameCreate) -> Game:
        """
        Create a new game from a Pydantic schema.

        Args:
            data: GameCreate schema with validated game data.

        Returns:
            The newly created Game entity.

        Example:
            >>> from src.schemas.game import GameCreate
            >>> from datetime import datetime
            >>> data = GameCreate(
            ...     season_id=season_uuid,
            ...     home_team_id=lakers_uuid,
            ...     away_team_id=celtics_uuid,
            ...     game_date=datetime(2024, 1, 15, 19, 30),
            ...     venue="Crypto.com Arena"
            ... )
            >>> game = service.create_game(data)
        """
        game_data = data.model_dump()
        if game_data.get("external_ids") is None:
            game_data["external_ids"] = {}
        if "status" in game_data and hasattr(game_data["status"], "value"):
            game_data["status"] = game_data["status"].value
        return self.create(game_data)

    def update_game(self, game_id: UUID, data: GameUpdate) -> Game | None:
        """
        Update an existing game from a Pydantic schema.

        Args:
            game_id: UUID of the game to update.
            data: GameUpdate schema with fields to update.

        Returns:
            The updated Game if found, None otherwise.

        Example:
            >>> from src.schemas.game import GameUpdate, GameStatus
            >>> data = GameUpdate(
            ...     status=GameStatus.FINAL,
            ...     home_score=112,
            ...     away_score=108
            ... )
            >>> game = service.update_game(game_id, data)
        """
        update_data = data.model_dump(exclude_unset=True)
        if "status" in update_data and hasattr(update_data["status"], "value"):
            update_data["status"] = update_data["status"].value
        return self.update(game_id, update_data)

    def update_score(
        self,
        game_id: UUID,
        home_score: int,
        away_score: int,
        status: GameStatus = GameStatus.FINAL,
    ) -> Game | None:
        """
        Update game score and status.

        Convenience method for updating just the score and status
        of a game, typically used when a game ends.

        Args:
            game_id: UUID of the game.
            home_score: Final score of the home team.
            away_score: Final score of the away team.
            status: Game status to set. Defaults to FINAL.

        Returns:
            The updated Game if found, None otherwise.

        Example:
            >>> game = service.update_score(
            ...     game_id=game_uuid,
            ...     home_score=112,
            ...     away_score=108,
            ...     status=GameStatus.FINAL
            ... )
            >>> if game:
            ...     print(f"Final score: {game.home_score} - {game.away_score}")
        """
        return self.update(
            game_id,
            {
                "home_score": home_score,
                "away_score": away_score,
                "status": status.value,
            },
        )
