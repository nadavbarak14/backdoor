"""
League Service Module

Provides business logic for league and season operations in the
Basketball Analytics Platform.

This module exports:
    - LeagueService: CRUD and query operations for leagues
    - SeasonService: CRUD and query operations for seasons

Usage:
    from src.services.league import LeagueService, SeasonService

    league_service = LeagueService(db_session)
    league = league_service.get_by_code("NBA")

    season_service = SeasonService(db_session)
    current = season_service.get_current(league.id)

The services handle all business logic for leagues and seasons including
finding leagues by code, counting seasons, and managing the current season.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.schemas.league import LeagueCreate, LeagueUpdate, SeasonCreate, SeasonUpdate
from src.services.base import BaseService


class LeagueService(BaseService[League]):
    """
    Service for league-related business operations.

    Extends BaseService with league-specific methods including finding
    leagues by code and retrieving leagues with season counts.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The League model class.

    Example:
        >>> service = LeagueService(db_session)
        >>> nba = service.get_by_code("NBA")
        >>> if nba:
        ...     print(f"{nba.name} has seasons")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the league service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = LeagueService(db_session)
        """
        super().__init__(db, League)

    def get_by_code(self, code: str) -> League | None:
        """
        Find a league by its unique code.

        Args:
            code: The unique short code of the league (e.g., "NBA").

        Returns:
            The League if found, None otherwise.

        Example:
            >>> nba = service.get_by_code("NBA")
            >>> if nba:
            ...     print(nba.name)  # "National Basketball Association"
        """
        stmt = select(League).where(League.code == code)
        return self.db.scalars(stmt).first()

    def get_with_season_count(self, league_id: UUID) -> tuple[League | None, int]:
        """
        Retrieve a league with its season count.

        Args:
            league_id: UUID of the league.

        Returns:
            Tuple of (League or None, season_count). If league is not found,
            returns (None, 0).

        Example:
            >>> league, count = service.get_with_season_count(league_id)
            >>> if league:
            ...     print(f"{league.name} has {count} seasons")
        """
        league = self.get_by_id(league_id)
        if league is None:
            return None, 0

        count_stmt = (
            select(func.count())
            .select_from(Season)
            .where(Season.league_id == league_id)
        )
        count = self.db.execute(count_stmt).scalar() or 0
        return league, count

    def get_all_with_season_counts(
        self, skip: int = 0, limit: int = 100
    ) -> list[tuple[League, int]]:
        """
        Retrieve all leagues with their season counts.

        Args:
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 100.

        Returns:
            List of tuples containing (League, season_count).

        Example:
            >>> leagues_with_counts = service.get_all_with_season_counts()
            >>> for league, count in leagues_with_counts:
            ...     print(f"{league.name}: {count} seasons")
        """
        stmt = (
            select(League, func.count(Season.id).label("season_count"))
            .outerjoin(Season, League.id == Season.league_id)
            .group_by(League.id)
            .offset(skip)
            .limit(limit)
        )
        results = self.db.execute(stmt).all()
        return [(row[0], row[1]) for row in results]

    def create_league(self, data: LeagueCreate) -> League:
        """
        Create a new league from a Pydantic schema.

        Args:
            data: LeagueCreate schema with validated league data.

        Returns:
            The newly created League entity.

        Example:
            >>> from src.schemas.league import LeagueCreate
            >>> data = LeagueCreate(name="NBA", code="NBA", country="USA")
            >>> league = service.create_league(data)
            >>> print(league.id)
        """
        return self.create(data.model_dump())

    def update_league(self, league_id: UUID, data: LeagueUpdate) -> League | None:
        """
        Update an existing league from a Pydantic schema.

        Args:
            league_id: UUID of the league to update.
            data: LeagueUpdate schema with fields to update.

        Returns:
            The updated League if found, None otherwise.

        Example:
            >>> from src.schemas.league import LeagueUpdate
            >>> data = LeagueUpdate(name="Updated Name")
            >>> league = service.update_league(league_id, data)
        """
        return self.update(league_id, data.model_dump(exclude_unset=True))


class SeasonService(BaseService[Season]):
    """
    Service for season-related business operations.

    Extends BaseService with season-specific methods including finding
    seasons by league, getting current seasons, and managing is_current flags.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The Season model class.

    Example:
        >>> service = SeasonService(db_session)
        >>> current = service.get_current(league_id)
        >>> if current:
        ...     print(f"Current season: {current.name}")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the season service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = SeasonService(db_session)
        """
        super().__init__(db, Season)

    def get_by_league(
        self, league_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Season]:
        """
        Retrieve all seasons for a specific league.

        Args:
            league_id: UUID of the league.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 100.

        Returns:
            List of seasons belonging to the specified league.

        Example:
            >>> seasons = service.get_by_league(nba_id)
            >>> for season in seasons:
            ...     print(f"{season.name}: {season.start_date}")
        """
        stmt = (
            select(Season)
            .where(Season.league_id == league_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_current(self, league_id: UUID | None = None) -> Season | None:
        """
        Get the current active season.

        Args:
            league_id: Optional UUID of a specific league. If provided,
                returns the current season for that league. If None,
                returns any current season.

        Returns:
            The current Season if found, None otherwise.

        Example:
            >>> # Get current season for a specific league
            >>> current = service.get_current(nba_id)
            >>> # Get any current season
            >>> any_current = service.get_current()
        """
        stmt = select(Season).where(Season.is_current == True)  # noqa: E712
        if league_id is not None:
            stmt = stmt.where(Season.league_id == league_id)
        return self.db.scalars(stmt).first()

    def create_season(self, data: SeasonCreate) -> Season:
        """
        Create a new season from a Pydantic schema.

        If the new season is marked as current, other seasons in the
        same league will be unmarked automatically.

        Args:
            data: SeasonCreate schema with validated season data.

        Returns:
            The newly created Season entity.

        Example:
            >>> from src.schemas.league import SeasonCreate
            >>> from datetime import date
            >>> data = SeasonCreate(
            ...     league_id=nba_id,
            ...     name="2024-25",
            ...     start_date=date(2024, 10, 22),
            ...     end_date=date(2025, 6, 15),
            ...     is_current=True
            ... )
            >>> season = service.create_season(data)
        """
        if data.is_current:
            self._unset_current_in_league(data.league_id)
        return self.create(data.model_dump())

    def set_current(self, season_id: UUID) -> Season | None:
        """
        Mark a season as the current season.

        Automatically unsets is_current on other seasons in the same league.

        Args:
            season_id: UUID of the season to mark as current.

        Returns:
            The updated Season if found, None otherwise.

        Example:
            >>> season = service.set_current(season_id)
            >>> if season:
            ...     print(f"{season.name} is now current")
        """
        season = self.get_by_id(season_id)
        if season is None:
            return None

        self._unset_current_in_league(season.league_id)

        season.is_current = True
        self.db.commit()
        self.db.refresh(season)
        return season

    def _unset_current_in_league(self, league_id: UUID) -> None:
        """
        Unset is_current flag on all seasons in a league.

        This is a helper method used when setting a new current season.

        Args:
            league_id: UUID of the league to update.
        """
        stmt = (
            select(Season)
            .where(Season.league_id == league_id)
            .where(Season.is_current == True)  # noqa: E712
        )
        current_seasons = self.db.scalars(stmt).all()
        for season in current_seasons:
            season.is_current = False
        self.db.flush()

    def update_season(self, season_id: UUID, data: SeasonUpdate) -> Season | None:
        """
        Update an existing season from a Pydantic schema.

        If is_current is set to True, other seasons in the same league
        will be unmarked automatically.

        Args:
            season_id: UUID of the season to update.
            data: SeasonUpdate schema with fields to update.

        Returns:
            The updated Season if found, None otherwise.

        Example:
            >>> from src.schemas.league import SeasonUpdate
            >>> data = SeasonUpdate(is_current=True)
            >>> season = service.update_season(season_id, data)
        """
        if data.is_current is True:
            season = self.get_by_id(season_id)
            if season:
                self._unset_current_in_league(season.league_id)

        return self.update(season_id, data.model_dump(exclude_unset=True))
