"""
Game Status Type Module

Provides the GameStatus enum and parse function.

This module exports:
    - GameStatus: Game state enumeration
    - parse_game_status(): Parse game status string

Usage:
    from src.sync.canonical.types.game_status import GameStatus, parse_game_status

    status = parse_game_status("final")  # GameStatus.FINAL
    status = parse_game_status("FT")  # GameStatus.FINAL (Euroleague format)
"""

from enum import Enum


class GameStatus(str, Enum):
    """
    Game status enumeration.

    Represents the current state of a basketball game.

    Values:
        SCHEDULED: Game is scheduled but not yet started
        LIVE: Game is currently in progress
        FINAL: Game has completed
        POSTPONED: Game has been postponed
        CANCELLED: Game has been cancelled

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


# Game status mappings from various sources to GameStatus enum
# Keys are lowercase for case-insensitive matching
_GAME_STATUS_MAP: dict[str, GameStatus] = {
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


def parse_game_status(raw: str | None) -> GameStatus | None:
    """
    Parse game status string to GameStatus enum.

    Case-insensitive parsing with support for various formats
    from different leagues.

    Args:
        raw: Raw status string from external source, or None.

    Returns:
        GameStatus enum value, or None if parsing fails.

    Example:
        >>> parse_game_status("final")
        <GameStatus.FINAL: 'FINAL'>
        >>> parse_game_status("FT")
        <GameStatus.FINAL: 'FINAL'>
        >>> parse_game_status("live")
        <GameStatus.LIVE: 'LIVE'>
        >>> parse_game_status("invalid")
        None
        >>> parse_game_status(None)
        None
    """
    if raw is None:
        return None

    if not isinstance(raw, str):
        return None

    raw = raw.strip()
    if not raw:
        return None

    key = raw.lower()

    if key in _GAME_STATUS_MAP:
        return _GAME_STATUS_MAP[key]

    return None
