"""
Universal Query Stats Tool Module

Provides a flexible query_stats tool for complex basketball analytics queries.
This tool supports filtering by league, season, team, and players with
configurable metrics, time-based filters, location filters, and output controls.

Usage:
    from src.services.query_stats import query_stats

    # Basic query
    result = query_stats.invoke({
        "team_name": "Maccabi Tel-Aviv",
        "metrics": ["points", "rebounds", "assists"],
        "db": db_session
    })

    # With time filters
    result = query_stats.invoke({
        "player_names": ["Jimmy Clark"],
        "quarter": 4,
        "clutch_only": True,
        "db": db_session
    })

    # With location filters
    result = query_stats.invoke({
        "player_names": ["Jimmy Clark"],
        "home_only": True,
        "db": db_session
    })

    # With opponent filter
    result = query_stats.invoke({
        "player_names": ["Jimmy Clark"],
        "opponent_team": "Hapoel Jerusalem",
        "db": db_session
    })
"""

from langchain_core.tools import tool
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.models.game import Game, PlayerGameStats
from src.models.league import League, Season
from src.models.player import Player
from src.models.stats import PlayerSeasonStats
from src.models.team import Team
from src.schemas.analytics import ClutchFilter, TimeFilter
from src.schemas.player import PlayerFilter
from src.schemas.team import TeamFilter
from src.services.analytics import AnalyticsService
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
# Time Filter Helpers
# =============================================================================


def _validate_time_filters(
    quarter: int | None,
    quarters: list[int] | None,
) -> str | None:
    """Validate time filter parameters. Returns error message or None."""
    if quarter is not None and quarters is not None:
        return "Error: 'quarter' and 'quarters' are mutually exclusive."
    if quarter is not None and not (1 <= quarter <= 4):
        return "Error: 'quarter' must be between 1 and 4."
    if quarters is not None:
        for q in quarters:
            if not (1 <= q <= 4):
                return f"Error: Quarter {q} must be between 1 and 4."
    return None


def _validate_location_filters(
    home_only: bool,
    away_only: bool,
) -> str | None:
    """Validate location filter parameters. Returns error message or None."""
    if home_only and away_only:
        return "Error: 'home_only' and 'away_only' are mutually exclusive."
    return None


def _has_time_filters(
    quarter: int | None,
    quarters: list[int] | None,
    clutch_only: bool,
    exclude_garbage_time: bool,
) -> bool:
    """Check if any time-based filters are active."""
    return (
        quarter is not None
        or quarters is not None
        or clutch_only
        or exclude_garbage_time
    )


def _has_location_filters(
    home_only: bool,
    away_only: bool,
    opponent_team_id=None,
) -> bool:
    """Check if any location/opponent filters are active."""
    return home_only or away_only or opponent_team_id is not None


