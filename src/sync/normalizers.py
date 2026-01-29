"""
Normalization Layer Module

Provides functions to normalize raw scraped values to canonical domain types.
This is the critical validation layer between external data and our database.

Philosophy (from Issue #201):
    "All persisted data must be normalized through our domain models,
    not raw scraped values. Nothing can be written to DB that doesn't
    match our types."

Key Design Decisions:
    1. FAIL LOUDLY: Unknown values raise NormalizationError
    2. Source-aware: Error messages include source for debugging
    3. Comprehensive mappings: Cover all known values from all leagues

Usage:
    from src.sync.normalizers import Normalizers, NormalizationError

    try:
        position = Normalizers.normalize_position("Point Guard", "winner")
        positions = Normalizers.normalize_positions("Guard-Forward", "euroleague")
        status = Normalizers.normalize_game_status("final", "nba")
    except NormalizationError as e:
        logger.error(f"Failed to normalize {e.field}='{e.value}' from {e.source}")
        raise

Example:
    >>> from src.sync.normalizers import Normalizers
    >>> Normalizers.normalize_position("PG", "nba")
    <Position.POINT_GUARD: 'PG'>
    >>> Normalizers.normalize_game_status("final", "winner")
    <GameStatus.FINAL: 'FINAL'>
"""

import re

from src.schemas.enums import EventType, GameStatus, Position


class NormalizationError(Exception):
    """
    Raised when a value cannot be normalized to a known enum.

    This error forces developers to add new mappings when encountering
    unknown values from external sources, rather than silently storing
    garbage in the database.

    Attributes:
        field: The field being normalized (e.g., "position", "game_status")
        value: The raw value that could not be normalized
        source: The data source (e.g., "winner", "nba", "euroleague")

    Example:
        >>> try:
        ...     Normalizers.normalize_position("Unknown Position", "winner")
        ... except NormalizationError as e:
        ...     print(f"Cannot normalize {e.field}='{e.value}' from {e.source}")
        Cannot normalize position='Unknown Position' from winner
    """

    def __init__(self, field: str, value: str, source: str) -> None:
        self.field = field
        self.value = value
        self.source = source
        super().__init__(
            f"Cannot normalize {field}='{value}' from {source}. "
            f"Add a mapping for this value in Normalizers."
        )


