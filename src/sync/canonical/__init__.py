"""
Canonical Package

Provides the "layer of truth" for normalized data types and entities
used across the Basketball Analytics Platform. All league adapters
convert their raw data to these validated types before storage.

This package exports:
    Types:
        - Position: Basketball position enum
        - Height: Validated height in centimeters
        - Nationality: ISO country code
        - EventType: Play-by-play event type enum
        - ShotType, ReboundType, FoulType, TurnoverType: Event subtypes
        - GameStatus: Game state enum

    Entities:
        - CanonicalPlayer: Player with positions, height, nationality
        - CanonicalTeam: Team with name, city, country
        - CanonicalGame: Game with teams, date, score, status
        - CanonicalPlayerStats: Box score statistics
        - CanonicalPBPEvent: Play-by-play event
        - CanonicalSeason: Season with dates

    Converter:
        - BaseLeagueConverter: ABC that all league converters must implement

    Parse Functions:
        - parse_position(): Parse single position
        - parse_positions(): Parse multi-position string
        - parse_height(): Parse height from various formats
        - parse_birthdate(): Parse birthdate from various formats
        - parse_nationality(): Parse country to ISO code
        - parse_game_status(): Parse game status

    Exceptions:
        - ValidationError: Data validation failed
        - ConversionError: Data conversion failed

Usage:
    from src.sync.canonical import (
        Position, parse_position, parse_positions,
        Height, parse_height,
        Nationality, parse_nationality,
        EventType, GameStatus,
        CanonicalPlayer, CanonicalTeam,
        BaseLeagueConverter,
    )

    # Parse raw data to canonical types
    position = parse_position("Point Guard")  # Position.POINT_GUARD
    height = parse_height("6'8\"")  # Height(cm=203)
    nationality = parse_nationality("Israel")  # Nationality(code="ISR")
"""

from src.sync.canonical.converter import BaseLeagueConverter
from src.sync.canonical.entities import (
    CanonicalGame,
    CanonicalPBPEvent,
    CanonicalPlayer,
    CanonicalPlayerStats,
    CanonicalSeason,
    CanonicalTeam,
)
from src.sync.canonical.types import (
    ConversionError,
    # Event types
    EventType,
    FoulType,
    # Game status
    GameStatus,
    # Height types and functions
    Height,
    # Nationality types and functions
    Nationality,
    # Position types and functions
    Position,
    ReboundType,
    ShotType,
    TurnoverType,
    # Exceptions
    ValidationError,
    # Birthdate functions
    parse_birthdate,
    parse_game_status,
    parse_height,
    parse_nationality,
    parse_position,
    parse_positions,
)

__all__ = [
    # Position
    "Position",
    "parse_position",
    "parse_positions",
    # Height
    "Height",
    "parse_height",
    # Birthdate
    "parse_birthdate",
    # Nationality
    "Nationality",
    "parse_nationality",
    # Events
    "EventType",
    "ShotType",
    "ReboundType",
    "FoulType",
    "TurnoverType",
    # Game status
    "GameStatus",
    "parse_game_status",
    # Entities
    "CanonicalPlayer",
    "CanonicalTeam",
    "CanonicalGame",
    "CanonicalPlayerStats",
    "CanonicalPBPEvent",
    "CanonicalSeason",
    # Converter
    "BaseLeagueConverter",
    # Exceptions
    "ValidationError",
    "ConversionError",
]
