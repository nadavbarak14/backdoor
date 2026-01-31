"""
Position Type Module

Provides the Position enum and parse functions for basketball player positions.

This module exports:
    - Position: Basketball position enumeration
    - parse_position(): Parse single position string
    - parse_positions(): Parse multi-position string

Usage:
    from src.sync.canonical.types.position import Position, parse_position, parse_positions

    position = parse_position("Point Guard")  # Position.POINT_GUARD
    positions = parse_positions("G/F")  # [Position.GUARD, Position.FORWARD]
"""

import re
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


# Position mappings from various sources to Position enum
# Keys are lowercase for case-insensitive matching
_POSITION_MAP: dict[str, Position] = {
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
    # Hebrew alternate spellings
    "שמירה": Position.GUARD,
    "חלוץ": Position.FORWARD,
    # NBA format variations - for combo positions, map to first position
    "g-f": Position.GUARD,  # Guard who can play forward
    "f-g": Position.FORWARD,  # Forward who can play guard
    "f-c": Position.FORWARD,  # Forward who can play center
    "c-f": Position.CENTER,  # Center who can play forward
}


def parse_position(raw: str | None) -> Position | None:
    """
    Parse a single position string to Position enum.

    Case-insensitive parsing with support for various formats
    from different leagues and languages.

    Args:
        raw: Raw position string from external source, or None.

    Returns:
        Position enum value, or None if parsing fails.

    Example:
        >>> parse_position("PG")
        <Position.POINT_GUARD: 'PG'>
        >>> parse_position("Point Guard")
        <Position.POINT_GUARD: 'PG'>
        >>> parse_position("גארד")
        <Position.GUARD: 'G'>
        >>> parse_position("invalid")
        None
        >>> parse_position(None)
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

    if key in _POSITION_MAP:
        return _POSITION_MAP[key]

    return None


def parse_positions(raw: str | None) -> list[Position]:
    """
    Parse position string that may contain multiple positions.

    Handles various multi-position formats:
    - "Guard-Forward" -> [GUARD, FORWARD]
    - "G/F" -> [GUARD, FORWARD]
    - "PG, SG" -> [POINT_GUARD, SHOOTING_GUARD]
    - "גארד-פורוורד" -> [GUARD, FORWARD]

    Args:
        raw: Raw position string, possibly with multiple positions, or None.

    Returns:
        List of Position enum values. Empty list if raw is None/empty.
        Duplicates are removed while preserving order.

    Example:
        >>> parse_positions("G/F")
        [<Position.GUARD: 'G'>, <Position.FORWARD: 'F'>]
        >>> parse_positions("PG, SG")
        [<Position.POINT_GUARD: 'PG'>, <Position.SHOOTING_GUARD: 'SG'>]
        >>> parse_positions("PG/PG")
        [<Position.POINT_GUARD: 'PG'>]
        >>> parse_positions(None)
        []
        >>> parse_positions("invalid")
        []
    """
    if raw is None:
        return []

    if not isinstance(raw, str):
        return []

    raw = raw.strip()
    if not raw:
        return []

    # Split by common separators: -, /, ,
    parts = re.split(r"[-/,]", raw)
    positions: list[Position] = []
    seen: set[Position] = set()

    for part in parts:
        part = part.strip()
        if part:
            position = parse_position(part)
            if position is not None and position not in seen:
                positions.append(position)
                seen.add(position)

    return positions
