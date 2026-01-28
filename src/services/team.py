"""
Team Service Module

Provides business logic for team operations in the Basketball Analytics Platform.

This module exports:
    - TeamService: CRUD and query operations for teams

Usage:
    from src.services.team import TeamService

    service = TeamService(db_session)
    team = service.get_by_external_id("nba", "1610612747")
    if team:
        roster = service.get_roster(team.id, season_id)

The service handles all team-related business logic including filtering,
external ID lookups, roster retrieval, and season associations.
"""

from uuid import UUID

from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.types import String

from src.models.league import Season
from src.models.player import PlayerTeamHistory
from src.models.team import Team, TeamSeason
from src.schemas.team import TeamCreate, TeamFilter, TeamUpdate
from src.services.base import BaseService


class TeamService(BaseService[Team]):
    """
    Service for team-related business operations.

    Extends BaseService with team-specific methods including filtering
    by various criteria, external ID lookups, and roster management.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The Team model class.

    Example:
        >>> service = TeamService(db_session)
        >>> teams, total = service.get_filtered(
        ...     TeamFilter(country="USA"),
        ...     skip=0,
        ...     limit=20
        ... )
        >>> print(f"Found {total} teams in USA")
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the team service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = TeamService(db_session)
        """
        super().__init__(db, Team)

    def get_filtered(
        self, filter_params: TeamFilter, skip: int = 0, limit: int = 100
    ) -> tuple[list[Team], int]:
        """
        Retrieve teams with filtering and pagination.

        Supports filtering by league, season, country, and name search.
        Returns both the teams and total count for pagination.

        Args:
            filter_params: TeamFilter schema with filter criteria.
            skip: Number of records to skip (offset). Defaults to 0.
            limit: Maximum number of records to return. Defaults to 100.

        Returns:
            Tuple of (list of teams, total count matching filters).

        Example:
            >>> from src.schemas.team import TeamFilter
            >>> filters = TeamFilter(country="USA", search="Lakers")
            >>> teams, total = service.get_filtered(filters, skip=0, limit=10)
            >>> print(f"Found {total} teams, showing {len(teams)}")
        """
        stmt = select(Team)

        if filter_params.season_id:
            stmt = stmt.join(TeamSeason).where(
                TeamSeason.season_id == filter_params.season_id
            )

        if filter_params.league_id:
            stmt = (
                stmt.join(TeamSeason, Team.id == TeamSeason.team_id)
                .join(Season, TeamSeason.season_id == Season.id)
                .where(Season.league_id == filter_params.league_id)
            )
            stmt = stmt.distinct()

        if filter_params.country:
            stmt = stmt.where(Team.country == filter_params.country)

        if filter_params.search:
            search_term = f"%{filter_params.search}%"
            stmt = stmt.where(
                or_(
                    Team.name.ilike(search_term),
                    Team.short_name.ilike(search_term),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        teams = list(self.db.scalars(stmt).all())

        return teams, total

    def get_by_external_id(self, source: str, external_id: str) -> Team | None:
        """
        Find a team by its external provider ID.

        Uses JSON field query to match provider-specific identifiers
        stored in the external_ids column.

        Args:
            source: The data provider name (e.g., "nba", "euroleague").
            external_id: The ID from the external provider.

        Returns:
            The Team if found, None otherwise.

        Example:
            >>> team = service.get_by_external_id("nba", "1610612747")
            >>> if team:
            ...     print(team.name)  # "Los Angeles Lakers"
        """
        # Use json_extract for SQLite compatibility (also works with PostgreSQL)
        stmt = select(Team).where(
            cast(func.json_extract(Team.external_ids, f"$.{source}"), String)
            == external_id
        )
        return self.db.scalars(stmt).first()

    def get_roster(self, team_id: UUID, season_id: UUID) -> list[PlayerTeamHistory]:
        """
        Get the roster for a team in a specific season.

        Returns PlayerTeamHistory entries with player relationship loaded.

        Args:
            team_id: UUID of the team.
            season_id: UUID of the season.

        Returns:
            List of PlayerTeamHistory entries for the team's roster.
            Each entry has the player relationship eagerly loaded.

        Example:
            >>> roster = service.get_roster(lakers_id, current_season_id)
            >>> for entry in roster:
            ...     print(f"#{entry.jersey_number} {entry.player.full_name}")
        """
        stmt = (
            select(PlayerTeamHistory)
            .options(joinedload(PlayerTeamHistory.player))
            .where(PlayerTeamHistory.team_id == team_id)
            .where(PlayerTeamHistory.season_id == season_id)
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_team_seasons(self, team_id: UUID) -> list[TeamSeason]:
        """
        Get all seasons a team has participated in.

        Args:
            team_id: UUID of the team.

        Returns:
            List of TeamSeason entries for the team.

        Example:
            >>> seasons = service.get_team_seasons(lakers_id)
            >>> for ts in seasons:
            ...     print(f"Season: {ts.season_id}")
        """
        stmt = select(TeamSeason).where(TeamSeason.team_id == team_id)
        return list(self.db.scalars(stmt).all())

    def create_team(self, data: TeamCreate) -> Team:
        """
        Create a new team from a Pydantic schema.

        Args:
            data: TeamCreate schema with validated team data.

        Returns:
            The newly created Team entity.

        Example:
            >>> from src.schemas.team import TeamCreate
            >>> data = TeamCreate(
            ...     name="Los Angeles Lakers",
            ...     short_name="LAL",
            ...     city="Los Angeles",
            ...     country="USA",
            ...     external_ids={"nba": "1610612747"}
            ... )
            >>> team = service.create_team(data)
        """
        team_data = data.model_dump()
        if team_data.get("external_ids") is None:
            team_data["external_ids"] = {}
        return self.create(team_data)

    def update_team(self, team_id: UUID, data: TeamUpdate) -> Team | None:
        """
        Update an existing team from a Pydantic schema.

        Args:
            team_id: UUID of the team to update.
            data: TeamUpdate schema with fields to update.

        Returns:
            The updated Team if found, None otherwise.

        Example:
            >>> from src.schemas.team import TeamUpdate
            >>> data = TeamUpdate(city="San Francisco")
            >>> team = service.update_team(team_id, data)
        """
        return self.update(team_id, data.model_dump(exclude_unset=True))

    def add_to_season(self, team_id: UUID, season_id: UUID) -> TeamSeason | None:
        """
        Add a team to a season.

        Creates a TeamSeason association linking the team to the season.
        If the association already exists, returns the existing entry.

        Args:
            team_id: UUID of the team.
            season_id: UUID of the season.

        Returns:
            The TeamSeason association, or None if team or season not found.

        Example:
            >>> team_season = service.add_to_season(lakers_id, season_2024_id)
            >>> if team_season:
            ...     print(f"Team added to season")
        """
        existing_stmt = select(TeamSeason).where(
            TeamSeason.team_id == team_id,
            TeamSeason.season_id == season_id,
        )
        existing = self.db.scalars(existing_stmt).first()
        if existing:
            return existing

        team = self.get_by_id(team_id)
        if team is None:
            return None

        season_stmt = select(Season).where(Season.id == season_id)
        season = self.db.scalars(season_stmt).first()
        if season is None:
            return None

        team_season = TeamSeason(team_id=team_id, season_id=season_id)
        self.db.add(team_season)
        self.db.commit()
        self.db.refresh(team_season)
        return team_season
