"""
Universal Query Stats Tool Module

Provides a flexible query_stats tool for complex basketball analytics queries.
This tool supports filtering by league, season, team, and players with
configurable metrics and output controls.

Usage:
    from src.services.query_stats import query_stats

    result = query_stats.invoke({
        "team_name": "Maccabi Tel-Aviv",
        "metrics": ["points", "rebounds", "assists"],
        "db": db_session
    })
"""

from langchain_core.tools import tool
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.models.player import Player
from src.models.stats import PlayerSeasonStats
from src.models.team import Team
from src.schemas.player import PlayerFilter
from src.schemas.team import TeamFilter
from src.services.league import SeasonService
from src.services.player import PlayerService
from src.services.player_stats import PlayerSeasonStatsService
from src.services.team import TeamService

# Response size constants to prevent context blowup
MAX_RESPONSE_ROWS = 20
MAX_RESPONSE_CHARS = 2500


# =============================================================================
# Helper Functions
# =============================================================================


def _resolve_league_by_name(db: Session, name: str) -> League | None:
    """Resolve a league name to a League entity."""
    stmt = select(League).where(
        or_(
            League.name.ilike(f"%{name}%"),
            League.code.ilike(f"%{name}%"),
        )
    )
    return db.scalars(stmt).first()


def _resolve_team_by_name(db: Session, name: str) -> Team | None:
    """Resolve a team name to a Team entity."""
    service = TeamService(db)
    teams, _ = service.get_filtered(TeamFilter(search=name), limit=10)
    return teams[0] if teams else None


def _resolve_player_by_name(db: Session, name: str) -> Player | None:
    """Resolve a player name to a Player entity."""
    service = PlayerService(db)
    players, _ = service.get_filtered(PlayerFilter(search=name), limit=10)
    return players[0] if players else None


def _resolve_season(
    db: Session,
    season_name: str | None = None,
    league_id=None,
) -> Season | None:
    """Resolve a season by name or get current season."""
    season_service = SeasonService(db)

    if season_name:
        stmt = select(Season).where(Season.name.ilike(f"%{season_name}%"))
        if league_id:
            stmt = stmt.where(Season.league_id == league_id)
        return db.scalars(stmt).first()

    return season_service.get_current(league_id)


# =============================================================================
# Metric Formatting
# =============================================================================


def _format_metric_header(metric: str) -> str:
    """Format metric name for table header."""
    headers = {
        "points": "PTS",
        "rebounds": "REB",
        "assists": "AST",
        "steals": "STL",
        "blocks": "BLK",
        "turnovers": "TO",
        "fg_pct": "FG%",
        "three_pct": "3P%",
        "ft_pct": "FT%",
        "plus_minus": "+/-",
        "minutes": "MIN",
        "games": "GP",
    }
    return headers.get(metric, metric.upper())


def _get_metric_value(stats: PlayerSeasonStats, metric: str, per: str) -> str:
    """Extract and format a metric value from stats object."""
    attr_map = {
        "points": ("avg_points", "total_points"),
        "rebounds": ("avg_rebounds", "total_rebounds"),
        "assists": ("avg_assists", "total_assists"),
        "steals": ("avg_steals", "total_steals"),
        "blocks": ("avg_blocks", "total_blocks"),
        "turnovers": ("avg_turnovers", "total_turnovers"),
        "fg_pct": ("field_goal_pct", "field_goal_pct"),
        "three_pct": ("three_point_pct", "three_point_pct"),
        "ft_pct": ("free_throw_pct", "free_throw_pct"),
        "plus_minus": ("avg_plus_minus", "total_plus_minus"),
        "minutes": ("avg_minutes", "total_minutes"),
        "games": ("games_played", "games_played"),
    }

    if metric not in attr_map:
        return "N/A"

    avg_attr, total_attr = attr_map[metric]
    value = getattr(stats, total_attr if per == "total" else avg_attr, None)

    if value is None:
        return "N/A"

    # Format based on metric type
    if metric in ("fg_pct", "three_pct", "ft_pct"):
        return f"{value * 100:.1f}%" if value else "0.0%"
    elif metric == "plus_minus":
        return f"{value:+.1f}" if per != "total" else f"{int(value):+d}"
    elif metric == "games" or per == "total":
        return f"{int(value)}"
    else:
        return f"{value:.1f}"


def _truncate_response(response: str, shown: int, total: int) -> str:
    """Truncate response if it exceeds size limits."""
    if len(response) > MAX_RESPONSE_CHARS:
        cutoff = response[:MAX_RESPONSE_CHARS].rfind("\n")
        if cutoff > 0:
            response = response[:cutoff]
            response += "\n\n*... truncated. Showing partial results.*"
    elif shown < total:
        response += f"\n\n*Showing {shown} of {total} results.*"
    return response


# =============================================================================
# Query Handlers
# =============================================================================


def _query_player_stats(
    db: Session,
    players: list[Player],
    season: Season,
    metrics: list[str],
    per: str,
    limit: int,
) -> str:
    """Query stats for specific players."""
    service = PlayerSeasonStatsService(db)

    lines = [f"## Player Stats - {season.name}", ""]

    # Build header
    header = "| Player | Team |"
    separator = "|--------|------|"
    for metric in metrics:
        header += f" {_format_metric_header(metric)} |"
        separator += "------|"
    lines.extend([header, separator])

    row_count = 0
    for player in players[:limit]:
        stats_list = service.get_player_season(player.id, season.id)
        if not stats_list:
            continue

        stats = stats_list[0]
        team_name = stats.team.short_name if stats.team else "N/A"
        player_name = f"{player.first_name} {player.last_name}"

        row = f"| {player_name} | {team_name} |"
        for metric in metrics:
            row += f" {_get_metric_value(stats, metric, per)} |"
        lines.append(row)
        row_count += 1

    if row_count == 0:
        return f"No stats found for the specified players in {season.name}."

    return _truncate_response("\n".join(lines), row_count, len(players))