class Normalizers:
    """
    Normalize raw scraped values to canonical domain types.

    FAIL LOUDLY: Unknown values raise NormalizationError.
    This forces us to add mappings for new values instead of silently
    storing garbage in the database.

    All methods are class methods that take the raw value and source name,
    returning the appropriate enum or raising NormalizationError.

    Example:
        >>> Normalizers.normalize_position("point guard", "winner")
        <Position.POINT_GUARD: 'PG'>
        >>> Normalizers.normalize_positions("G/F", "euroleague")
        [<Position.GUARD: 'G'>, <Position.FORWARD: 'F'>]
    """

    # Position mappings from various sources to Position enum
    # Keys are lowercase for case-insensitive matching
    POSITION_MAP: dict[str, Position] = {
        # Standard abbreviations (most common)
        "pg": Position.POINT_GUARD,
        "sg": Position.SHOOTING_GUARD,
        "sf": Position.SMALL_FORWARD,
        "pf": Position.POWER_FORWARD,
        "c": Position.CENTER,
        "g": Position.GUARD,
        "f": Position.FORWARD,
        # Full English names
        "point guard": Position.POINT_GUARD,
        "shooting guard": Position.SHOOTING_GUARD,
        "small forward": Position.SMALL_FORWARD,
        "power forward": Position.POWER_FORWARD,
        "center": Position.CENTER,
        "guard": Position.GUARD,
        "forward": Position.FORWARD,
        # Alternative spellings
        "point": Position.POINT_GUARD,
        "shooting": Position.SHOOTING_GUARD,
        "centre": Position.CENTER,  # British spelling
        # Euroleague format
        "guard (point)": Position.POINT_GUARD,
        "guard (shooting)": Position.SHOOTING_GUARD,
        "forward (small)": Position.SMALL_FORWARD,
        "forward (power)": Position.POWER_FORWARD,
        # Hebrew (Winner league, iBasketball)
        "גארד": Position.GUARD,
        "פורוורד": Position.FORWARD,
        "סנטר": Position.CENTER,
        "פוינט גארד": Position.POINT_GUARD,
        "שוטינג גארד": Position.SHOOTING_GUARD,
        "סמול פורוורד": Position.SMALL_FORWARD,
        "פאוור פורוורד": Position.POWER_FORWARD,
        # NBA format variations
        "g-f": Position.GUARD,  # Guard who can play forward
        "f-g": Position.FORWARD,  # Forward who can play guard
        "f-c": Position.FORWARD,  # Forward who can play center
        "c-f": Position.CENTER,  # Center who can play forward
    }

    # Game status mappings from various sources to GameStatus enum
    # Keys are lowercase for case-insensitive matching
    GAME_STATUS_MAP: dict[str, GameStatus] = {
        # Final/completed states
        "final": GameStatus.FINAL,
        "finished": GameStatus.FINAL,
        "ft": GameStatus.FINAL,
        "played": GameStatus.FINAL,
        "completed": GameStatus.FINAL,
        "ended": GameStatus.FINAL,
        "over": GameStatus.FINAL,
        "result": GameStatus.FINAL,
        # Scheduled/upcoming states
        "scheduled": GameStatus.SCHEDULED,
        "not started": GameStatus.SCHEDULED,
        "upcoming": GameStatus.SCHEDULED,
        "future": GameStatus.SCHEDULED,
        "pending": GameStatus.SCHEDULED,
        "tbd": GameStatus.SCHEDULED,
        # Live/in-progress states
        "live": GameStatus.LIVE,
        "in progress": GameStatus.LIVE,
        "in_progress": GameStatus.LIVE,
        "playing": GameStatus.LIVE,
        "ongoing": GameStatus.LIVE,
        "active": GameStatus.LIVE,
        # Postponed states
        "postponed": GameStatus.POSTPONED,
        "delayed": GameStatus.POSTPONED,
        "suspended": GameStatus.POSTPONED,
        # Cancelled states
        "cancelled": GameStatus.CANCELLED,
        "canceled": GameStatus.CANCELLED,  # American spelling
        "abandoned": GameStatus.CANCELLED,
        "forfeit": GameStatus.CANCELLED,
        "forfeited": GameStatus.CANCELLED,
    }

    # Event type mappings from various sources to EventType enum
    # Keys are lowercase for case-insensitive matching
    EVENT_TYPE_MAP: dict[str, EventType] = {
        # Shots
        "shot": EventType.SHOT,
        "made shot": EventType.SHOT,
        "missed shot": EventType.SHOT,
        "field goal": EventType.SHOT,
        "2pt": EventType.SHOT,
        "3pt": EventType.SHOT,
        "layup": EventType.SHOT,
        "dunk": EventType.SHOT,
        "jump shot": EventType.SHOT,
        # Free throws
        "free throw": EventType.FREE_THROW,
        "free_throw": EventType.FREE_THROW,
        "ft": EventType.FREE_THROW,
        "foul shot": EventType.FREE_THROW,
        # Rebounds
        "rebound": EventType.REBOUND,
        "reb": EventType.REBOUND,
        "offensive rebound": EventType.REBOUND,
        "defensive rebound": EventType.REBOUND,
        # Assists
        "assist": EventType.ASSIST,
        "ast": EventType.ASSIST,
        # Turnovers
        "turnover": EventType.TURNOVER,
        "to": EventType.TURNOVER,
        "tov": EventType.TURNOVER,
        "lost ball": EventType.TURNOVER,
        "bad pass": EventType.TURNOVER,
        # Steals
        "steal": EventType.STEAL,
        "stl": EventType.STEAL,
        # Blocks
        "block": EventType.BLOCK,
        "blk": EventType.BLOCK,
        "blocked shot": EventType.BLOCK,
        # Fouls
        "foul": EventType.FOUL,
        "personal foul": EventType.FOUL,
        "technical foul": EventType.FOUL,
        "flagrant foul": EventType.FOUL,
        "offensive foul": EventType.FOUL,
        "shooting foul": EventType.FOUL,
        # Substitutions
        "substitution": EventType.SUBSTITUTION,
        "sub": EventType.SUBSTITUTION,
        "sub in": EventType.SUBSTITUTION,
        "sub out": EventType.SUBSTITUTION,
        # Timeouts
        "timeout": EventType.TIMEOUT,
        "team timeout": EventType.TIMEOUT,
        "official timeout": EventType.TIMEOUT,
        # Jump balls
        "jump ball": EventType.JUMP_BALL,
        "jump_ball": EventType.JUMP_BALL,
        "tip off": EventType.JUMP_BALL,
        # Violations
        "violation": EventType.VIOLATION,
        "travel": EventType.VIOLATION,
        "travelling": EventType.VIOLATION,
        "backcourt": EventType.VIOLATION,
        "3 seconds": EventType.VIOLATION,
        "5 seconds": EventType.VIOLATION,
        "8 seconds": EventType.VIOLATION,
        "24 seconds": EventType.VIOLATION,
        "shot clock": EventType.VIOLATION,
        "double dribble": EventType.VIOLATION,
        "kicked ball": EventType.VIOLATION,
        # Period events
        "period start": EventType.PERIOD_START,
        "period_start": EventType.PERIOD_START,
        "start of period": EventType.PERIOD_START,
        "period end": EventType.PERIOD_END,
        "period_end": EventType.PERIOD_END,
        "end of period": EventType.PERIOD_END,
    }

    @classmethod
    def normalize_position(cls, raw: str, source: str) -> Position:
        """
        Normalize a single position string to Position enum.

        Args:
            raw: Raw position string from external source.
            source: Name of the data source for error reporting.

        Returns:
            Position enum value.

        Raises:
            NormalizationError: If position cannot be mapped.

        Example:
            >>> Normalizers.normalize_position("Point Guard", "nba")
            <Position.POINT_GUARD: 'PG'>
            >>> Normalizers.normalize_position("גארד", "winner")
            <Position.GUARD: 'G'>
        """
        if not raw or not raw.strip():
            raise NormalizationError("position", raw or "(empty)", source)

        key = raw.lower().strip()

        if key in cls.POSITION_MAP:
            return cls.POSITION_MAP[key]

        raise NormalizationError("position", raw, source)

    @classmethod
    def normalize_positions(cls, raw: str, source: str) -> list[Position]:
        """
        Normalize position string that may contain multiple positions.

        Handles various formats:
        - "Guard-Forward" -> [GUARD, FORWARD]
        - "G/F" -> [GUARD, FORWARD]
        - "PG, SG" -> [POINT_GUARD, SHOOTING_GUARD]
        - "גארד-פורוורד" -> [GUARD, FORWARD]

        Args:
            raw: Raw position string, possibly with multiple positions.
            source: Name of the data source for error reporting.

        Returns:
            List of Position enum values. Empty list if raw is empty.

        Raises:
            NormalizationError: If any position cannot be mapped.

        Example:
            >>> Normalizers.normalize_positions("G/F", "euroleague")
            [<Position.GUARD: 'G'>, <Position.FORWARD: 'F'>]
            >>> Normalizers.normalize_positions("Point Guard", "nba")
            [<Position.POINT_GUARD: 'PG'>]
        """
        if not raw or not raw.strip():
            return []

        # Split by common separators: -, /, ,
        parts = re.split(r"[-/,]", raw)
        positions = []

        for part in parts:
            part = part.strip()
            if part:
                positions.append(cls.normalize_position(part, source))

        return positions

    @classmethod
    def try_normalize_positions(
        cls, raw: str | None, source: str
    ) -> list[Position] | None:
        """
        Try to normalize positions, returning None on failure instead of raising.

        Useful for optional position fields where unknown values should be
        silently skipped rather than causing sync failures.

        Args:
            raw: Raw position string or None.
            source: Name of the data source for logging.

        Returns:
            List of Position enum values, empty list if raw is empty,
            or None if normalization fails.

        Example:
            >>> Normalizers.try_normalize_positions("Unknown", "test")
            None
            >>> Normalizers.try_normalize_positions("PG", "test")
            [<Position.POINT_GUARD: 'PG'>]
        """
        if not raw:
            return []
        try:
            return cls.normalize_positions(raw, source)
        except NormalizationError:
            return None

    @classmethod
    def normalize_game_status(cls, raw: str, source: str) -> GameStatus:
        """
        Normalize game status string to GameStatus enum.

        Args:
            raw: Raw status string from external source.
            source: Name of the data source for error reporting.

        Returns:
            GameStatus enum value.

        Raises:
            NormalizationError: If status cannot be mapped.

        Example:
            >>> Normalizers.normalize_game_status("final", "winner")
            <GameStatus.FINAL: 'FINAL'>
            >>> Normalizers.normalize_game_status("FT", "euroleague")
            <GameStatus.FINAL: 'FINAL'>
        """
        if not raw or not raw.strip():
            raise NormalizationError("game_status", raw or "(empty)", source)

        key = raw.lower().strip()

        if key in cls.GAME_STATUS_MAP:
            return cls.GAME_STATUS_MAP[key]

        raise NormalizationError("game_status", raw, source)

    @classmethod
    def normalize_event_type(cls, raw: str, source: str) -> EventType:
        """
        Normalize event type string to EventType enum.

        Args:
            raw: Raw event type string from external source.
            source: Name of the data source for error reporting.

        Returns:
            EventType enum value.

        Raises:
            NormalizationError: If event type cannot be mapped.

        Example:
            >>> Normalizers.normalize_event_type("Made Shot", "nba")
            <EventType.SHOT: 'SHOT'>
            >>> Normalizers.normalize_event_type("rebound", "winner")
            <EventType.REBOUND: 'REBOUND'>
        """
        if not raw or not raw.strip():
            raise NormalizationError("event_type", raw or "(empty)", source)

        key = raw.lower().strip()

        if key in cls.EVENT_TYPE_MAP:
            return cls.EVENT_TYPE_MAP[key]

        raise NormalizationError("event_type", raw, source)

    @classmethod
    def try_normalize_event_type(cls, raw: str | None, source: str) -> EventType | None:
        """
        Try to normalize event type, returning None on failure.

        Useful for PBP events where unknown event types should be
        skipped rather than causing sync failures.

        Args:
            raw: Raw event type string or None.
            source: Name of the data source.

        Returns:
            EventType enum value or None if normalization fails.

        Example:
            >>> Normalizers.try_normalize_event_type("Unknown Event", "test")
            None
            >>> Normalizers.try_normalize_event_type("shot", "test")
            <EventType.SHOT: 'SHOT'>
        """
        if not raw:
            return None
        try:
            return cls.normalize_event_type(raw, source)
        except NormalizationError:
            return None
