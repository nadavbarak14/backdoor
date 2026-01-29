"""
Canonical Team Entity Module

Provides the CanonicalTeam dataclass for standardized team data.

Usage:
    from src.sync.canonical.entities import CanonicalTeam

    team = CanonicalTeam(
        external_id="100",
        source="euroleague",
        name="Maccabi Tel Aviv",
        short_name="MAC",
        city="Tel Aviv",
        country="Israel",
    )
"""

from dataclasses import dataclass


@dataclass
class CanonicalTeam:
    """
    Canonical representation of a basketball team.

    All league adapters convert their team data to this format.

    Attributes:
        external_id: Unique identifier from the source system
        source: Source system name (e.g., "euroleague", "nba", "ibasketball")
        name: Full team name
        short_name: Abbreviated team name (3-4 characters typically)
        city: City where the team is based
        country: Country where the team is based

    Example:
        >>> team = CanonicalTeam(
        ...     external_id="100",
        ...     source="euroleague",
        ...     name="Maccabi Tel Aviv",
        ...     short_name="MAC",
        ...     city="Tel Aviv",
        ...     country="Israel",
        ... )
    """

    external_id: str
    source: str
    name: str
    short_name: str | None
    city: str | None
    country: str | None
