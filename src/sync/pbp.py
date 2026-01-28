"""
Play-by-Play Utilities Module

Provides shared utilities for processing play-by-play data across all sync sources.
This module centralizes the logic for inferring relationships between PBP events.

Usage:
    from src.sync.pbp import infer_pbp_links

    events = mapper.map_pbp_events(raw_data)
    linked_events = infer_pbp_links(events)
"""

from src.schemas.game import EventType
from src.sync.types import RawPBPEvent


def parse_clock_to_seconds(clock: str) -> float:
    """
    Parse game clock string to seconds remaining in period.

    Args:
        clock: Clock string like "09:45" or "9:45".

    Returns:
        Seconds remaining as float.

    Example:
        >>> parse_clock_to_seconds("09:45")
        585.0
        >>> parse_clock_to_seconds("0:30")
        30.0
    """
    if not clock:
        return 0.0

    try:
        parts = clock.split(":")
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return float(minutes * 60 + seconds)
        return 0.0
    except (ValueError, AttributeError):
        return 0.0


def infer_pbp_links(events: list[RawPBPEvent]) -> list[RawPBPEvent]:
    """
    Infer relationships between play-by-play events.

    Links related events based on timing and type:
    1. ASSIST after made SHOT (same team, <2 sec) -> links to shot
    2. REBOUND after missed SHOT (<3 sec) -> links to shot
    3. STEAL after TURNOVER (diff team, <2 sec) -> links to turnover
    4. BLOCK with missed SHOT (same time) -> links to shot
    5. FREE_THROW after FOUL -> links to foul

    Args:
        events: List of RawPBPEvent objects without links.

    Returns:
        Same events with related_event_numbers populated.

    Example:
        >>> from src.schemas.game import EventType
        >>> shot = RawPBPEvent(
        ...     event_number=1, period=1, clock="09:45",
        ...     event_type=EventType.SHOT, success=True, team_external_id="home"
        ... )
        >>> assist = RawPBPEvent(
        ...     event_number=2, period=1, clock="09:44",
        ...     event_type=EventType.ASSIST, team_external_id="home"
        ... )
        >>> linked = infer_pbp_links([shot, assist])
        >>> linked[1].related_event_numbers
        [1]
    """
    for i, event in enumerate(events):
        # Look at previous events in same period for potential links
        for j in range(i - 1, max(0, i - 10) - 1, -1):
            prev_event = events[j]

            # Must be same period
            if prev_event.period != event.period:
                continue

            prev_time = parse_clock_to_seconds(prev_event.clock)
            curr_time = parse_clock_to_seconds(event.clock)
            time_diff = prev_time - curr_time  # Clock counts down

            # Rule 1: ASSIST after made SHOT (same team, <2 sec)
            if (
                event.event_type == EventType.ASSIST
                and prev_event.event_type == EventType.SHOT
                and prev_event.success is True
                and event.team_external_id == prev_event.team_external_id
                and 0 <= time_diff <= 2
            ):
                event.related_event_numbers = [prev_event.event_number]
                break

            # Rule 2: REBOUND after missed SHOT (<3 sec)
            if (
                event.event_type == EventType.REBOUND
                and prev_event.event_type == EventType.SHOT
                and prev_event.success is False
                and 0 <= time_diff <= 3
            ):
                event.related_event_numbers = [prev_event.event_number]
                break

            # Rule 3: STEAL after TURNOVER (diff team, <2 sec)
            if (
                event.event_type == EventType.STEAL
                and prev_event.event_type == EventType.TURNOVER
                and event.team_external_id != prev_event.team_external_id
                and 0 <= time_diff <= 2
            ):
                event.related_event_numbers = [prev_event.event_number]
                break

            # Rule 4: BLOCK with missed SHOT (same time)
            if (
                event.event_type == EventType.BLOCK
                and prev_event.event_type == EventType.SHOT
                and prev_event.success is False
                and abs(time_diff) <= 1
            ):
                event.related_event_numbers = [prev_event.event_number]
                break

            # Rule 5: FREE_THROW after FOUL
            if (
                event.event_type == EventType.FREE_THROW
                and prev_event.event_type == EventType.FOUL
                and 0 <= time_diff <= 5
            ):
                event.related_event_numbers = [prev_event.event_number]
                break

    return events
