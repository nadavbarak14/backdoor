"""
League and Season Schema Module

Pydantic schemas for league and season-related API operations:
- LeagueCreate, LeagueUpdate: Request validation for league CRUD
- LeagueResponse, LeagueListResponse: Response serialization for leagues
- SeasonCreate, SeasonUpdate: Request validation for season CRUD
- SeasonResponse: Response serialization for seasons
- SeasonFilter: Query parameter validation for season filtering

Usage:
    from src.schemas.league import LeagueCreate, LeagueResponse

    @router.post("/leagues", response_model=LeagueResponse)
    def create_league(data: LeagueCreate):
        ...
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.base import OrmBase

# =============================================================================
# League Schemas
# =============================================================================


class LeagueCreate(BaseModel):
    """
    Schema for creating a new league.

    All fields are required for league creation.

    Attributes:
        name: Full league name (e.g., "National Basketball Association").
        code: Short unique code (e.g., "NBA").
        country: Country where the league is based.

    Example:
        >>> data = LeagueCreate(
        ...     name="National Basketball Association",
        ...     code="NBA",
        ...     country="United States"
        ... )
    """

    name: str = Field(..., min_length=1, max_length=100, description="Full league name")
    code: str = Field(
        ..., min_length=1, max_length=20, description="Short unique league code"
    )
    country: str = Field(
        ..., min_length=1, max_length=100, description="Country where league is based"
    )


class LeagueUpdate(BaseModel):
    """
    Schema for updating an existing league.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: Full league name (optional).
        code: Short unique code (optional).
        country: Country where the league is based (optional).

    Example:
        >>> data = LeagueUpdate(name="Updated League Name")
    """

    name: str | None = Field(
        None, min_length=1, max_length=100, description="Full league name"
    )
    code: str | None = Field(
        None, min_length=1, max_length=20, description="Short unique league code"
    )
    country: str | None = Field(
        None, min_length=1, max_length=100, description="Country where league is based"
    )


class LeagueResponse(OrmBase):
    """
    Schema for league API response.

    Includes all league data plus computed season count.
    Compatible with ORM objects via model_validate().

    Attributes:
        id: Unique league identifier.
        name: Full league name.
        code: Short unique league code.
        country: Country where league is based.
        season_count: Number of seasons in this league.
        created_at: Timestamp when league was created.
        updated_at: Timestamp when league was last updated.

    Example:
        >>> league_orm = session.get(League, league_id)
        >>> response = LeagueResponse.model_validate(league_orm)
    """

    id: UUID
    name: str
    code: str
    country: str
    season_count: int = Field(default=0, description="Number of seasons in this league")
    created_at: datetime
    updated_at: datetime


class LeagueListResponse(BaseModel):
    """
    Schema for paginated league list response.

    Attributes:
        items: List of leagues for the current page.
        total: Total number of leagues across all pages.

    Example:
        >>> response = LeagueListResponse(items=[league1, league2], total=50)
    """

    items: list[LeagueResponse]
    total: int


# =============================================================================
# Season Schemas
# =============================================================================


class SeasonCreate(BaseModel):
    """
    Schema for creating a new season.

    Attributes:
        league_id: UUID of the league this season belongs to.
        name: Season identifier (e.g., "2023-24").
        start_date: Season start date.
        end_date: Season end date.
        is_current: Whether this is the current active season.

    Example:
        >>> from datetime import date
        >>> data = SeasonCreate(
        ...     league_id=league_uuid,
        ...     name="2023-24",
        ...     start_date=date(2023, 10, 1),
        ...     end_date=date(2024, 6, 30),
        ...     is_current=True
        ... )
    """

    league_id: UUID = Field(..., description="UUID of the league")
    name: str = Field(
        ..., min_length=1, max_length=50, description="Season identifier (e.g., 2023-24)"
    )
    start_date: date = Field(..., description="Season start date")
    end_date: date = Field(..., description="Season end date")
    is_current: bool = Field(
        default=False, description="Whether this is the current active season"
    )


class SeasonUpdate(BaseModel):
    """
    Schema for updating an existing season.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: Season identifier (optional).
        start_date: Season start date (optional).
        end_date: Season end date (optional).
        is_current: Whether this is the current active season (optional).

    Example:
        >>> data = SeasonUpdate(is_current=False)
    """

    name: str | None = Field(
        None, min_length=1, max_length=50, description="Season identifier"
    )
    start_date: date | None = Field(None, description="Season start date")
    end_date: date | None = Field(None, description="Season end date")
    is_current: bool | None = Field(
        None, description="Whether this is the current active season"
    )


class SeasonResponse(OrmBase):
    """
    Schema for season API response.

    Compatible with ORM objects via model_validate().

    Attributes:
        id: Unique season identifier.
        league_id: UUID of the league this season belongs to.
        name: Season identifier (e.g., "2023-24").
        start_date: Season start date.
        end_date: Season end date.
        is_current: Whether this is the current active season.
        created_at: Timestamp when season was created.
        updated_at: Timestamp when season was last updated.

    Example:
        >>> season_orm = session.get(Season, season_id)
        >>> response = SeasonResponse.model_validate(season_orm)
    """

    id: UUID
    league_id: UUID
    name: str
    start_date: date
    end_date: date
    is_current: bool
    created_at: datetime
    updated_at: datetime


class SeasonFilter(BaseModel):
    """
    Schema for filtering seasons in list queries.

    Used as query parameters for season list endpoints.
    All fields are optional filters.

    Attributes:
        league_id: Filter by league UUID.
        is_current: Filter by current season status.

    Example:
        >>> # In FastAPI endpoint
        >>> @router.get("/seasons")
        >>> def list_seasons(filters: SeasonFilter = Depends()):
        ...     ...
    """

    league_id: UUID | None = Field(None, description="Filter by league UUID")
    is_current: bool | None = Field(None, description="Filter by current season status")
