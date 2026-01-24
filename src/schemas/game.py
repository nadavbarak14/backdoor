"""
Game Schema Module

Pydantic schemas for game-related API operations:
- GameStatus, EventType: Enums for game and event statuses
- GameCreate, GameUpdate: Request validation for game CRUD
- GameResponse, GameWithBoxScoreResponse: Response serialization for games
- GameFilter: Query parameter validation for game filtering
- GameListResponse: Paginated game list response

Usage:
    from src.schemas.game import GameCreate, GameResponse, GameStatus

    @router.post("/games", response_model=GameResponse)
    def create_game(data: GameCreate):
        ...
"""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.base import OrmBase


class GameStatus(str, Enum):
    """
    Game status enumeration.

    Represents the current state of a basketball game.

    Values:
        SCHEDULED: Game is scheduled but not yet started.
        LIVE: Game is currently in progress.
        FINAL: Game has completed.
        POSTPONED: Game has been postponed.
        CANCELLED: Game has been cancelled.

    Example:
        >>> status = GameStatus.FINAL
        >>> print(status.value)
        'FINAL'
    """

    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINAL = "FINAL"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class EventType(str, Enum):
    """
    Play-by-play event type enumeration.

    Represents the type of action that occurred during a game.

    Values:
        SHOT: Field goal attempt.
        ASSIST: Assist on a made basket.
        REBOUND: Offensive or defensive rebound.
        TURNOVER: Turnover by a player.
        STEAL: Steal by a player.
        BLOCK: Blocked shot.
        FOUL: Personal, technical, or flagrant foul.
        FREE_THROW: Free throw attempt.
        SUBSTITUTION: Player substitution.
        TIMEOUT: Team or official timeout.
        JUMP_BALL: Jump ball situation.
        VIOLATION: Travelling, backcourt, etc.
        PERIOD_START: Start of a period.
        PERIOD_END: End of a period.

    Example:
        >>> event_type = EventType.SHOT
        >>> print(event_type.value)
        'SHOT'
    """

    SHOT = "SHOT"
    ASSIST = "ASSIST"
    REBOUND = "REBOUND"
    TURNOVER = "TURNOVER"
    STEAL = "STEAL"
    BLOCK = "BLOCK"
    FOUL = "FOUL"
    FREE_THROW = "FREE_THROW"
    SUBSTITUTION = "SUBSTITUTION"
    TIMEOUT = "TIMEOUT"
    JUMP_BALL = "JUMP_BALL"
    VIOLATION = "VIOLATION"
    PERIOD_START = "PERIOD_START"
    PERIOD_END = "PERIOD_END"


class GameCreate(BaseModel):
    """
    Schema for creating a new game.

    Attributes:
        season_id: UUID of the season this game belongs to.
        home_team_id: UUID of the home team.
        away_team_id: UUID of the away team.
        game_date: Date and time of the game.
        status: Current game status (defaults to SCHEDULED).
        venue: Name of the arena/venue (optional).
        external_ids: Optional dict mapping provider names to their IDs.

    Example:
        >>> from datetime import datetime
        >>> data = GameCreate(
        ...     season_id=season_uuid,
        ...     home_team_id=lakers_uuid,
        ...     away_team_id=celtics_uuid,
        ...     game_date=datetime(2024, 1, 15, 19, 30),
        ...     status=GameStatus.SCHEDULED,
        ...     venue="Crypto.com Arena"
        ... )
    """

    season_id: UUID = Field(..., description="Season UUID this game belongs to")
    home_team_id: UUID = Field(..., description="Home team UUID")
    away_team_id: UUID = Field(..., description="Away team UUID")
    game_date: datetime = Field(..., description="Date and time of the game")
    status: GameStatus = Field(default=GameStatus.SCHEDULED, description="Game status")
    venue: str | None = Field(None, max_length=200, description="Arena/venue name")
    external_ids: dict[str, str] | None = Field(
        default=None, description="External provider ID mappings"
    )


class GameUpdate(BaseModel):
    """
    Schema for updating an existing game.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        game_date: Date and time of the game (optional).
        status: Current game status (optional).
        home_score: Home team's final score (optional).
        away_score: Away team's final score (optional).
        venue: Name of the arena/venue (optional).
        attendance: Number of spectators (optional).
        external_ids: External provider ID mappings (optional).

    Example:
        >>> data = GameUpdate(status=GameStatus.FINAL, home_score=112, away_score=108)
    """

    game_date: datetime | None = Field(None, description="Date and time of the game")
    status: GameStatus | None = Field(None, description="Game status")
    home_score: int | None = Field(None, ge=0, description="Home team's final score")
    away_score: int | None = Field(None, ge=0, description="Away team's final score")
    venue: str | None = Field(None, max_length=200, description="Arena/venue name")
    attendance: int | None = Field(None, ge=0, description="Number of spectators")
    external_ids: dict[str, str] | None = Field(
        None, description="External provider ID mappings"
    )


