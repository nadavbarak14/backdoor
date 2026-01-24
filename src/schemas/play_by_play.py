"""
Play-by-Play Schema Module

Pydantic schemas for play-by-play event data:
- PlayByPlayEventResponse: Individual event response
- PlayByPlayResponse: Complete game play-by-play
- PlayByPlayFilter: Query parameter validation for filtering events

Usage:
    from src.schemas.play_by_play import PlayByPlayResponse, PlayByPlayFilter

    @router.get("/games/{game_id}/play-by-play")
    def get_play_by_play(game_id: UUID, filters: PlayByPlayFilter = Depends()):
        ...
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.base import OrmBase


class PlayByPlayEventResponse(OrmBase):
    """
    Schema for individual play-by-play event response.

    Contains detailed information about a single game event.

    Attributes:
        id: Unique event identifier.
        game_id: UUID of the game.
        event_number: Sequence number within the game.
        period: Period/quarter number (1-4 for regulation, 5+ for OT).
        clock: Game clock time (e.g., "10:30").
        event_type: Type of event (SHOT, REBOUND, etc.).
        event_subtype: Subtype for additional detail (e.g., "3PT", "OFFENSIVE").
        player_id: UUID of the player involved (nullable for team events).
        player_name: Name of the player involved (nullable for team events).
        team_id: UUID of the team involved.
        team_name: Name of the team involved.
        success: Whether the action was successful (for shots, nullable).
        coord_x: X coordinate on court (nullable).
        coord_y: Y coordinate on court (nullable).
        attributes: Extensible event attributes.
        description: Human-readable description of the event.
        related_event_ids: IDs of events linked to this one.

    Example:
        >>> event = PlayByPlayEventResponse(
        ...     id=event_uuid,
        ...     game_id=game_uuid,
        ...     event_number=42,
        ...     period=2,
        ...     clock="5:30",
        ...     event_type="SHOT",
        ...     event_subtype="3PT",
        ...     player_id=player_uuid,
        ...     player_name="Stephen Curry",
        ...     team_id=team_uuid,
        ...     team_name="Golden State Warriors",
        ...     success=True,
        ...     coord_x=7.5,
        ...     coord_y=0.5,
        ...     attributes={"shot_distance": 24.5},
        ...     description="Curry makes 3PT from top of key",
        ...     related_event_ids=[assist_event_uuid]
        ... )
    """

    id: UUID
    game_id: UUID
    event_number: int
    period: int
    clock: str
    event_type: str
    event_subtype: str | None
    player_id: UUID | None
    player_name: str | None
    team_id: UUID
    team_name: str
    success: bool | None
    coord_x: float | None
    coord_y: float | None
    attributes: dict[str, Any]
    description: str | None
    related_event_ids: list[UUID]


class PlayByPlayResponse(BaseModel):
    """
    Schema for complete game play-by-play response.

    Contains all play-by-play events for a game.

    Attributes:
        game_id: UUID of the game.
        events: List of play-by-play events.
        total_events: Total number of events in the game.

    Example:
        >>> response = PlayByPlayResponse(
        ...     game_id=game_uuid,
        ...     events=[event1, event2, event3, ...],
        ...     total_events=425
        ... )
    """

    game_id: UUID
    events: list[PlayByPlayEventResponse]
    total_events: int


class PlayByPlayFilter(BaseModel):
    """
    Schema for filtering play-by-play events.

    Used as query parameters for play-by-play endpoints.
    All fields are optional filters.

    Attributes:
        period: Filter by period number.
        event_type: Filter by event type (SHOT, REBOUND, etc.).
        player_id: Filter by player UUID.
        team_id: Filter by team UUID.

    Example:
        >>> filters = PlayByPlayFilter(
        ...     period=4,
        ...     event_type="SHOT",
        ...     team_id=team_uuid
        ... )
    """

    period: int | None = Field(None, ge=1, description="Filter by period number")
    event_type: str | None = Field(
        None, description="Filter by event type (SHOT, REBOUND, etc.)"
    )
    player_id: UUID | None = Field(None, description="Filter by player UUID")
    team_id: UUID | None = Field(None, description="Filter by team UUID")
