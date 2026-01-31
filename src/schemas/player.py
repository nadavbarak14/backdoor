"""
Player Schema Module

Pydantic schemas for player-related API operations:
- PlayerCreate, PlayerUpdate: Request validation for player CRUD
- PlayerResponse, PlayerListResponse: Response serialization for players
- PlayerFilter: Query parameter validation for player filtering
- PlayerTeamHistoryResponse: Team history for a player
- PlayerWithHistoryResponse: Player with full team history

Usage:
    from src.schemas.player import PlayerCreate, PlayerResponse

    @router.post("/players", response_model=PlayerResponse)
    def create_player(data: PlayerCreate):
        ...
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.base import OrmBase


class PlayerCreate(BaseModel):
    """
    Schema for creating a new player.

    Attributes:
        first_name: Player's first name.
        last_name: Player's last name.
        birth_date: Player's birth date (optional).
        nationality: Player's nationality/country code (optional).
        height_cm: Player's height in centimeters (100-250 range, optional).
        positions: List of player's positions (e.g., ["SF", "PF"]).
        external_ids: Optional dict mapping provider names to their IDs.

    Example:
        >>> from datetime import date
        >>> data = PlayerCreate(
        ...     first_name="LeBron",
        ...     last_name="James",
        ...     birth_date=date(1984, 12, 30),
        ...     nationality="United States",
        ...     height_cm=206,
        ...     positions=["SF", "PF"],
        ...     external_ids={"nba": "2544"}
        ... )
    """

    first_name: str = Field(
        ..., min_length=1, max_length=100, description="Player's first name"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=100, description="Player's last name"
    )
    birth_date: date | None = Field(None, description="Player's birth date")
    nationality: str | None = Field(
        None, max_length=100, description="Player's nationality or country code"
    )
    height_cm: int | None = Field(
        None, ge=100, le=250, description="Player's height in centimeters (100-250)"
    )
    positions: list[str] = Field(
        default_factory=list,
        description="List of positions (PG, SG, SF, PF, C, G, F)",
    )
    external_ids: dict[str, str] | None = Field(
        default=None, description="External provider ID mappings"
    )


class PlayerUpdate(BaseModel):
    """
    Schema for updating an existing player.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        first_name: Player's first name (optional).
        last_name: Player's last name (optional).
        birth_date: Player's birth date (optional).
        nationality: Player's nationality (optional).
        height_cm: Player's height in centimeters (optional).
        positions: List of player's positions (optional).
        external_ids: External provider ID mappings (optional).

    Example:
        >>> data = PlayerUpdate(positions=["PF", "C"])
    """

    first_name: str | None = Field(
        None, min_length=1, max_length=100, description="Player's first name"
    )
    last_name: str | None = Field(
        None, min_length=1, max_length=100, description="Player's last name"
    )
    birth_date: date | None = Field(None, description="Player's birth date")
    nationality: str | None = Field(
        None, max_length=100, description="Player's nationality or country code"
    )
    height_cm: int | None = Field(
        None, ge=100, le=250, description="Player's height in centimeters (100-250)"
    )
    positions: list[str] | None = Field(
        None,
        description="List of positions (PG, SG, SF, PF, C, G, F)",
    )
    external_ids: dict[str, str] | None = Field(
        None, description="External provider ID mappings"
    )


class PlayerResponse(OrmBase):
    """
    Schema for player API response.

    Includes full_name as a computed property from the ORM model.
    Compatible with ORM objects via model_validate().

    Attributes:
        id: Unique player identifier.
        first_name: Player's first name.
        last_name: Player's last name.
        full_name: Player's full name (computed from first_name + last_name).
        birth_date: Player's birth date.
        nationality: Player's nationality.
        height_cm: Player's height in centimeters.
        positions: List of player's positions.
        external_ids: External provider ID mappings.
        created_at: Timestamp when player was created.
        updated_at: Timestamp when player was last updated.

    Example:
        >>> player_orm = session.get(Player, player_id)
        >>> response = PlayerResponse.model_validate(player_orm)
        >>> print(response.full_name)
        'LeBron James'
    """

    id: UUID
    first_name: str
    last_name: str
    full_name: str
    birth_date: date | None
    nationality: str | None
    height_cm: int | None
    positions: list[str] = []
    external_ids: dict[str, str]
    created_at: datetime
    updated_at: datetime


class PlayerListResponse(BaseModel):
    """
    Schema for paginated player list response.

    Attributes:
        items: List of players for the current page.
        total: Total number of players across all pages.

    Example:
        >>> response = PlayerListResponse(items=[player1, player2], total=500)
    """

    items: list[PlayerResponse]
    total: int


class PlayerFilter(BaseModel):
    """
    Schema for filtering players in list queries.

    Used as query parameters for player list endpoints.
    All fields are optional filters.

    Attributes:
        team_id: Filter by team UUID (players currently on this team).
        season_id: Filter by season UUID (players active in this season).
        position: Filter by position (e.g., "PG", "C").
        nationality: Filter by nationality/country.
        search: Search term for player name.

    Example:
        >>> # In FastAPI endpoint
        >>> @router.get("/players")
        >>> def list_players(filters: PlayerFilter = Depends()):
        ...     ...
    """

    team_id: UUID | None = Field(None, description="Filter by team UUID")
    season_id: UUID | None = Field(None, description="Filter by season UUID")
    position: str | None = Field(None, description="Filter by position")
    nationality: str | None = Field(None, description="Filter by nationality/country")
    search: str | None = Field(
        None, min_length=1, description="Search term for player name"
    )


class PlayerTeamHistoryResponse(OrmBase):
    """
    Schema for a player's team history entry.

    Represents one team affiliation for a player during a specific season.

    Attributes:
        team_id: UUID of the team.
        team_name: Full name of the team.
        season_id: UUID of the season.
        season_name: Name of the season (e.g., "2023-24").
        jersey_number: Player's jersey number on this team.
        positions: Player's positions on this team (may differ from primary).

    Example:
        >>> history = PlayerTeamHistoryResponse(
        ...     team_id=team_uuid,
        ...     team_name="Los Angeles Lakers",
        ...     season_id=season_uuid,
        ...     season_name="2023-24",
        ...     jersey_number=23,
        ...     positions=["SF", "PF"]
        ... )
    """

    team_id: UUID
    team_name: str
    season_id: UUID
    season_name: str
    jersey_number: int | None
    positions: list[str] = []


class PlayerWithHistoryResponse(OrmBase):
    """
    Schema for player with complete team history.

    Includes full player data plus a list of all team affiliations.

    Attributes:
        id: Unique player identifier.
        first_name: Player's first name.
        last_name: Player's last name.
        full_name: Player's full name.
        birth_date: Player's birth date.
        nationality: Player's nationality.
        height_cm: Player's height in centimeters.
        positions: List of player's positions.
        external_ids: External provider ID mappings.
        created_at: Timestamp when player was created.
        updated_at: Timestamp when player was last updated.
        team_history: List of team affiliations across seasons.

    Example:
        >>> response = PlayerWithHistoryResponse.model_validate(player_orm)
        >>> for entry in response.team_history:
        ...     print(f"{entry.team_name} ({entry.season_name})")
    """

    id: UUID
    first_name: str
    last_name: str
    full_name: str
    birth_date: date | None
    nationality: str | None
    height_cm: int | None
    positions: list[str] = []
    external_ids: dict[str, str]
    created_at: datetime
    updated_at: datetime
    team_history: list[PlayerTeamHistoryResponse]