class GameResponse(OrmBase):
    """
    Schema for game API response.

    Includes basic game information with team names.

    Attributes:
        id: Unique game identifier.
        season_id: UUID of the season this game belongs to.
        home_team_id: UUID of the home team.
        home_team_name: Name of the home team.
        away_team_id: UUID of the away team.
        away_team_name: Name of the away team.
        game_date: Date and time of the game.
        status: Current game status.
        home_score: Home team's final score (None if not finished).
        away_score: Away team's final score (None if not finished).
        venue: Name of the arena/venue.
        attendance: Number of spectators.
        external_ids: External provider ID mappings.
        created_at: Timestamp when game was created.
        updated_at: Timestamp when game was last updated.

    Example:
        >>> response = GameResponse.model_validate(game_orm)
        >>> print(f"{response.home_team_name} vs {response.away_team_name}")
    """

    id: UUID
    season_id: UUID
    home_team_id: UUID
    home_team_name: str
    away_team_id: UUID
    away_team_name: str
    game_date: datetime
    status: str
    home_score: int | None
    away_score: int | None
    venue: str | None
    attendance: int | None
    external_ids: dict[str, str]
    created_at: datetime
    updated_at: datetime


class GameListResponse(BaseModel):
    """
    Schema for paginated game list response.

    Attributes:
        items: List of games for the current page.
        total: Total number of games across all pages.

    Example:
        >>> response = GameListResponse(items=[game1, game2], total=100)
    """

    items: list[GameResponse]
    total: int


class GameFilter(BaseModel):
    """
    Schema for filtering games in list queries.

    Used as query parameters for game list endpoints.
    All fields are optional filters.

    Attributes:
        season_id: Filter by season UUID.
        team_id: Filter by team UUID (home or away).
        start_date: Filter games on or after this date.
        end_date: Filter games on or before this date.
        status: Filter by game status.

    Example:
        >>> filters = GameFilter(
        ...     season_id=season_uuid,
        ...     team_id=lakers_uuid,
        ...     status=GameStatus.FINAL
        ... )
    """

    season_id: UUID | None = Field(None, description="Filter by season UUID")
    team_id: UUID | None = Field(None, description="Filter by team UUID (home or away)")
    start_date: date | None = Field(
        None, description="Filter games on or after this date"
    )
    end_date: date | None = Field(
        None, description="Filter games on or before this date"
    )
    status: GameStatus | None = Field(None, description="Filter by game status")


# Forward references for circular imports - these will be imported from stats.py
# when the GameWithBoxScoreResponse is used
class TeamBoxScoreResponse(OrmBase):
    """
    Schema for team box score in game context.

    Contains team-level stats for a single game.

    Attributes:
        team_id: UUID of the team.
        team_name: Name of the team.
        is_home: Whether this team is the home team.
        points: Total points scored.
        field_goals_made: Number of field goals made.
        field_goals_attempted: Number of field goals attempted.
        field_goal_pct: Field goal percentage (computed).
        three_pointers_made: Number of 3-point field goals made.
        three_pointers_attempted: Number of 3-point field goals attempted.
        three_point_pct: 3-point percentage (computed).
        free_throws_made: Number of free throws made.
        free_throws_attempted: Number of free throws attempted.
        free_throw_pct: Free throw percentage (computed).
        offensive_rebounds: Number of offensive rebounds.
        defensive_rebounds: Number of defensive rebounds.
        total_rebounds: Total number of rebounds.
        assists: Number of assists.
        turnovers: Number of turnovers.
        steals: Number of steals.
        blocks: Number of blocks.
        personal_fouls: Number of personal fouls.
        fast_break_points: Points scored on fast breaks.
        points_in_paint: Points scored in the paint.
        second_chance_points: Points from second chance opportunities.
        bench_points: Points scored by bench players.

    Example:
        >>> box_score = TeamBoxScoreResponse(
        ...     team_id=team_uuid,
        ...     team_name="Los Angeles Lakers",
        ...     is_home=True,
        ...     points=112,
        ...     ...
        ... )
    """

    team_id: UUID
    team_name: str
    is_home: bool
    points: int
    field_goals_made: int
    field_goals_attempted: int
    field_goal_pct: float
    three_pointers_made: int
    three_pointers_attempted: int
    three_point_pct: float
    free_throws_made: int
    free_throws_attempted: int
    free_throw_pct: float
    offensive_rebounds: int
    defensive_rebounds: int
    total_rebounds: int
    assists: int
    turnovers: int
    steals: int
    blocks: int
    personal_fouls: int
    fast_break_points: int
    points_in_paint: int
    second_chance_points: int
    bench_points: int


