"""
Domain Enums Module

Central definitions for all domain enumeration types used across the
Basketball Analytics Platform. These enums represent canonical values
that must be used consistently throughout the system.

This module exports:
    - Position: Basketball player positions
    - GameStatus: Game state enumeration
    - EventType: Play-by-play event types

Philosophy:
    All persisted data must be normalized through our domain models.
    Nothing can be written to DB that doesn't match our types.
    External data sources must map their values to these enums.

Usage:
    from src.schemas.enums import Position, GameStatus, EventType

    # In mappers - normalize external values to enums
    position = Position.POINT_GUARD
    status = GameStatus.FINAL

    # In models - store enum values in database
    player.positions = [Position.GUARD, Position.FORWARD]
    game.status = GameStatus.SCHEDULED
"""

from enum import Enum


class Position(str, Enum):
    """
    Basketball position enumeration.

    Represents standard basketball positions. Players can have multiple
    positions stored as a list.

    Values:
        POINT_GUARD: Primary ball handler (PG)
        SHOOTING_GUARD: Secondary ball handler/scorer (SG)
        SMALL_FORWARD: Versatile wing player (SF)
        POWER_FORWARD: Frontcourt player (PF)
        CENTER: Primary post player (C)
        GUARD: Generic guard position (G) - when source doesn't specify PG/SG
        FORWARD: Generic forward position (F) - when source doesn't specify SF/PF

    Example:
        >>> position = Position.POINT_GUARD
        >>> print(position.value)
        'PG'
        >>> # Players can have multiple positions
        >>> positions = [Position.SHOOTING_GUARD, Position.SMALL_FORWARD]
    """

    # Primary positions (5 standard)
    POINT_GUARD = "PG"
    SHOOTING_GUARD = "SG"
    SMALL_FORWARD = "SF"
    POWER_FORWARD = "PF"
    CENTER = "C"

    # Generic positions (when source doesn't specify exact position)
    GUARD = "G"
    FORWARD = "F"


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
