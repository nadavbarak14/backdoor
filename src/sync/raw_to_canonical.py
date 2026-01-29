"""
Raw to Canonical Conversion Utilities

Provides functions to convert Raw types to Canonical types during the
migration away from Raw types. This module serves as a bridge to enable
incremental migration.

These utilities will be removed once adapters are updated to use
converters directly (returning Canonical types instead of Raw types).

Usage:
    from src.sync.raw_to_canonical import (
        raw_game_to_canonical,
        raw_boxscore_to_canonical_stats,
        raw_pbp_to_canonical,
    )

    # Convert RawGame to CanonicalGame
    canonical = raw_game_to_canonical(raw_game, source="winner")

    # Convert RawBoxScore player stats to list of CanonicalPlayerStats
    stats = raw_boxscore_to_canonical_stats(raw_boxscore)
"""

from src.schemas.enums import GameStatus
from src.sync.canonical.entities import (
    CanonicalGame,
    CanonicalPBPEvent,
    CanonicalPlayerStats,
)
from src.sync.canonical.types import EventType
from src.sync.types import RawBoxScore, RawGame, RawPBPEvent, RawPlayerStats


def raw_game_to_canonical(
    raw: RawGame, source: str, season_external_id: str = ""
) -> CanonicalGame:
    """
    Convert a RawGame to CanonicalGame.

    Args:
        raw: RawGame from adapter.
        source: Data source name (e.g., "winner", "euroleague").
        season_external_id: External ID of the season (required by CanonicalGame).

    Returns:
        CanonicalGame with validated data.

    Example:
        >>> canonical = raw_game_to_canonical(raw_game, "winner", "2024-25")
    """
    # Convert status to string - CanonicalGame.status is a string
    if isinstance(raw.status, GameStatus):
        status_str = raw.status.value
    else:
        status_str = str(raw.status)

    return CanonicalGame(
        external_id=raw.external_id,
        source=source,
        season_external_id=season_external_id,
        home_team_external_id=raw.home_team_external_id,
        away_team_external_id=raw.away_team_external_id,
        game_date=raw.game_date,
        status=status_str,
        home_score=raw.home_score,
        away_score=raw.away_score,
    )


def raw_player_stats_to_canonical(raw: RawPlayerStats) -> CanonicalPlayerStats:
    """
    Convert RawPlayerStats to CanonicalPlayerStats.

    Args:
        raw: RawPlayerStats from boxscore.

    Returns:
        CanonicalPlayerStats with minutes in seconds.

    Example:
        >>> canonical = raw_player_stats_to_canonical(player_stats)
    """
    return CanonicalPlayerStats(
        player_external_id=raw.player_external_id,
        player_name=raw.player_name,
        team_external_id=raw.team_external_id,
        minutes_seconds=raw.minutes_played,  # Already in seconds
        is_starter=raw.is_starter,
        points=raw.points,
        field_goals_made=raw.field_goals_made,
        field_goals_attempted=raw.field_goals_attempted,
        two_pointers_made=raw.two_pointers_made,
        two_pointers_attempted=raw.two_pointers_attempted,
        three_pointers_made=raw.three_pointers_made,
        three_pointers_attempted=raw.three_pointers_attempted,
        free_throws_made=raw.free_throws_made,
        free_throws_attempted=raw.free_throws_attempted,
        offensive_rebounds=raw.offensive_rebounds,
        defensive_rebounds=raw.defensive_rebounds,
        total_rebounds=raw.total_rebounds,
        assists=raw.assists,
        turnovers=raw.turnovers,
        steals=raw.steals,
        blocks=raw.blocks,
        personal_fouls=raw.personal_fouls,
        plus_minus=raw.plus_minus,
    )


def raw_boxscore_to_canonical_stats(raw: RawBoxScore) -> list[CanonicalPlayerStats]:
    """
    Convert RawBoxScore to list of CanonicalPlayerStats.

    Args:
        raw: RawBoxScore with home_players and away_players.

    Returns:
        List of CanonicalPlayerStats for all players.

    Example:
        >>> stats = raw_boxscore_to_canonical_stats(boxscore)
    """
    canonical_stats: list[CanonicalPlayerStats] = []

    for player_stats in raw.home_players:
        canonical_stats.append(raw_player_stats_to_canonical(player_stats))

    for player_stats in raw.away_players:
        canonical_stats.append(raw_player_stats_to_canonical(player_stats))

    return canonical_stats


def raw_pbp_to_canonical(raw: RawPBPEvent) -> CanonicalPBPEvent:
    """
    Convert RawPBPEvent to CanonicalPBPEvent.

    Args:
        raw: RawPBPEvent from adapter.

    Returns:
        CanonicalPBPEvent with validated data.

    Example:
        >>> canonical = raw_pbp_to_canonical(event)
    """
    # Convert event_type - already EventType enum
    event_type = (
        raw.event_type
        if isinstance(raw.event_type, EventType)
        else EventType(raw.event_type)
    )

    # Parse clock string to seconds
    clock_seconds = _parse_clock_to_seconds(raw.clock)

    return CanonicalPBPEvent(
        event_number=raw.event_number,
        period=raw.period,
        clock_seconds=clock_seconds,
        event_type=event_type,
        player_external_id=raw.player_external_id,
        player_name=raw.player_name,
        team_external_id=raw.team_external_id,
        success=raw.success,
        coord_x=raw.coord_x,
        coord_y=raw.coord_y,
        related_event_ids=raw.related_event_numbers,
    )


def raw_pbp_list_to_canonical(events: list[RawPBPEvent]) -> list[CanonicalPBPEvent]:
    """
    Convert list of RawPBPEvent to list of CanonicalPBPEvent.

    Args:
        events: List of RawPBPEvent from adapter.

    Returns:
        List of CanonicalPBPEvent.

    Example:
        >>> canonical_events = raw_pbp_list_to_canonical(raw_events)
    """
    return [raw_pbp_to_canonical(e) for e in events]


def _parse_clock_to_seconds(clock: str) -> int:
    """
    Parse clock string (MM:SS) to total seconds.

    Args:
        clock: Clock string like "10:30" or "5:05".

    Returns:
        Total seconds (10:30 -> 630).
    """
    if not clock or ":" not in clock:
        return 0

    try:
        parts = clock.split(":")
        minutes = int(parts[0])
        seconds = int(parts[1]) if len(parts) > 1 else 0
        return minutes * 60 + seconds
    except (ValueError, IndexError):
        return 0
