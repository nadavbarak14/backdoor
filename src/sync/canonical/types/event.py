"""
Event Type Module

Provides enums for play-by-play event types and subtypes.

This module exports:
    - EventType: Main event type enumeration
    - ShotType: Shot subtype enumeration
    - ReboundType: Rebound subtype enumeration
    - FoulType: Foul subtype enumeration
    - TurnoverType: Turnover subtype enumeration

Usage:
    from src.sync.canonical.types.event import (
        EventType, ShotType, ReboundType, FoulType, TurnoverType
    )

    event_type = EventType.SHOT
    shot_type = ShotType.THREE_POINT
"""

from enum import Enum


class EventType(str, Enum):
    """
    Play-by-play event type enumeration.

    Represents the type of action that occurred during a game.

    Values:
        SHOT: Field goal attempt
        ASSIST: Assist on a made basket
        REBOUND: Offensive or defensive rebound
        TURNOVER: Turnover by a player (includes violations)
        STEAL: Steal by a player
        BLOCK: Blocked shot
        FOUL: Personal, technical, or flagrant foul
        FREE_THROW: Free throw attempt
        SUBSTITUTION: Player substitution
        TIMEOUT: Team or official timeout
        JUMP_BALL: Jump ball situation
        PERIOD_START: Start of a period
        PERIOD_END: End of a period

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
    PERIOD_START = "PERIOD_START"
    PERIOD_END = "PERIOD_END"


class ShotType(str, Enum):
    """
    Shot subtype enumeration.

    Provides detail on the type of field goal attempted.

    Values:
        TWO_POINT: Two-point field goal attempt
        THREE_POINT: Three-point field goal attempt
        DUNK: Dunk attempt
        LAYUP: Layup attempt

    Example:
        >>> shot_type = ShotType.THREE_POINT
        >>> print(shot_type.value)
        '3PT'
    """

    TWO_POINT = "2PT"
    THREE_POINT = "3PT"
    DUNK = "DUNK"
    LAYUP = "LAYUP"


class ReboundType(str, Enum):
    """
    Rebound subtype enumeration.

    Values:
        OFFENSIVE: Offensive rebound (same team as shooter)
        DEFENSIVE: Defensive rebound (opposing team)

    Example:
        >>> rebound_type = ReboundType.OFFENSIVE
        >>> print(rebound_type.value)
        'OFF'
    """

    OFFENSIVE = "OFF"
    DEFENSIVE = "DEF"


class FoulType(str, Enum):
    """
    Foul subtype enumeration.

    Values:
        PERSONAL: Standard personal foul
        TECHNICAL: Technical foul
        FLAGRANT: Flagrant foul
        OFFENSIVE: Offensive foul (charge)

    Example:
        >>> foul_type = FoulType.TECHNICAL
        >>> print(foul_type.value)
        'TECHNICAL'
    """

    PERSONAL = "PERSONAL"
    TECHNICAL = "TECHNICAL"
    FLAGRANT = "FLAGRANT"
    OFFENSIVE = "OFFENSIVE"


class TurnoverType(str, Enum):
    """
    Turnover subtype enumeration.

    Values:
        BAD_PASS: Turnover due to bad pass
        LOST_BALL: Lost ball turnover
        TRAVEL: Travelling violation
        BACKCOURT: Backcourt violation
        SHOT_CLOCK: Shot clock violation
        OFFENSIVE_FOUL: Turnover via offensive foul
        OTHER: Other turnover type

    Example:
        >>> turnover_type = TurnoverType.TRAVEL
        >>> print(turnover_type.value)
        'TRAVEL'
    """

    BAD_PASS = "BAD_PASS"
    LOST_BALL = "LOST_BALL"
    TRAVEL = "TRAVEL"
    BACKCOURT = "BACKCOURT"
    SHOT_CLOCK = "SHOT_CLOCK"
    OFFENSIVE_FOUL = "OFFENSIVE_FOUL"
    OTHER = "OTHER"
