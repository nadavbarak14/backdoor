"""
Canonical Player Stats Entity Module

Provides the CanonicalPlayerStats dataclass for standardized box score data.

Usage:
    from src.sync.canonical.entities import CanonicalPlayerStats

    stats = CanonicalPlayerStats(
        player_external_id="P123",
        player_name="LeBron James",
        team_external_id="T100",
        minutes_seconds=2100,  # 35 minutes
        is_starter=True,
        points=28,
        field_goals_made=10,
        field_goals_attempted=18,
        assists=8,
        total_rebounds=7,
    )
"""

from dataclasses import dataclass, field


@dataclass
class CanonicalPlayerStats:
    """
    Canonical representation of player box score statistics.

    All league adapters convert their stats data to this format.
    Minutes are ALWAYS stored in seconds to avoid format ambiguity.

    Attributes:
        player_external_id: External ID of the player
        player_name: Player's name (for logging/debugging)
        team_external_id: External ID of the team
        minutes_seconds: Playing time in SECONDS (not minutes!)
        is_starter: Whether the player started the game

        Scoring:
            points: Total points scored
            field_goals_made: Field goals made
            field_goals_attempted: Field goals attempted
            two_pointers_made: Two-point field goals made
            two_pointers_attempted: Two-point field goals attempted
            three_pointers_made: Three-point field goals made
            three_pointers_attempted: Three-point field goals attempted
            free_throws_made: Free throws made
            free_throws_attempted: Free throws attempted

        Rebounds:
            offensive_rebounds: Offensive rebounds
            defensive_rebounds: Defensive rebounds
            total_rebounds: Total rebounds

        Other:
            assists: Assists
            turnovers: Turnovers
            steals: Steals
            blocks: Blocks
            personal_fouls: Personal fouls
            plus_minus: Plus/minus rating

    Example:
        >>> stats = CanonicalPlayerStats(
        ...     player_external_id="P123",
        ...     player_name="LeBron James",
        ...     team_external_id="T100",
        ...     minutes_seconds=2100,  # 35 minutes
        ...     points=28,
        ...     assists=8,
        ... )
        >>> stats.minutes_seconds / 60  # Convert to minutes
        35.0
    """

    player_external_id: str
    player_name: str
    team_external_id: str
    minutes_seconds: int
    is_starter: bool = field(default=False)

    # Scoring
    points: int = field(default=0)
    field_goals_made: int = field(default=0)
    field_goals_attempted: int = field(default=0)
    two_pointers_made: int = field(default=0)
    two_pointers_attempted: int = field(default=0)
    three_pointers_made: int = field(default=0)
    three_pointers_attempted: int = field(default=0)
    free_throws_made: int = field(default=0)
    free_throws_attempted: int = field(default=0)

    # Rebounds
    offensive_rebounds: int = field(default=0)
    defensive_rebounds: int = field(default=0)
    total_rebounds: int = field(default=0)

    # Other
    assists: int = field(default=0)
    turnovers: int = field(default=0)
    steals: int = field(default=0)
    blocks: int = field(default=0)
    personal_fouls: int = field(default=0)
    plus_minus: int = field(default=0)
