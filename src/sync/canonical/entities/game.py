"""
Canonical Game Entity Module

Provides the CanonicalGame dataclass for standardized game data.

Usage:
    from src.sync.canonical.entities import CanonicalGame
    from datetime import datetime

    game = CanonicalGame(
        external_id="G123",
        source="euroleague",
        season_external_id="E2024",
        home_team_external_id="T100",
        away_team_external_id="T200",
        game_date=datetime(2024, 11, 15, 20, 0),
        status="FINAL",
        home_score=85,
        away_score=78,
        venue="Menora Mivtachim Arena",
    )
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CanonicalGame:
    """
    Canonical representation of a basketball game.

    All league adapters convert their game data to this format.

    Attributes:
        external_id: Unique identifier from the source system
        source: Source system name (e.g., "euroleague", "nba", "ibasketball")
        season_external_id: External ID of the season this game belongs to
        home_team_external_id: External ID of the home team
        away_team_external_id: External ID of the away team
        game_date: Date and time of the game
        status: Game status ("SCHEDULED", "LIVE", "FINAL", "POSTPONED", "CANCELLED")
        home_score: Home team's final score (None if not yet played)
        away_score: Away team's final score (None if not yet played)
        venue: Name of the venue/arena

    Example:
        >>> game = CanonicalGame(
        ...     external_id="G123",
        ...     source="euroleague",
        ...     season_external_id="E2024",
        ...     home_team_external_id="T100",
        ...     away_team_external_id="T200",
        ...     game_date=datetime(2024, 11, 15, 20, 0),
        ...     status="FINAL",
        ...     home_score=85,
        ...     away_score=78,
        ... )
    """

    external_id: str
    source: str
    season_external_id: str
    home_team_external_id: str
    away_team_external_id: str
    game_date: datetime
    status: str
    home_score: int | None
    away_score: int | None
    venue: str | None = field(default=None)
