"""
Canonical Player Entity Module

Provides the CanonicalPlayer dataclass for standardized player data.

Usage:
    from src.sync.canonical.entities import CanonicalPlayer
    from src.sync.canonical import Position, Height, Nationality

    player = CanonicalPlayer(
        external_id="123",
        source="euroleague",
        first_name="LeBron",
        last_name="James",
        positions=[Position.SF, Position.PF],
        height=Height(cm=206),
        birth_date=date(1984, 12, 30),
        nationality=Nationality(code="USA"),
        jersey_number="23",
    )
"""

from dataclasses import dataclass
from datetime import date

from src.sync.canonical.types import Height, Nationality, Position


@dataclass
class CanonicalPlayer:
    """
    Canonical representation of a basketball player.

    All league adapters convert their player data to this format.

    Attributes:
        external_id: Unique identifier from the source system
        source: Source system name (e.g., "euroleague", "nba", "ibasketball")
        first_name: Player's first name
        last_name: Player's last name
        positions: List of positions the player can play (multiple supported)
        height: Player's height (validated Height dataclass)
        birth_date: Player's birth date
        nationality: Player's nationality (ISO country code)
        jersey_number: Player's jersey number as string (can be "00", "1", etc.)

    Example:
        >>> player = CanonicalPlayer(
        ...     external_id="123",
        ...     source="euroleague",
        ...     first_name="LeBron",
        ...     last_name="James",
        ...     positions=[Position.SF, Position.PF],
        ...     height=Height(cm=206),
        ...     birth_date=date(1984, 12, 30),
        ...     nationality=Nationality(code="USA"),
        ...     jersey_number="23",
        ... )
        >>> player.full_name
        'LeBron James'
        >>> player.primary_position
        <Position.SMALL_FORWARD: 'SF'>
    """

    external_id: str
    source: str
    first_name: str
    last_name: str
    positions: list[Position]
    height: Height | None
    birth_date: date | None
    nationality: Nationality | None
    jersey_number: str | None

    @property
    def full_name(self) -> str:
        """
        Get the player's full name.

        Returns:
            First and last name concatenated with a space.
            Handles cases where either name might be empty.
        """
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def primary_position(self) -> Position | None:
        """
        Get the player's primary (first listed) position.

        Returns:
            First position in the positions list, or None if empty.
        """
        return self.positions[0] if self.positions else None

    @property
    def height_cm(self) -> int | None:
        """
        Get the player's height in centimeters.

        Returns:
            Height in cm, or None if height is not set.
        """
        return self.height.cm if self.height else None

    @property
    def nationality_code(self) -> str | None:
        """
        Get the player's nationality as ISO country code.

        Returns:
            ISO 3166-1 alpha-3 code, or None if nationality is not set.
        """
        return self.nationality.code if self.nationality else None