class PlayerBoxScoreResponse(OrmBase):
    """
    Schema for player box score in game context.

    Contains player-level stats for a single game.

    Attributes:
        player_id: UUID of the player.
        player_name: Full name of the player.
        team_id: UUID of the team.
        is_starter: Whether the player started the game.
        minutes_played: Playing time in seconds.
        minutes_display: Playing time formatted (e.g., "25:30").
        points: Total points scored.
        field_goals_made: Number of field goals made.
        field_goals_attempted: Number of field goals attempted.
        field_goal_pct: Field goal percentage (computed).
        three_pointers_made: Number of 3-point field goals made.
        three_pointers_attempted: Number of 3-point field goals attempted.
        three_point_pct: 3-point percentage (computed).
        free_throws_made: Number of free throws made.
        free_throws_attempted: Number of free throws attempted.
        free_throw_pct: Free throw percentage (computed).
        offensive_rebounds: Number of offensive rebounds.
        defensive_rebounds: Number of defensive rebounds.
        total_rebounds: Total number of rebounds.
        assists: Number of assists.
        turnovers: Number of turnovers.
        steals: Number of steals.
        blocks: Number of blocks.
        personal_fouls: Number of personal fouls.
        plus_minus: Plus/minus statistic.

    Example:
        >>> box_score = PlayerBoxScoreResponse(
        ...     player_id=player_uuid,
        ...     player_name="LeBron James",
        ...     team_id=team_uuid,
        ...     is_starter=True,
        ...     minutes_display="35:42",
        ...     points=25,
        ...     ...
        ... )
    """

    player_id: UUID
    player_name: str
    team_id: UUID
    is_starter: bool
    minutes_played: int
    minutes_display: str
    points: int
    field_goals_made: int
    field_goals_attempted: int
    field_goal_pct: float
    three_pointers_made: int
    three_pointers_attempted: int
    three_point_pct: float
    free_throws_made: int
    free_throws_attempted: int
    free_throw_pct: float
    offensive_rebounds: int
    defensive_rebounds: int
    total_rebounds: int
    assists: int
    turnovers: int
    steals: int
    blocks: int
    personal_fouls: int
    plus_minus: int


class GameWithBoxScoreResponse(OrmBase):
    """
    Schema for game with complete box score data.

    Includes full game information plus team and player stats.

    Attributes:
        id: Unique game identifier.
        season_id: UUID of the season this game belongs to.
        home_team_id: UUID of the home team.
        home_team_name: Name of the home team.
        away_team_id: UUID of the away team.
        away_team_name: Name of the away team.
        game_date: Date and time of the game.
        status: Current game status.
        home_score: Home team's final score.
        away_score: Away team's final score.
        venue: Name of the arena/venue.
        attendance: Number of spectators.
        external_ids: External provider ID mappings.
        home_team_stats: Team box score for home team.
        away_team_stats: Team box score for away team.
        home_players: Player box scores for home team.
        away_players: Player box scores for away team.
        created_at: Timestamp when game was created.
        updated_at: Timestamp when game was last updated.

    Example:
        >>> response = GameWithBoxScoreResponse(
        ...     id=game_uuid,
        ...     home_team_name="Los Angeles Lakers",
        ...     away_team_name="Boston Celtics",
        ...     home_score=112,
        ...     away_score=108,
        ...     home_team_stats=home_box_score,
        ...     away_team_stats=away_box_score,
        ...     home_players=[player1_stats, player2_stats, ...],
        ...     away_players=[player3_stats, player4_stats, ...],
        ...     ...
        ... )
    """

    id: UUID
    season_id: UUID
    home_team_id: UUID
    home_team_name: str
    away_team_id: UUID
    away_team_name: str
    game_date: datetime
    status: str
    home_score: int | None
    away_score: int | None
    venue: str | None
    attendance: int | None
    external_ids: dict[str, str]
    home_team_stats: TeamBoxScoreResponse | None
    away_team_stats: TeamBoxScoreResponse | None
    home_players: list[PlayerBoxScoreResponse]
    away_players: list[PlayerBoxScoreResponse]
    created_at: datetime
    updated_at: datetime
