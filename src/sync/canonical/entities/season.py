"""
Canonical Season Entity Module

Provides the CanonicalSeason dataclass for standardized season data.

Usage:
    from src.sync.canonical.entities import CanonicalSeason
    from datetime import date

    season = CanonicalSeason(
        external_id="E2024",
        source="euroleague",
        name="2024-25",
        start_date=date(2024, 10, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
    )
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class CanonicalSeason:
    """
    Canonical representation of a basketball season.

    All league adapters convert their season data to this format.

    Attributes:
        external_id: Unique identifier from the source system
        source: Source system name (e.g., "euroleague", "nba", "ibasketball")
        name: Season name in YYYY-YY format (e.g., "2024-25")
        start_date: First day of the season
        end_date: Last day of the season
        is_current: Whether this is the current/active season

    Example:
        >>> season = CanonicalSeason(
        ...     external_id="E2024",
        ...     source="euroleague",
        ...     name="2024-25",
        ...     start_date=date(2024, 10, 1),
        ...     end_date=date(2025, 5, 31),
        ...     is_current=True,
        ... )
    """

    external_id: str
    source: str
    name: str
    start_date: date | None
    end_date: date | None
    is_current: bool = field(default=False)
