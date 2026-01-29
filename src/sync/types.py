"""
Raw Data Types Module (DEPRECATED)

.. deprecated::
    These Raw types are being phased out in favor of Canonical types.
    Use types from src.sync.canonical instead:
    - RawSeason -> CanonicalSeason
    - RawTeam -> CanonicalTeam
    - RawGame -> CanonicalGame
    - RawPlayerStats -> CanonicalPlayerStats
    - RawPBPEvent -> CanonicalPBPEvent
    - RawPlayerInfo -> CanonicalPlayer

    For migration, use the conversion utilities in src.sync.raw_to_canonical:
    - raw_game_to_canonical()
    - raw_boxscore_to_canonical_stats()
    - raw_pbp_list_to_canonical()

Defines dataclasses for raw data from external sync sources before transformation
into database models. These types represent the intermediate format between
external APIs and our internal data models.

All types use the "Raw" prefix to distinguish them from database models.
External IDs are strings to support various provider formats.

Usage:
    from src.sync.types import RawSeason, RawTeam, RawGame

    season = RawSeason(
        external_id="2024-25",
        name="2024-25",
        source_id="E2024",  # Optional: original source-specific ID
        start_date=date(2024, 10, 1),
        end_date=date(2025, 6, 30),
        is_current=True
    )
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from src.schemas.enums import EventType, GameStatus, Position
from src.sync.season import SeasonFormatError, validate_season_format


@dataclass
class RawSeason:
    """
    Raw season data from an external source.

    The name field MUST be in standardized YYYY-YY format (e.g., "2024-25").
    Use normalize_season_name() to convert from year to this format.
    Source-specific identifiers (like "E2024" for Euroleague) should be
    stored in the source_id field.

    Attributes:
        external_id: Provider-specific season identifier (for backward compat)
        name: Season name in YYYY-YY format (e.g., "2024-25")
        source_id: Original source-specific identifier (e.g., "E2024")
        start_date: Season start date, if available
        end_date: Season end date, if available
        is_current: Whether this is the current active season

    Raises:
        SeasonFormatError: If name is not in valid YYYY-YY format.

    Example:
        >>> season = RawSeason(
        ...     external_id="2024-25",
        ...     name="2024-25",
        ...     source_id="E2024",
        ...     start_date=date(2024, 10, 1),
        ...     end_date=date(2025, 6, 30),
        ...     is_current=True
        ... )
    """

    external_id: str
    name: str
    source_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False

    def __post_init__(self):
        """Validate that the season name is in YYYY-YY format."""
        if not validate_season_format(self.name):
            raise SeasonFormatError(self.name)


@dataclass
class RawTeam:
    """
    Raw team data from an external source.

    Attributes:
        external_id: Provider-specific team identifier
        name: Full team name
        short_name: Abbreviated team name (e.g., "LAL")

    Example:
        >>> team = RawTeam(
        ...     external_id="team-123",
        ...     name="Los Angeles Lakers",
        ...     short_name="LAL"
        ... )
    """

    external_id: str
    name: str
    short_name: str | None = None


@dataclass
class RawGame:
    """
    Raw game data from an external source.

    Attributes:
        external_id: Provider-specific game identifier
        home_team_external_id: External ID of the home team
        away_team_external_id: External ID of the away team
        game_date: Date and time of the game
        status: Game status as GameStatus enum (SCHEDULED, LIVE, FINAL, etc.)
        home_score: Home team score (None if not started)
        away_score: Away team score (None if not started)

    Example:
        >>> game = RawGame(
        ...     external_id="game-456",
        ...     home_team_external_id="team-123",
        ...     away_team_external_id="team-789",
        ...     game_date=datetime(2024, 1, 15, 19, 30),
        ...     status=GameStatus.FINAL,
        ...     home_score=112,
        ...     away_score=108
        ... )
    """

    external_id: str
    home_team_external_id: str
    away_team_external_id: str
    game_date: datetime
    status: GameStatus  # Must be GameStatus enum
    home_score: int | None = None
    away_score: int | None = None


@dataclass
class RawPlayerStats:
    """
    Raw player statistics from a box score.

    Attributes:
        player_external_id: External ID of the player
        player_name: Display name of the player
        team_external_id: External ID of the player's team
        minutes_played: Playing time in seconds
        is_starter: Whether player started the game
        points: Total points scored
        field_goals_made: Field goals made
        field_goals_attempted: Field goals attempted
        two_pointers_made: Two-point field goals made
        two_pointers_attempted: Two-point field goals attempted
        three_pointers_made: Three-point field goals made
        three_pointers_attempted: Three-point field goals attempted
        free_throws_made: Free throws made
        free_throws_attempted: Free throws attempted
        offensive_rebounds: Offensive rebounds
        defensive_rebounds: Defensive rebounds
        total_rebounds: Total rebounds
        assists: Assists
        turnovers: Turnovers
        steals: Steals
        blocks: Blocks
        personal_fouls: Personal fouls
        plus_minus: Plus/minus statistic
        efficiency: Performance index rating

    Example:
        >>> stats = RawPlayerStats(
        ...     player_external_id="player-123",
        ...     player_name="LeBron James",
        ...     team_external_id="team-456",
        ...     minutes_played=2040,  # 34 minutes in seconds
        ...     points=25,
        ...     assists=8,
        ...     total_rebounds=7
        ... )
    """

    player_external_id: str
    player_name: str
    team_external_id: str
    minutes_played: int = 0
    is_starter: bool = False
    points: int = 0
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    two_pointers_made: int = 0
    two_pointers_attempted: int = 0
    three_pointers_made: int = 0
    three_pointers_attempted: int = 0
    free_throws_made: int = 0
    free_throws_attempted: int = 0
    offensive_rebounds: int = 0
    defensive_rebounds: int = 0
    total_rebounds: int = 0
    assists: int = 0
    turnovers: int = 0
    steals: int = 0
    blocks: int = 0
    personal_fouls: int = 0
    plus_minus: int = 0
    efficiency: int = 0
    jersey_number: str | None = None  # For matching with roster


@dataclass
class RawBoxScore:
    """
    Raw box score data combining game info and player stats.

    Attributes:
        game: The game this box score belongs to
        home_players: Stats for home team players
        away_players: Stats for away team players

    Example:
        >>> boxscore = RawBoxScore(
        ...     game=raw_game,
        ...     home_players=[home_player_stats],
        ...     away_players=[away_player_stats]
        ... )
    """

    game: RawGame
    home_players: list[RawPlayerStats] = field(default_factory=list)
    away_players: list[RawPlayerStats] = field(default_factory=list)


@dataclass
class RawPBPEvent:
    """
    Raw play-by-play event from an external source.

    Attributes:
        event_number: Sequential event number within the game
        period: Period/quarter number (1-4 for regulation, 5+ for OT)
        clock: Game clock time as string (e.g., "10:45")
        event_type: Type of event using canonical EventType enum
        event_subtype: Subtype for detail (e.g., "lay-up", "3-pointer", "offensive")
        player_name: Name of the player involved, if applicable
        player_external_id: External ID of the player (for database linking)
        team_external_id: External ID of the team involved
        success: Whether the event was successful (e.g., shot made)
        coord_x: X coordinate on the court, if available
        coord_y: Y coordinate on the court, if available
        related_event_numbers: Event numbers this event is linked to

    Example:
        >>> event = RawPBPEvent(
        ...     event_number=42,
        ...     period=1,
        ...     clock="08:32",
        ...     event_type=EventType.SHOT,
        ...     event_subtype="3PT",
        ...     player_name="Stephen Curry",
        ...     player_external_id="1001",
        ...     team_external_id="team-123",
        ...     success=True,
        ...     coord_x=25.5,
        ...     coord_y=8.0
        ... )
    """

    event_number: int
    period: int
    clock: str
    event_type: EventType
    event_subtype: str | None = None
    player_name: str | None = None
    player_external_id: str | None = None
    team_external_id: str | None = None
    success: bool | None = None
    coord_x: float | None = None
    coord_y: float | None = None
    related_event_numbers: list[int] | None = None


@dataclass
class RawPlayerInfo:
    """
    Raw player biographical information from an external source.

    This is separate from game stats and includes player bio data
    that may come from different sources than game data.

    Attributes:
        external_id: Provider-specific player identifier
        first_name: Player's first name
        last_name: Player's last name
        birth_date: Player's date of birth, if available
        height_cm: Player's height in centimeters, if available
        positions: Player's positions as list of Position enums
        jersey_number: Player's jersey number
        nationality: Player's nationality

    Example:
        >>> player = RawPlayerInfo(
        ...     external_id="player-123",
        ...     first_name="LeBron",
        ...     last_name="James",
        ...     birth_date=date(1984, 12, 30),
        ...     height_cm=206,
        ...     positions=[Position.SMALL_FORWARD, Position.POWER_FORWARD]
        ... )
    """

    external_id: str
    first_name: str
    last_name: str
    birth_date: date | None = None
    height_cm: int | None = None
    positions: list[Position] = field(default_factory=list)
    jersey_number: str | None = None
    nationality: str | None = None