def _get_recent_games(
    db: Session,
    season: Season,
    player_id=None,
    team_id=None,
    last_n_games: int | None = None,
    home_only: bool = False,
    away_only: bool = False,
    opponent_team_id=None,
) -> list[Game]:
    """
    Get recent games for a player or team, optionally limited to N games.

    Args:
        db: Database session.
        season: Season to filter games by.
        player_id: Filter games where this player played.
        team_id: Filter games involving this team.
        last_n_games: Limit to most recent N games.
        home_only: Only include home games (requires team_id or player with team).
        away_only: Only include away games (requires team_id or player with team).
        opponent_team_id: Only include games against this opponent.

    Returns:
        List of Game objects matching the criteria.
    """
    has_location_filters = home_only or away_only or opponent_team_id

    if player_id:
        # For player queries with location filters, we need post-query filtering
        # because the player's team may vary per game
        if has_location_filters:
            stmt = (
                select(Game, PlayerGameStats.team_id)
                .join(PlayerGameStats, Game.id == PlayerGameStats.game_id)
                .where(PlayerGameStats.player_id == player_id)
                .where(Game.season_id == season.id)
                .order_by(Game.game_date.desc())
            )
            if last_n_games:
                stmt = stmt.limit(last_n_games)

            result = db.execute(stmt).all()

            # Post-filter based on location/opponent
            filtered_games = []
            for game, player_team_id in result:
                # Check home/away based on player's team
                if home_only and game.home_team_id != player_team_id:
                    continue
                if away_only and game.away_team_id != player_team_id:
                    continue
                # Check opponent filter
                if opponent_team_id:
                    game_opponent = (
                        game.away_team_id
                        if game.home_team_id == player_team_id
                        else game.home_team_id
                    )
                    if game_opponent != opponent_team_id:
                        continue
                filtered_games.append(game)
            return filtered_games
        else:
            # Simple player query without location filters
            stmt = (
                select(Game)
                .join(PlayerGameStats, Game.id == PlayerGameStats.game_id)
                .where(PlayerGameStats.player_id == player_id)
                .where(Game.season_id == season.id)
                .order_by(Game.game_date.desc())
            )
    elif team_id:
        stmt = (
            select(Game)
            .where(Game.season_id == season.id)
            .where((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
        )
        # Apply location filters for team queries directly in WHERE clause
        if home_only:
            stmt = stmt.where(Game.home_team_id == team_id)
        elif away_only:
            stmt = stmt.where(Game.away_team_id == team_id)
        if opponent_team_id:
            stmt = stmt.where(
                (Game.home_team_id == opponent_team_id)
                | (Game.away_team_id == opponent_team_id)
            )
        stmt = stmt.order_by(Game.game_date.desc())
    else:
        stmt = (
            select(Game)
            .where(Game.season_id == season.id)
            .order_by(Game.game_date.desc())
        )

    if last_n_games:
        stmt = stmt.limit(last_n_games)

    return list(db.scalars(stmt).all())


def _calc_stats_from_games(
    db: Session,
    games: list[Game],
    player_id=None,
    team_id=None,
    quarter: int | None = None,
    quarters: list[int] | None = None,
    clutch_only: bool = False,
    exclude_garbage_time: bool = False,
) -> dict:
    """
    Calculate stats from games, with optional time filters.

    When time filters are active, uses PBP events. Otherwise uses box scores.
    Returns dict with aggregated stats.
    """
    # Initialize accumulators
    totals = {
        "games": 0,
        "points": 0,
        "rebounds": 0,
        "assists": 0,
        "steals": 0,
        "blocks": 0,
        "turnovers": 0,
        "fgm": 0,
        "fga": 0,
        "fg3m": 0,
        "fg3a": 0,
        "ftm": 0,
        "fta": 0,
        "plus_minus": 0,
        "minutes": 0,
    }

    use_pbp = _has_time_filters(quarter, quarters, clutch_only, exclude_garbage_time)

    if use_pbp:
        analytics = AnalyticsService(db)

        for game in games:
            game_stats = _calc_pbp_stats_for_game(
                analytics,
                game,
                player_id=player_id,
                team_id=team_id,
                quarter=quarter,
                quarters=quarters,
                clutch_only=clutch_only,
                exclude_garbage_time=exclude_garbage_time,
            )
            if game_stats["has_data"]:
                totals["games"] += 1
                for key in totals:
                    if key != "games":
                        totals[key] += game_stats.get(key, 0)
    else:
        # Use box scores directly
        for game in games:
            if player_id:
                stmt = (
                    select(PlayerGameStats)
                    .where(PlayerGameStats.game_id == game.id)
                    .where(PlayerGameStats.player_id == player_id)
                )
                pgs = db.scalars(stmt).first()
                if pgs:
                    totals["games"] += 1
                    totals["points"] += pgs.points or 0
                    totals["rebounds"] += pgs.total_rebounds or 0
                    totals["assists"] += pgs.assists or 0
                    totals["steals"] += pgs.steals or 0
                    totals["blocks"] += pgs.blocks or 0
                    totals["turnovers"] += pgs.turnovers or 0
                    totals["fgm"] += pgs.field_goals_made or 0
                    totals["fga"] += pgs.field_goals_attempted or 0
                    totals["fg3m"] += pgs.three_pointers_made or 0
                    totals["fg3a"] += pgs.three_pointers_attempted or 0
                    totals["ftm"] += pgs.free_throws_made or 0
                    totals["fta"] += pgs.free_throws_attempted or 0
                    totals["plus_minus"] += pgs.plus_minus or 0
                    totals["minutes"] += (pgs.minutes_played or 0) // 60
            elif team_id:
                # Sum all players on team for this game
                stmt = (
                    select(PlayerGameStats)
                    .where(PlayerGameStats.game_id == game.id)
                    .where(PlayerGameStats.team_id == team_id)
                )
                all_pgs = list(db.scalars(stmt).all())
                if all_pgs:
                    totals["games"] += 1
                    for pgs in all_pgs:
                        totals["points"] += pgs.points or 0
                        totals["rebounds"] += pgs.total_rebounds or 0
                        totals["assists"] += pgs.assists or 0
                        totals["steals"] += pgs.steals or 0
                        totals["blocks"] += pgs.blocks or 0
                        totals["turnovers"] += pgs.turnovers or 0
                        totals["fgm"] += pgs.field_goals_made or 0
                        totals["fga"] += pgs.field_goals_attempted or 0
                        totals["fg3m"] += pgs.three_pointers_made or 0
                        totals["fg3a"] += pgs.three_pointers_attempted or 0
                        totals["ftm"] += pgs.free_throws_made or 0
                        totals["fta"] += pgs.free_throws_attempted or 0
                        totals["plus_minus"] += pgs.plus_minus or 0

    return totals


def _calc_pbp_stats_for_game(
    analytics: AnalyticsService,
    game: Game,
    player_id=None,
    team_id=None,
    quarter: int | None = None,
    quarters: list[int] | None = None,
    clutch_only: bool = False,
    exclude_garbage_time: bool = False,
) -> dict:
    """Calculate stats from PBP events for a single game with time filters."""
    stats = {
        "has_data": False,
        "points": 0,
        "rebounds": 0,
        "assists": 0,
        "steals": 0,
        "blocks": 0,
        "turnovers": 0,
        "fgm": 0,
        "fga": 0,
        "fg3m": 0,
        "fg3a": 0,
        "ftm": 0,
        "fta": 0,
        "plus_minus": 0,
        "minutes": 0,
    }

    # Get filtered events
    if clutch_only:
        events = analytics.get_clutch_events(game.id, ClutchFilter())
    else:
        # Build TimeFilter for quarter filtering
        time_filter = TimeFilter(
            period=quarter,
            periods=quarters,
            exclude_garbage_time=exclude_garbage_time,
        )
        events = analytics.get_events_by_time(game.id, time_filter)

    if not events:
        return stats

    # Filter events by player/team and accumulate stats
    for event in events:
        if player_id and event.player_id != player_id:
            continue
        if team_id and event.team_id != team_id:
            continue

        stats["has_data"] = True

        if event.event_type == "SHOT":
            stats["fga"] += 1
            is_3pt = event.event_subtype == "3PT"
            if is_3pt:
                stats["fg3a"] += 1
            if event.success:
                stats["fgm"] += 1
                stats["points"] += 3 if is_3pt else 2
                if is_3pt:
                    stats["fg3m"] += 1
        elif event.event_type == "FREE_THROW":
            stats["fta"] += 1
            if event.success:
                stats["ftm"] += 1
                stats["points"] += 1
        elif event.event_type == "REBOUND":
            stats["rebounds"] += 1
        elif event.event_type == "ASSIST":
            stats["assists"] += 1
        elif event.event_type == "STEAL":
            stats["steals"] += 1
        elif event.event_type == "BLOCK":
            stats["blocks"] += 1
        elif event.event_type == "TURNOVER":
            stats["turnovers"] += 1

    return stats


def _format_game_stats_value(totals: dict, metric: str, per: str) -> str:
    """Format a metric value from game-aggregated stats."""
    games = totals.get("games", 0)
    if games == 0:
        return "N/A"

    if metric == "games":
        return str(games)
    elif metric == "points":
        val = totals["points"]
    elif metric == "rebounds":
        val = totals["rebounds"]
    elif metric == "assists":
        val = totals["assists"]
    elif metric == "steals":
        val = totals["steals"]
    elif metric == "blocks":
        val = totals["blocks"]
    elif metric == "turnovers":
        val = totals["turnovers"]
    elif metric == "fg_pct":
        fga = totals["fga"]
        fgm = totals["fgm"]
        pct = fgm / fga if fga > 0 else 0
        return f"{pct * 100:.1f}%"
    elif metric == "three_pct":
        fg3a = totals["fg3a"]
        fg3m = totals["fg3m"]
        pct = fg3m / fg3a if fg3a > 0 else 0
        return f"{pct * 100:.1f}%"
    elif metric == "ft_pct":
        fta = totals["fta"]
        ftm = totals["ftm"]
        pct = ftm / fta if fta > 0 else 0
        return f"{pct * 100:.1f}%"
    elif metric == "plus_minus":
        val = totals["plus_minus"]
        if per == "total":
            return f"{int(val):+d}"
        else:
            avg = val / games
            return f"{avg:+.1f}"
    elif metric == "minutes":
        val = totals["minutes"]
    else:
        return "N/A"

    if per == "total":
        return str(int(val))
    else:
        avg = val / games
        return f"{avg:.1f}"


def _build_time_filter_label(
    quarter: int | None,
    quarters: list[int] | None,
    clutch_only: bool,
    exclude_garbage_time: bool,
    last_n_games: int | None,
    home_only: bool = False,
    away_only: bool = False,
    opponent_name: str | None = None,
) -> str:
    """Build a human-readable label for active time and location filters."""
    parts = []
    if quarter:
        parts.append(f"Q{quarter}")
    if quarters:
        if quarters == [1, 2]:
            parts.append("1st Half")
        elif quarters == [3, 4]:
            parts.append("2nd Half")
        else:
            parts.append(f"Q{','.join(str(q) for q in quarters)}")
    if clutch_only:
        parts.append("Clutch")
    if exclude_garbage_time:
        parts.append("No Garbage Time")
    if last_n_games:
        parts.append(f"Last {last_n_games} Games")
    if home_only:
        parts.append("Home")
    if away_only:
        parts.append("Away")
    if opponent_name:
        parts.append(f"vs {opponent_name}")
    return " | ".join(parts) if parts else ""


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
    # Time filters
    quarter: int | None = None,
    quarters: list[int] | None = None,
    clutch_only: bool = False,
    exclude_garbage_time: bool = False,
    last_n_games: int | None = None,
    # Location filters
    home_only: bool = False,
    away_only: bool = False,
    opponent_team: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Universal stats query tool for flexible basketball analytics.

    Use this tool for complex queries combining filters and metrics.
    Supports querying by league, season, team, or specific players.
    Time-based and location filters allow analysis of specific game situations.

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
        quarter: Single quarter to filter (1-4). Mutually exclusive with quarters.
        quarters: Multiple quarters (e.g., [1,2] for 1st half). Mutually exclusive
            with quarter.
        clutch_only: Only include clutch time (last 5 min Q4/OT, within 5 pts).
        exclude_garbage_time: Exclude when score differential > 20 points.
        last_n_games: Limit to most recent N games.
        home_only: Only include home games. Mutually exclusive with away_only.
        away_only: Only include away games. Mutually exclusive with home_only.
        opponent_team: Only include games against this team (by name).
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted stats table. Truncated if too large.

    Example queries:
        - "Get Maccabi's stats this season"
        - "Jimmy Clark's 4th quarter scoring" -> quarter=4
        - "First half shooting %" -> quarters=[1,2]
        - "Clutch performance" -> clutch_only=True
        - "Last 5 games trend" -> last_n_games=5
        - "Home vs away split" -> home_only=True / away_only=True
        - "Stats against Hapoel Jerusalem" -> opponent_team="Hapoel Jerusalem"
        - "Home clutch stats" -> home_only=True, clutch_only=True
    """
    if db is None:
        return "Error: Database session not provided."

    # Validate time filters
    validation_error = _validate_time_filters(quarter, quarters)
    if validation_error:
        return validation_error

    # Validate location filters
    location_error = _validate_location_filters(home_only, away_only)
    if location_error:
        return location_error

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

    # Resolve opponent team
    opponent = None
    if opponent_team:
        opponent = _resolve_team_by_name(db, opponent_team)
        if not opponent:
            return f"Opponent team '{opponent_team}' not found."

    # Resolve players
    players: list[Player] = []
    if player_names:
        for name in player_names:
            player = _resolve_player_by_name(db, name)
            if player:
                players.append(player)
            else:
                return f"Player '{name}' not found."

    # Check if time or location filters are active
    time_filters_active = (
        _has_time_filters(quarter, quarters, clutch_only, exclude_garbage_time)
        or last_n_games is not None
    )
    location_filters_active = _has_location_filters(
        home_only, away_only, opponent.id if opponent else None
    )

    # Execute query based on mode
    if time_filters_active or location_filters_active:
        return _query_with_time_filters(
            db=db,
            season=season_obj,
            players=players,
            team=team,
            metrics=metrics,
            per=per,
            limit=limit,
            quarter=quarter,
            quarters=quarters,
            clutch_only=clutch_only,
            exclude_garbage_time=exclude_garbage_time,
            last_n_games=last_n_games,
            home_only=home_only,
            away_only=away_only,
            opponent_team_id=opponent.id if opponent else None,
            opponent_name=opponent.name if opponent else None,
        )
    elif players:
        return _query_player_stats(db, players, season_obj, metrics, per, limit)
    elif team:
        return _query_team_stats(db, team, season_obj, metrics, per, limit)
    else:
        return _query_league_stats(db, league, season_obj, metrics, per, limit)


def _query_with_time_filters(
    db: Session,
    season: Season,
    players: list[Player],
    team: Team | None,
    metrics: list[str],
    per: str,
    limit: int,
    quarter: int | None,
    quarters: list[int] | None,
    clutch_only: bool,
    exclude_garbage_time: bool,
    last_n_games: int | None,
    home_only: bool = False,
    away_only: bool = False,
    opponent_team_id=None,
    opponent_name: str | None = None,
) -> str:
    """Query stats with time-based and location filters applied."""
    # Build filter label for header
    filter_label = _build_time_filter_label(
        quarter,
        quarters,
        clutch_only,
        exclude_garbage_time,
        last_n_games,
        home_only,
        away_only,
        opponent_name,
    )

    if players:
        # Query each player with time filters
        lines = [f"## Player Stats - {season.name}", f"*{filter_label}*", ""]

        header = "| Player | Team |"
        separator = "|--------|------|"
        for metric in metrics:
            header += f" {_format_metric_header(metric)} |"
            separator += "------|"
        lines.extend([header, separator])

        row_count = 0
        for player in players[:limit]:
            # Get games for this player
            games = _get_recent_games(
                db,
                season,
                player_id=player.id,
                last_n_games=last_n_games,
                home_only=home_only,
                away_only=away_only,
                opponent_team_id=opponent_team_id,
            )
            if not games:
                continue

            # Calculate stats with time filters
            totals = _calc_stats_from_games(
                db,
                games,
                player_id=player.id,
                quarter=quarter,
                quarters=quarters,
                clutch_only=clutch_only,
                exclude_garbage_time=exclude_garbage_time,
            )

            if totals["games"] == 0:
                continue

            # Get team name from most recent game
            team_name = "N/A"
            stmt = (
                select(PlayerGameStats)
                .where(PlayerGameStats.game_id == games[0].id)
                .where(PlayerGameStats.player_id == player.id)
            )
            pgs = db.scalars(stmt).first()
            if pgs and pgs.team:
                team_name = pgs.team.short_name

            player_name = f"{player.first_name} {player.last_name}"
            row = f"| {player_name} | {team_name} |"
            for metric in metrics:
                row += f" {_format_game_stats_value(totals, metric, per)} |"
            lines.append(row)
            row_count += 1

        if row_count == 0:
            return f"No stats found for the specified players with {filter_label}."

        return _truncate_response("\n".join(lines), row_count, len(players))

    elif team:
        # Query team players with time and location filters
        games = _get_recent_games(
            db,
            season,
            team_id=team.id,
            last_n_games=last_n_games,
            home_only=home_only,
            away_only=away_only,
            opponent_team_id=opponent_team_id,
        )
        if not games:
            filter_desc = filter_label if filter_label else "filters"
            return f"No games found for {team.name} with {filter_desc}."

        # Get all players who played for this team
        player_ids = set()
        for game in games:
            stmt = (
                select(PlayerGameStats.player_id)
                .where(PlayerGameStats.game_id == game.id)
                .where(PlayerGameStats.team_id == team.id)
            )
            for pid in db.scalars(stmt).all():
                player_ids.add(pid)

        lines = [f"## {team.name} - {season.name}", f"*{filter_label}*", ""]

        header = "| Player |"
        separator = "|--------|"
        for metric in metrics:
            header += f" {_format_metric_header(metric)} |"
            separator += "------|"
        lines.extend([header, separator])

        # Calculate stats for each player
        player_stats_list = []
        for player_id in player_ids:
            totals = _calc_stats_from_games(
                db,
                games,
                player_id=player_id,
                quarter=quarter,
                quarters=quarters,
                clutch_only=clutch_only,
                exclude_garbage_time=exclude_garbage_time,
            )
            if totals["games"] > 0:
                player = db.get(Player, player_id)
                if player:
                    player_stats_list.append((player, totals))

        # Sort by points (descending)
        player_stats_list.sort(
            key=lambda x: x[1]["points"] / max(x[1]["games"], 1), reverse=True
        )

        for player, totals in player_stats_list[:limit]:
            player_name = f"{player.first_name} {player.last_name}"
            row = f"| {player_name} |"
            for metric in metrics:
                row += f" {_format_game_stats_value(totals, metric, per)} |"
            lines.append(row)

        if len(player_stats_list) == 0:
            return f"No stats found for {team.name} with {filter_label}."

        return _truncate_response(
            "\n".join(lines), min(len(player_stats_list), limit), len(player_stats_list)
        )

    else:
        # League-wide query with filters is not supported (too expensive)
        return (
            "Error: Time filters (quarter, clutch, etc.) and location filters "
            "(home_only, away_only, opponent_team) require specifying a player or team. "
            "League-wide filtered queries are not supported."
        )
