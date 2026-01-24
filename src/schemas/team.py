"""
Team Schema Module

Pydantic schemas for team-related API operations:
- TeamCreate, TeamUpdate: Request validation for team CRUD
- TeamResponse, TeamListResponse: Response serialization for teams
- TeamFilter: Query parameter validation for team filtering
- TeamRosterPlayerResponse, TeamRosterResponse: Team roster responses

Usage:
    from src.schemas.team import TeamCreate, TeamResponse

    @router.post("/teams", response_model=TeamResponse)
    def create_team(data: TeamCreate):
        ...
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.base import OrmBase


class TeamCreate(BaseModel):
    """
    Schema for creating a new team.

    Attributes:
        name: Full team name (e.g., "Los Angeles Lakers").
        short_name: Abbreviated team name (e.g., "LAL").
        city: Team's home city.
        country: Team's country.
        external_ids: Optional dict mapping provider names to their IDs.

    Example:
        >>> data = TeamCreate(
        ...     name="Los Angeles Lakers",
        ...     short_name="LAL",
        ...     city="Los Angeles",
        ...     country="United States",
        ...     external_ids={"nba": "1610612747"}
        ... )
    """

    name: str = Field(..., min_length=1, max_length=100, description="Full team name")
    short_name: str = Field(
        ..., min_length=1, max_length=20, description="Abbreviated team name"
    )
    city: str = Field(..., min_length=1, max_length=100, description="Team's home city")
    country: str = Field(
        ..., min_length=1, max_length=100, description="Team's country"
    )
    external_ids: dict[str, str] | None = Field(
        default=None, description="External provider ID mappings"
    )


class TeamUpdate(BaseModel):
    """
    Schema for updating an existing team.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: Full team name (optional).
        short_name: Abbreviated team name (optional).
        city: Team's home city (optional).
        country: Team's country (optional).
        external_ids: External provider ID mappings (optional).

    Example:
        >>> data = TeamUpdate(city="San Francisco")
    """

    name: str | None = Field(
        None, min_length=1, max_length=100, description="Full team name"
    )
    short_name: str | None = Field(
        None, min_length=1, max_length=20, description="Abbreviated team name"
    )
    city: str | None = Field(
        None, min_length=1, max_length=100, description="Team's home city"
    )
    country: str | None = Field(
        None, min_length=1, max_length=100, description="Team's country"
    )
    external_ids: dict[str, str] | None = Field(
        None, description="External provider ID mappings"
    )


class TeamResponse(OrmBase):
    """
    Schema for team API response.

    Compatible with ORM objects via model_validate().

    Attributes:
        id: Unique team identifier.
        name: Full team name.
        short_name: Abbreviated team name.
        city: Team's home city.
        country: Team's country.
        external_ids: External provider ID mappings.
        created_at: Timestamp when team was created.
        updated_at: Timestamp when team was last updated.

    Example:
        >>> team_orm = session.get(Team, team_id)
        >>> response = TeamResponse.model_validate(team_orm)
    """

    id: UUID
    name: str
    short_name: str
    city: str
    country: str
    external_ids: dict[str, str]
    created_at: datetime
    updated_at: datetime


class TeamListResponse(BaseModel):
    """
    Schema for paginated team list response.

    Attributes:
        items: List of teams for the current page.
        total: Total number of teams across all pages.

    Example:
        >>> response = TeamListResponse(items=[team1, team2], total=30)
    """

    items: list[TeamResponse]
    total: int


class TeamFilter(BaseModel):
    """
    Schema for filtering teams in list queries.

    Used as query parameters for team list endpoints.
    All fields are optional filters.

    Attributes:
        league_id: Filter by league UUID (teams with seasons in this league).
        season_id: Filter by season UUID (teams playing in this season).
        country: Filter by country name.
        search: Search term for team name or short name.

    Example:
        >>> # In FastAPI endpoint
        >>> @router.get("/teams")
        >>> def list_teams(filters: TeamFilter = Depends()):
        ...     ...
    """

    league_id: UUID | None = Field(
        None, description="Filter by league (teams with seasons in this league)"
    )
    season_id: UUID | None = Field(
        None, description="Filter by season (teams playing in this season)"
    )
    country: str | None = Field(None, description="Filter by country name")
    search: str | None = Field(
        None, min_length=1, description="Search term for team name or short name"
    )


class TeamRosterPlayerResponse(OrmBase):
    """
    Schema for player info within a team roster context.

    Represents a player's information as part of a team's roster,
    including their role on that specific team.

    Attributes:
        id: Unique player identifier.
        first_name: Player's first name.
        last_name: Player's last name.
        full_name: Player's full name (computed).
        jersey_number: Player's jersey number on this team.
        position: Player's position on this team.

    Example:
        >>> player = TeamRosterPlayerResponse(
        ...     id=player_uuid,
        ...     first_name="LeBron",
        ...     last_name="James",
        ...     full_name="LeBron James",
        ...     jersey_number=23,
        ...     position="SF"
        ... )
    """

    id: UUID
    first_name: str
    last_name: str
    full_name: str
    jersey_number: int | None
    position: str | None


class TeamRosterResponse(OrmBase):
    """
    Schema for complete team roster response.

    Includes team info, season context, and list of players.

    Attributes:
        team: Team information.
        season_id: Season UUID for this roster.
        season_name: Season name (e.g., "2023-24").
        players: List of players on the roster.

    Example:
        >>> response = TeamRosterResponse(
        ...     team=team_response,
        ...     season_id=season_uuid,
        ...     season_name="2023-24",
        ...     players=[player1, player2]
        ... )
    """

    team: TeamResponse
    season_id: UUID
    season_name: str
    players: list[TeamRosterPlayerResponse]
