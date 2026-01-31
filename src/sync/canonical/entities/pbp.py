"""
Canonical Play-by-Play Event Entity Module

Provides the CanonicalPBPEvent dataclass for standardized play-by-play data.

Usage:
    from src.sync.canonical.entities import CanonicalPBPEvent
    from src.sync.canonical import EventType, ShotType

    event = CanonicalPBPEvent(
        event_number=42,
        period=2,
        clock_seconds=330,  # 5:30 remaining
        event_type=EventType.SHOT,
        shot_type=ShotType.THREE_POINT,
        player_external_id="P123",
        team_external_id="T100",
        success=True,
        coord_x=7.5,
        coord_y=0.5,
    )
"""

from dataclasses import dataclass, field

from src.sync.canonical.types import (
    EventType,
    FoulType,
    ReboundType,
    ShotType,
    TurnoverType,
)


@dataclass
class CanonicalPBPEvent:
    """
    Canonical representation of a play-by-play event.

    All league adapters convert their PBP data to this format.
    Clock time is ALWAYS stored in seconds remaining in the period.

    Attributes:
        event_number: Sequence number of the event in the game
        period: Period number (1-4 for regulation, 5+ for OT)
        clock_seconds: Seconds remaining in the period
        event_type: Type of event (SHOT, ASSIST, REBOUND, etc.)

        Subtypes (set based on event_type):
            shot_type: Type of shot (2PT, 3PT, DUNK, LAYUP)
            rebound_type: Type of rebound (OFFENSIVE, DEFENSIVE)
            foul_type: Type of foul (PERSONAL, TECHNICAL, etc.)
            turnover_type: Type of turnover (TRAVEL, BAD_PASS, etc.)

        Context:
            player_external_id: External ID of the player involved
            player_name: Player's name (for debugging)
            team_external_id: External ID of the team
            success: Whether the action was successful (made/missed)

        Shot details:
            coord_x: X coordinate on court
            coord_y: Y coordinate on court

        Linking:
            related_event_ids: Event numbers of related events

    Example:
        >>> event = CanonicalPBPEvent(
        ...     event_number=42,
        ...     period=2,
        ...     clock_seconds=330,  # 5:30 remaining
        ...     event_type=EventType.SHOT,
        ...     shot_type=ShotType.THREE_POINT,
        ...     player_external_id="P123",
        ...     success=True,
        ... )
    """

    event_number: int
    period: int
    clock_seconds: int
    event_type: EventType

    # Subtypes (set based on event_type)
    shot_type: ShotType | None = field(default=None)
    rebound_type: ReboundType | None = field(default=None)
    foul_type: FoulType | None = field(default=None)
    turnover_type: TurnoverType | None = field(default=None)

    # Context
    player_external_id: str | None = field(default=None)
    player_name: str | None = field(default=None)
    team_external_id: str | None = field(default=None)
    success: bool | None = field(default=None)

    # Shot details
    coord_x: float | None = field(default=None)
    coord_y: float | None = field(default=None)

    # Linking
    related_event_ids: list[int] | None = field(default=None)
