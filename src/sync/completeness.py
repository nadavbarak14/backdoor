"""
Completeness Detection Module

Provides functions to detect incomplete data in the sync pipeline.
Used to identify records that need to be resynced from external sources.

Completeness Criteria:
    - Player: has height AND birth_date AND positions not empty
    - Game: has PlayerGameStats AND has PlayByPlayEvents
    - Team: has name AND short_name

Usage:
    from src.sync.completeness import (
        get_incomplete_players,
        get_games_without_stats,
        get_sync_completeness_report,
    )

    # Find players missing bio data
    incomplete = get_incomplete_players(db, source="euroleague")

    # Get overall completeness report
    report = get_sync_completeness_report(db)
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.play_by_play import PlayByPlayEvent
from src.models.player import Player
from src.models.team import Team


def get_incomplete_players(
    db: Session,
    source: str | None = None,
    limit: int | None = None,
) -> list[Player]:
    """
    Find players missing bio data.

    A player is considered incomplete if any of the following are true:
    - height_cm is None
    - birth_date is None
    - positions is empty (empty JSON array)

    Args:
        db: Database session.
        source: Optional - only check players from this source.
            Filters by external_ids containing the source key.
        limit: Optional - maximum number of players to return.

    Returns:
        List of Player objects with missing bio data.

    Example:
        >>> incomplete = get_incomplete_players(db, source="euroleague")
        >>> for player in incomplete:
        ...     print(f"{player.full_name}: missing data")
    """
    stmt = select(Player).where(
        or_(
            Player.height_cm.is_(None),
            Player.birth_date.is_(None),
            func.json_array_length(Player.positions) == 0,
        )
    )

    if source:
        # Filter by external_ids containing source key
        # Use json_extract for SQLite compatibility
        stmt = stmt.where(
            func.json_extract(Player.external_ids, f"$.{source}").isnot(None)
        )

    stmt = stmt.order_by(Player.last_name, Player.first_name)

    if limit:
        stmt = stmt.limit(limit)

    return list(db.scalars(stmt).all())


def get_games_without_stats(
    db: Session,
    source: str | None = None,
    limit: int | None = None,
) -> list[Game]:
    """
    Find FINAL games that have no PlayerGameStats records.

    Only returns games that are marked as FINAL (completed games).
    Games in progress or scheduled are excluded.

    Args:
        db: Database session.
        source: Optional - only check games from this source.
            Filters by external_ids containing the source key.
        limit: Optional - maximum number of games to return.

    Returns:
        List of Game objects without boxscore data.

    Example:
        >>> games = get_games_without_stats(db, source="winner")
        >>> print(f"Need to sync stats for {len(games)} games")
    """
    # Subquery: game IDs that have PlayerGameStats
    has_stats = select(PlayerGameStats.game_id).distinct().subquery()

    stmt = (
        select(Game)
        .where(
            Game.status == "FINAL",
            Game.id.notin_(select(has_stats.c.game_id)),
        )
        .order_by(Game.game_date.desc())
    )

    if source:
        # Use json_extract for SQLite compatibility
        stmt = stmt.where(
            func.json_extract(Game.external_ids, f"$.{source}").isnot(None)
        )

    if limit:
        stmt = stmt.limit(limit)

    return list(db.scalars(stmt).all())


def get_games_without_pbp(
    db: Session,
    source: str | None = None,
    limit: int | None = None,
) -> list[Game]:
    """
    Find FINAL games that have no PlayByPlayEvent records.

    Only returns games that are marked as FINAL (completed games).
    Games in progress or scheduled are excluded.

    Args:
        db: Database session.
        source: Optional - only check games from this source.
            Filters by external_ids containing the source key.
        limit: Optional - maximum number of games to return.

    Returns:
        List of Game objects without play-by-play data.

    Example:
        >>> games = get_games_without_pbp(db, source="euroleague")
        >>> for game in games:
        ...     print(f"Missing PBP: {game.game_date}")
    """
    # Subquery: game IDs that have PlayByPlayEvent
    has_pbp = select(PlayByPlayEvent.game_id).distinct().subquery()

    stmt = (
        select(Game)
        .where(
            Game.status == "FINAL",
            Game.id.notin_(select(has_pbp.c.game_id)),
        )
        .order_by(Game.game_date.desc())
    )

    if source:
        # Use json_extract for SQLite compatibility
        stmt = stmt.where(
            func.json_extract(Game.external_ids, f"$.{source}").isnot(None)
        )

    if limit:
        stmt = stmt.limit(limit)

    return list(db.scalars(stmt).all())


def get_incomplete_teams(
    db: Session,
    source: str | None = None,
    limit: int | None = None,
) -> list[Team]:
    """
    Find teams missing required data.

    A team is considered incomplete if:
    - name is None or empty
    - short_name is None or empty

    Args:
        db: Database session.
        source: Optional - only check teams from this source.
        limit: Optional - maximum number of teams to return.

    Returns:
        List of Team objects with missing data.

    Example:
        >>> teams = get_incomplete_teams(db)
        >>> print(f"Found {len(teams)} incomplete teams")
    """
    stmt = select(Team).where(
        or_(
            Team.name.is_(None),
            Team.name == "",
            Team.short_name.is_(None),
            Team.short_name == "",
        )
    )

    if source:
        # Use json_extract for SQLite compatibility
        stmt = stmt.where(
            func.json_extract(Team.external_ids, f"$.{source}").isnot(None)
        )

    stmt = stmt.order_by(Team.name)

    if limit:
        stmt = stmt.limit(limit)

    return list(db.scalars(stmt).all())


def get_sync_completeness_report(
    db: Session,
    source: str | None = None,
) -> dict:
    """
    Get overall sync completeness statistics.

    Returns counts of total and incomplete records for each entity type.

    Args:
        db: Database session.
        source: Optional - filter by data source.

    Returns:
        Dict with completeness stats:
        {
            "players": {"total": 100, "incomplete": 5, "complete_pct": 95.0},
            "games": {
                "total": 50,
                "without_stats": 2,
                "without_pbp": 3,
                "stats_pct": 96.0,
                "pbp_pct": 94.0,
            },
            "teams": {"total": 20, "incomplete": 0, "complete_pct": 100.0},
        }

    Example:
        >>> report = get_sync_completeness_report(db, source="euroleague")
        >>> print(f"Players: {report['players']['complete_pct']}% complete")
    """
    # Count total players
    player_query = select(func.count()).select_from(Player)
    if source:
        player_query = player_query.where(
            func.json_extract(Player.external_ids, f"$.{source}").isnot(None)
        )
    total_players = db.execute(player_query).scalar() or 0

    incomplete_players = len(get_incomplete_players(db, source))

    # Count total FINAL games
    game_query = select(func.count()).select_from(Game).where(Game.status == "FINAL")
    if source:
        game_query = game_query.where(
            func.json_extract(Game.external_ids, f"$.{source}").isnot(None)
        )
    total_games = db.execute(game_query).scalar() or 0

    games_without_stats = len(get_games_without_stats(db, source))
    games_without_pbp = len(get_games_without_pbp(db, source))

    # Count total teams
    team_query = select(func.count()).select_from(Team)
    if source:
        team_query = team_query.where(
            func.json_extract(Team.external_ids, f"$.{source}").isnot(None)
        )
    total_teams = db.execute(team_query).scalar() or 0

    incomplete_teams = len(get_incomplete_teams(db, source))

    # Calculate percentages
    def pct(complete: int, total: int) -> float:
        if total == 0:
            return 100.0
        return round(complete / total * 100, 1)

    return {
        "players": {
            "total": total_players,
            "incomplete": incomplete_players,
            "complete_pct": pct(total_players - incomplete_players, total_players),
        },
        "games": {
            "total": total_games,
            "without_stats": games_without_stats,
            "without_pbp": games_without_pbp,
            "stats_pct": pct(total_games - games_without_stats, total_games),
            "pbp_pct": pct(total_games - games_without_pbp, total_games),
        },
        "teams": {
            "total": total_teams,
            "incomplete": incomplete_teams,
            "complete_pct": pct(total_teams - incomplete_teams, total_teams),
        },
    }