def _query_team_stats(
    db: Session,
    team: Team,
    season: Season,
    metrics: list[str],
    per: str,
    limit: int,
) -> str:
    """Query stats for all players on a team."""
    stmt = (
        select(PlayerSeasonStats)
        .where(PlayerSeasonStats.team_id == team.id)
        .where(PlayerSeasonStats.season_id == season.id)
        .order_by(PlayerSeasonStats.avg_points.desc())
        .limit(limit)
    )
    all_stats = list(db.scalars(stmt).all())

    if not all_stats:
        return f"No stats found for {team.name} in {season.name}."

    lines = [f"## {team.name} - {season.name}", ""]

    header = "| Player |"
    separator = "|--------|"
    for metric in metrics:
        header += f" {_format_metric_header(metric)} |"
        separator += "------|"
    lines.extend([header, separator])

    for stats in all_stats:
        player = stats.player
        player_name = f"{player.first_name} {player.last_name}"
        row = f"| {player_name} |"
        for metric in metrics:
            row += f" {_get_metric_value(stats, metric, per)} |"
        lines.append(row)

    return _truncate_response("\n".join(lines), len(all_stats), len(all_stats))


def _query_league_stats(
    db: Session,
    league: League | None,
    season: Season,
    metrics: list[str],
    per: str,
    limit: int,
) -> str:
    """Query league-wide stats (leaderboard mode)."""
    service = PlayerSeasonStatsService(db)

    sort_metric = metrics[0] if metrics else "points"
    sort_attr_map = {
        "points": "avg_points",
        "rebounds": "avg_rebounds",
        "assists": "avg_assists",
        "steals": "avg_steals",
        "blocks": "avg_blocks",
        "fg_pct": "field_goal_pct",
        "three_pct": "three_point_pct",
        "ft_pct": "free_throw_pct",
    }
    sort_attr = sort_attr_map.get(sort_metric, "avg_points")

    try:
        leaders = service.get_league_leaders(
            season.id, category=sort_attr, limit=limit, min_games=1
        )
    except ValueError:
        leaders = service.get_league_leaders(
            season.id, category="avg_points", limit=limit, min_games=1
        )

    if not leaders:
        league_str = f" in {league.name}" if league else ""
        return f"No stats found for {season.name}{league_str}."

    league_str = f"{league.name} - " if league else ""
    lines = [
        f"## {league_str}{season.name} Leaders",
        f"*Sorted by {_format_metric_header(sort_metric)}*",
        "",
    ]

    header = "| # | Player | Team |"
    separator = "|---|--------|------|"
    for metric in metrics:
        header += f" {_format_metric_header(metric)} |"
        separator += "------|"
    lines.extend([header, separator])

    for i, stats in enumerate(leaders, 1):
        player = stats.player
        player_name = f"{player.first_name} {player.last_name}"
        team_name = stats.team.short_name if stats.team else "N/A"

        row = f"| {i} | {player_name} | {team_name} |"
        for metric in metrics:
            row += f" {_get_metric_value(stats, metric, per)} |"
        lines.append(row)

    return _truncate_response("\n".join(lines), len(leaders), len(leaders))


# =============================================================================
# Main Tool
# =============================================================================


@tool
def query_stats(
    league_name: str | None = None,
    season: str | None = None,
    team_name: str | None = None,
    player_names: list[str] | None = None,
    metrics: list[str] | None = None,
    limit: int = 10,
    per: str = "game",
    db: Session | None = None,
) -> str:
    """
    Universal stats query tool for flexible basketball analytics.

    Use this tool for complex queries combining filters and metrics.
    Supports querying by league, season, team, or specific players.

    Args:
        league_name: Filter by league (e.g., "Israeli", "Winner League").
        season: Filter by season (e.g., "2024-25"). Defaults to current.
        team_name: Filter by team (e.g., "Maccabi Tel-Aviv").
        player_names: Specific player(s) to query.
        metrics: Stats to return. Options: points, rebounds, assists,
            steals, blocks, turnovers, fg_pct, three_pct, ft_pct,
            plus_minus, minutes, games. Defaults to basic stats.
        limit: Maximum rows to return (default 10, max 20).
        per: "game" (averages), "total" (season totals). Default "game".
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted stats table. Truncated if too large.

    Example queries:
        - "Get Maccabi's stats this season"
        - "Jimmy Clark's scoring numbers"
        - "Top 10 scorers in the league"
    """
    if db is None:
        return "Error: Database session not provided."

    if metrics is None:
        metrics = ["points", "rebounds", "assists", "fg_pct"]

    limit = min(limit, MAX_RESPONSE_ROWS)

    # Resolve league
    league = None
    if league_name:
        league = _resolve_league_by_name(db, league_name)
        if not league:
            return f"League '{league_name}' not found."

    # Resolve season
    league_id = league.id if league else None
    season_obj = _resolve_season(db, season, league_id)
    if not season_obj:
        return "No season found. Please specify a season."

    # Resolve team
    team = None
    if team_name:
        team = _resolve_team_by_name(db, team_name)
        if not team:
            return f"Team '{team_name}' not found."

    # Resolve players
    players: list[Player] = []
    if player_names:
        for name in player_names:
            player = _resolve_player_by_name(db, name)
            if player:
                players.append(player)
            else:
                return f"Player '{name}' not found."

    # Execute query based on mode
    if players:
        return _query_player_stats(db, players, season_obj, metrics, per, limit)
    elif team:
        return _query_team_stats(db, team, season_obj, metrics, per, limit)
    else:
        return _query_league_stats(db, league, season_obj, metrics, per, limit)
