"""
LangChain Chat Tools Module

Provides LangChain @tool wrappers around existing services for the chat agent.
Each tool calls existing service methods and formats output for LLM consumption.

This module exports LangChain tools that accept human-friendly parameters (names,
not UUIDs), resolve names to IDs internally, and return markdown-formatted strings
optimized for LLM understanding.

Usage:
    from src.services.chat_tools import search_players, get_player_stats

    # Tools are async and require a database session
    result = await search_players(query="Curry", session=db_session)
    print(result)  # Markdown formatted player list

The tools are designed to be used with LangChain agents for natural language
basketball analytics queries.
"""

from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from src.models.league import Season
from src.models.player import Player
from src.models.team import Team
from src.schemas.analytics import ClutchFilter
from src.schemas.player import PlayerFilter
from src.schemas.team import TeamFilter
from src.services.analytics import AnalyticsService
from src.services.game import GameService
from src.services.league import SeasonService
from src.services.player import PlayerService
from src.services.player_stats import PlayerSeasonStatsService
from src.services.stats import PlayerGameStatsService
from src.services.team import TeamService

# =============================================================================
# Helper Functions for Name Resolution
# =============================================================================


def _resolve_player_by_name(db: Session, name: str) -> Player | None:
    """
    Resolve a player name to a Player entity.

    Searches for players by first or last name using partial matching.
    Returns the best match (fewest total matches = more specific).

    Args:
        db: Database session.
        name: Player name to search for (partial match supported).

    Returns:
        Player entity if found, None otherwise.

    Example:
        >>> player = _resolve_player_by_name(db, "Curry")
        >>> if player:
        ...     print(player.full_name)  # "Stephen Curry"
    """
    service = PlayerService(db)
    players, _ = service.get_filtered(PlayerFilter(search=name), limit=10)
    if not players:
        return None
    # Return first match (best match based on search)
    return players[0]


def _resolve_team_by_name(db: Session, name: str) -> Team | None:
    """
    Resolve a team name to a Team entity.

    Searches for teams by name or short name using partial matching.

    Args:
        db: Database session.
        name: Team name to search for (partial match supported).

    Returns:
        Team entity if found, None otherwise.

    Example:
        >>> team = _resolve_team_by_name(db, "Lakers")
        >>> if team:
        ...     print(team.name)  # "Los Angeles Lakers"
    """
    service = TeamService(db)
    teams, _ = service.get_filtered(TeamFilter(search=name), limit=10)
    if not teams:
        return None
    return teams[0]


def _resolve_season(
    db: Session,
    season_name: str | None = None,
) -> Season | None:
    """
    Resolve a season by name or get current season.

    If season_name is provided, searches for it. Otherwise returns
    the current season.

    Args:
        db: Database session.
        season_name: Season name like "2023-24" or None for current.

    Returns:
        Season entity if found, None otherwise.

    Example:
        >>> season = _resolve_season(db, "2023-24")
        >>> current = _resolve_season(db)  # Gets current season
    """
    season_service = SeasonService(db)

    if season_name:
        # Search for season by name
        from sqlalchemy import select

        from src.models.league import League

        stmt = select(Season).join(League).where(Season.name.ilike(f"%{season_name}%"))
        season = db.scalars(stmt).first()
        return season

    # Get current season
    return season_service.get_current()


def _format_stat_line(
    points: int,
    rebounds: int,
    assists: int,
    steals: int = 0,
    blocks: int = 0,
    fg_pct: float | None = None,
) -> str:
    """Format a basic stat line as a string."""
    parts = [f"{points} PTS", f"{rebounds} REB", f"{assists} AST"]
    if steals > 0:
        parts.append(f"{steals} STL")
    if blocks > 0:
        parts.append(f"{blocks} BLK")
    if fg_pct is not None:
        parts.append(f"{fg_pct:.1%} FG")
    return " | ".join(parts)


# =============================================================================
# Basic Lookup Tools
# =============================================================================


@tool
def search_players(
    query: str,
    team_name: str | None = None,
    position: str | None = None,
    limit: int = 10,
    db: Session | None = None,
) -> str:
    """
    Search for basketball players by name.

    Use this tool when users ask about finding players or need to identify
    a player before getting their stats.

    Args:
        query: Player name to search for (partial match supported).
        team_name: Optional team filter (e.g., "Lakers", "Warriors").
        position: Optional position filter (PG, SG, SF, PF, C).
        limit: Max results to return (default 10).
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted list of matching players with their team and position.

    Example queries this tool handles:
        - "Find players named Curry"
        - "Who are the point guards on the Lakers?"
        - "Search for James"
    """
    if db is None:
        return "Error: Database session not provided."

    service = PlayerService(db)

    # Build filter
    filter_params = PlayerFilter(search=query, position=position)

    # Resolve team name to ID if provided
    if team_name:
        team = _resolve_team_by_name(db, team_name)
        if team:
            filter_params.team_id = team.id

    players, total = service.get_filtered(filter_params, limit=limit)

    if not players:
        return f"No players found matching '{query}'."

    # Format output
    lines = [f"## Players Matching '{query}'", "", f"Found {total} players:", ""]

    for player in players:
        # Get current team from history
        history = service.get_team_history(player.id)
        current_team = history[0].team.name if history else "Free Agent"
        position_str = player.position or "N/A"

        lines.append(f"- **{player.first_name} {player.last_name}**")
        lines.append(f"  - Position: {position_str}")
        lines.append(f"  - Team: {current_team}")
        lines.append("")

    return "\n".join(lines)


@tool
def search_teams(
    query: str,
    country: str | None = None,
    limit: int = 10,
    db: Session | None = None,
) -> str:
    """
    Search for basketball teams by name.

    Use this tool when users ask about finding teams or need to identify
    a team before getting their stats or roster.

    Args:
        query: Team name to search for (partial match supported).
        country: Optional country filter (e.g., "USA", "ISR").
        limit: Max results to return (default 10).
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted list of matching teams with city and country.

    Example queries this tool handles:
        - "Find teams in Israel"
        - "Search for Maccabi"
        - "Show me NBA teams"
    """
    if db is None:
        return "Error: Database session not provided."

    service = TeamService(db)
    filter_params = TeamFilter(search=query, country=country)

    teams, total = service.get_filtered(filter_params, limit=limit)

    if not teams:
        return f"No teams found matching '{query}'."

    lines = [f"## Teams Matching '{query}'", "", f"Found {total} teams:", ""]

    for team in teams:
        lines.append(f"- **{team.name}** ({team.short_name})")
        lines.append(f"  - City: {team.city or 'N/A'}")
        lines.append(f"  - Country: {team.country or 'N/A'}")
        lines.append("")

    return "\n".join(lines)


@tool
def get_team_roster(
    team_name: str,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get the roster for a basketball team.

    Use this tool when users ask about a team's players or want to see
    the full roster for a specific season.

    Args:
        team_name: Team name to get roster for (e.g., "Lakers", "Maccabi").
        season: Optional season (e.g., "2023-24"). Defaults to current season.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted roster with player names, positions, and jersey numbers.

    Example queries this tool handles:
        - "Show me the Lakers roster"
        - "Who plays for Maccabi Tel Aviv?"
        - "Get the Warriors roster for 2023-24"
    """
    if db is None:
        return "Error: Database session not provided."

    # Resolve team
    team = _resolve_team_by_name(db, team_name)
    if not team:
        return f"Team '{team_name}' not found."

    # Resolve season
    season_obj = _resolve_season(db, season)
    if not season_obj:
        return "No current season found."

    service = TeamService(db)
    roster = service.get_roster(team.id, season_obj.id)

    if not roster:
        return f"No roster found for {team.name} in {season_obj.name}."

    lines = [
        f"## {team.name} Roster",
        f"Season: {season_obj.name}",
        "",
        "| # | Player | Position |",
        "|---|--------|----------|",
    ]

    for entry in roster:
        jersey = entry.jersey_number or "-"
        player = entry.player
        name = f"{player.first_name} {player.last_name}"
        position = entry.position or player.position or "N/A"
        lines.append(f"| {jersey} | {name} | {position} |")

    lines.append("")
    lines.append(f"*Total: {len(roster)} players*")

    return "\n".join(lines)


@tool
def get_game_details(
    home_team: str | None = None,
    away_team: str | None = None,
    game_id: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get detailed box score for a specific game.

    Use this tool when users ask about a specific game's results, score,
    or player performances in that game.

    Args:
        home_team: Home team name (used with away_team to find recent game).
        away_team: Away team name (used with home_team to find recent game).
        game_id: Specific game ID if known.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted game summary with score, team stats, and top performers.

    Example queries this tool handles:
        - "What was the score of the Lakers vs Celtics game?"
        - "Show me last night's game details"
        - "Get the box score for Maccabi vs Hapoel"
    """
    if db is None:
        return "Error: Database session not provided."

    game_service = GameService(db)
    analytics = AnalyticsService(db)

    game = None

    # If game_id provided, use it directly
    if game_id:
        try:
            game = game_service.get_with_box_score(UUID(game_id))
        except ValueError:
            return f"Invalid game ID: {game_id}"
    elif home_team and away_team:
        # Find most recent game between these teams
        home = _resolve_team_by_name(db, home_team)
        away = _resolve_team_by_name(db, away_team)
        if not home or not away:
            return f"Could not find teams: {home_team}, {away_team}"

        games = analytics.get_games_vs_opponent(home.id, away.id)
        if games:
            game = game_service.get_with_box_score(games[0].id)
    else:
        return "Please provide either game_id or both home_team and away_team."

    if not game:
        return "Game not found."

    # Format output
    date_str = game.game_date.strftime("%Y-%m-%d") if game.game_date else "Unknown"
    home_name = game.home_team.name if game.home_team else "Home"
    away_name = game.away_team.name if game.away_team else "Away"

    lines = [
        f"## {away_name} @ {home_name}",
        f"Date: {date_str} | Status: {game.status}",
        "",
        "### Final Score",
        f"**{home_name}**: {game.home_score or 0}",
        f"**{away_name}**: {game.away_score or 0}",
        "",
    ]

    # Add top performers if player stats available
    if game.player_game_stats:
        lines.append("### Top Performers")

        # Group by team
        home_stats = [
            s for s in game.player_game_stats if s.team_id == game.home_team_id
        ]
        away_stats = [
            s for s in game.player_game_stats if s.team_id == game.away_team_id
        ]

        # Sort by points
        home_stats.sort(key=lambda x: x.points or 0, reverse=True)
        away_stats.sort(key=lambda x: x.points or 0, reverse=True)

        lines.append(f"\n**{home_name}**:")
        for stat in home_stats[:3]:
            name = f"{stat.player.first_name} {stat.player.last_name}"
            stat_line = _format_stat_line(
                stat.points or 0,
                stat.total_rebounds or 0,
                stat.assists or 0,
            )
            lines.append(f"- {name}: {stat_line}")

        lines.append(f"\n**{away_name}**:")
        for stat in away_stats[:3]:
            name = f"{stat.player.first_name} {stat.player.last_name}"
            stat_line = _format_stat_line(
                stat.points or 0,
                stat.total_rebounds or 0,
                stat.assists or 0,
            )
            lines.append(f"- {name}: {stat_line}")

    return "\n".join(lines)


# =============================================================================
# Stats Tools
# =============================================================================


@tool
def get_player_stats(
    player_name: str,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get player statistics for a specific season or career.

    Use this tool when users ask about a player's season averages, totals,
    or overall performance metrics.

    Args:
        player_name: Player name to get stats for (e.g., "LeBron", "Curry").
        season: Optional season (e.g., "2023-24"). Defaults to current season.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted stats including PPG, RPG, APG, shooting percentages.

    Example queries this tool handles:
        - "What are LeBron's stats this season?"
        - "Show me Stephen Curry's season averages"
        - "Get Deni Avdija's 2023-24 stats"
    """
    if db is None:
        return "Error: Database session not provided."

    # Resolve player
    player = _resolve_player_by_name(db, player_name)
    if not player:
        return f"Player '{player_name}' not found."

    # Resolve season
    season_obj = _resolve_season(db, season)
    if not season_obj:
        return "No current season found."

    service = PlayerSeasonStatsService(db)
    stats_list = service.get_player_season(player.id, season_obj.id)

    if not stats_list:
        return f"No stats found for {player.first_name} {player.last_name} in {season_obj.name}."

    # Aggregate if multiple teams (traded mid-season)
    total_games = sum(s.games_played for s in stats_list)
    main_team = stats_list[0].team.name if stats_list[0].team else "Unknown"

    # Use the first entry for averages (typically the most games)
    stats = stats_list[0]

    lines = [
        f"## {player.first_name} {player.last_name} - {season_obj.name}",
        f"Team: {main_team}",
        f"Games: {total_games}",
        "",
        "### Averages Per Game",
        "",
        "| Stat | Value |",
        "|------|-------|",
        f"| Points | {stats.avg_points or 0:.1f} |",
        f"| Rebounds | {stats.avg_rebounds or 0:.1f} |",
        f"| Assists | {stats.avg_assists or 0:.1f} |",
        f"| Steals | {stats.avg_steals or 0:.1f} |",
        f"| Blocks | {stats.avg_blocks or 0:.1f} |",
        "",
        "### Shooting",
        "",
        "| Category | Percentage |",
        "|----------|------------|",
        f"| FG% | {(stats.field_goal_pct or 0) * 100:.1f}% |",
        f"| 3P% | {(stats.three_point_pct or 0) * 100:.1f}% |",
        f"| FT% | {(stats.free_throw_pct or 0) * 100:.1f}% |",
        f"| TS% | {(stats.true_shooting_pct or 0) * 100:.1f}% |",
    ]

    if len(stats_list) > 1:
        lines.append("")
        lines.append(f"*Note: Player was on {len(stats_list)} teams this season.*")

    return "\n".join(lines)


@tool
def get_player_games(
    player_name: str,
    limit: int = 5,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get a player's recent game log.

    Use this tool when users ask about a player's recent performances,
    game-by-game stats, or how they've been playing lately.

    Args:
        player_name: Player name (e.g., "Curry", "LeBron").
        limit: Number of recent games to show (default 5).
        season: Optional season filter (e.g., "2023-24").
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted game log with date, opponent, and stats per game.

    Example queries this tool handles:
        - "Show me Curry's last 5 games"
        - "How did LeBron play recently?"
        - "Get Deni's game log"
    """
    if db is None:
        return "Error: Database session not provided."

    # Resolve player
    player = _resolve_player_by_name(db, player_name)
    if not player:
        return f"Player '{player_name}' not found."

    # Resolve season if provided
    season_id = None
    if season:
        season_obj = _resolve_season(db, season)
        if season_obj:
            season_id = season_obj.id

    service = PlayerGameStatsService(db)
    game_log, total = service.get_player_game_log(
        player.id, season_id=season_id, limit=limit
    )

    if not game_log:
        return f"No games found for {player.first_name} {player.last_name}."

    lines = [
        f"## {player.first_name} {player.last_name} - Last {len(game_log)} Games",
        "",
        "| Date | Opponent | PTS | REB | AST | FG% |",
        "|------|----------|-----|-----|-----|-----|",
    ]

    for stat in game_log:
        game = stat.game
        date_str = game.game_date.strftime("%m/%d") if game.game_date else "?"

        # Determine opponent
        is_home = stat.team_id == game.home_team_id
        opp = game.away_team if is_home else game.home_team
        opp_name = opp.short_name if opp else "???"
        prefix = "vs" if is_home else "@"

        # Calculate FG%
        fga = stat.field_goals_attempted or 0
        fgm = stat.field_goals_made or 0
        fg_pct = (fgm / fga * 100) if fga > 0 else 0

        lines.append(
            f"| {date_str} | {prefix} {opp_name} | "
            f"{stat.points or 0} | {stat.total_rebounds or 0} | "
            f"{stat.assists or 0} | {fg_pct:.0f}% |"
        )

    lines.append("")
    lines.append(f"*Showing {len(game_log)} of {total} games*")

    return "\n".join(lines)


@tool
def get_league_leaders(
    category: str,
    limit: int = 10,
    season: str | None = None,
    min_games: int = 5,
    db: Session | None = None,
) -> str:
    """
    Get league leaders for a statistical category.

    Use this tool when users ask about who leads the league in a stat,
    or rankings for specific categories.

    Args:
        category: Stat category. Options: "points", "rebounds", "assists",
            "steals", "blocks", "field_goal_pct", "three_point_pct".
        limit: Number of leaders to show (default 10).
        season: Optional season (e.g., "2023-24"). Defaults to current.
        min_games: Minimum games played to qualify (default 5).
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted leaderboard with rankings and stats.

    Example queries this tool handles:
        - "Who leads the league in assists?"
        - "Top 10 scorers this season"
        - "Show me the 3-point percentage leaders"
    """
    if db is None:
        return "Error: Database session not provided."

    # Resolve season
    season_obj = _resolve_season(db, season)
    if not season_obj:
        return "No current season found."

    # Normalize category name
    category_display = {
        "points": "Points Per Game",
        "avg_points": "Points Per Game",
        "rebounds": "Rebounds Per Game",
        "avg_rebounds": "Rebounds Per Game",
        "assists": "Assists Per Game",
        "avg_assists": "Assists Per Game",
        "steals": "Steals Per Game",
        "avg_steals": "Steals Per Game",
        "blocks": "Blocks Per Game",
        "avg_blocks": "Blocks Per Game",
        "field_goal_pct": "Field Goal %",
        "three_point_pct": "3-Point %",
        "free_throw_pct": "Free Throw %",
    }

    display_name = category_display.get(category, category.replace("_", " ").title())

    service = PlayerSeasonStatsService(db)

    try:
        leaders = service.get_league_leaders(
            season_obj.id, category=category, limit=limit, min_games=min_games
        )
    except ValueError as e:
        return f"Error: {e}"

    if not leaders:
        return f"No leaders found for {display_name}."

    # Determine which attribute to display
    attr_map = {
        "points": "avg_points",
        "avg_points": "avg_points",
        "rebounds": "avg_rebounds",
        "avg_rebounds": "avg_rebounds",
        "assists": "avg_assists",
        "avg_assists": "avg_assists",
        "steals": "avg_steals",
        "avg_steals": "avg_steals",
        "blocks": "avg_blocks",
        "avg_blocks": "avg_blocks",
        "field_goal_pct": "field_goal_pct",
        "three_point_pct": "three_point_pct",
        "free_throw_pct": "free_throw_pct",
    }
    attr = attr_map.get(category, category)
    is_pct = "pct" in attr

    lines = [
        f"## {display_name} Leaders - {season_obj.name}",
        f"*Minimum {min_games} games played*",
        "",
        "| Rank | Player | Team | Value |",
        "|------|--------|------|-------|",
    ]

    for i, stats in enumerate(leaders, 1):
        player = stats.player
        name = f"{player.first_name} {player.last_name}"
        team = stats.team.short_name if stats.team else "N/A"
        value = getattr(stats, attr, 0) or 0
        value_str = f"{value * 100:.1f}%" if is_pct else f"{value:.1f}"

        lines.append(f"| {i} | {name} | {team} | {value_str} |")

    return "\n".join(lines)


# =============================================================================
# Advanced Analytics Tools
# =============================================================================


@tool
def get_clutch_stats(
    team_name: str | None = None,
    player_name: str | None = None,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get performance statistics in clutch situations across a season.

    Clutch is defined as the final 5 minutes of 4th quarter or OT,
    with the score within 5 points.

    Use this tool when users ask about:
        - Clutch performance or late-game situations
        - "Why are we bad at clutch?"
        - Close game performance

    Args:
        team_name: Team to analyze (e.g., "Lakers", "Maccabi").
        player_name: Specific player (optional).
        season: Season (e.g., "2023-24"). Defaults to current.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted clutch stats including win/loss record,
        shooting percentages (clutch vs overall), points and turnovers.

    Example queries this tool handles:
        - "How do we perform in clutch situations?"
        - "Show me LeBron's clutch stats"
        - "Why are we bad in close games?"
    """
    if db is None:
        return "Error: Database session not provided."

    # Need either team or player
    if not team_name and not player_name:
        return "Please provide either team_name or player_name."

    # Resolve entities
    team_id = None
    player_id = None
    entity_name = ""

    if team_name:
        team = _resolve_team_by_name(db, team_name)
        if not team:
            return f"Team '{team_name}' not found."
        team_id = team.id
        entity_name = team.name

    if player_name:
        player = _resolve_player_by_name(db, player_name)
        if not player:
            return f"Player '{player_name}' not found."
        player_id = player.id
        entity_name = f"{player.first_name} {player.last_name}"

    # Resolve season
    season_obj = _resolve_season(db, season)
    if not season_obj:
        return "No current season found."

    analytics = AnalyticsService(db)
    clutch_filter = ClutchFilter()  # Use defaults

    stats = analytics.get_clutch_stats_for_season(
        season_id=season_obj.id,
        team_id=team_id,
        player_id=player_id,
        clutch_filter=clutch_filter,
    )

    lines = [
        f"## Clutch Performance: {entity_name}",
        f"Season: {season_obj.name}",
        "*Clutch = Last 5 min of Q4/OT, score within 5 points*",
        "",
        "### Overview",
        f"- Games with clutch situations: {stats.games_in_clutch}",
    ]

    if team_id:
        lines.append(f"- Record in clutch games: {stats.wins}-{stats.losses}")

    lines.extend(
        [
            "",
            "### Shooting Comparison",
            "",
            "| Category | Clutch | Overall | Diff |",
            "|----------|--------|---------|------|",
        ]
    )

    fg_diff = (stats.fg_pct_clutch - stats.fg_pct_overall) * 100
    lines.append(
        f"| FG% | {stats.fg_pct_clutch * 100:.1f}% | "
        f"{stats.fg_pct_overall * 100:.1f}% | {fg_diff:+.1f}% |"
    )

    three_diff = (stats.three_pct_clutch - stats.three_pct_overall) * 100
    lines.append(
        f"| 3P% | {stats.three_pct_clutch * 100:.1f}% | "
        f"{stats.three_pct_overall * 100:.1f}% | {three_diff:+.1f}% |"
    )

    ft_diff = (stats.ft_pct_clutch - stats.ft_pct_overall) * 100
    lines.append(
        f"| FT% | {stats.ft_pct_clutch * 100:.1f}% | "
        f"{stats.ft_pct_overall * 100:.1f}% | {ft_diff:+.1f}% |"
    )

    lines.extend(
        [
            "",
            "### Clutch Per-Game Averages",
            f"- Points: {stats.points_per_clutch_game:.1f}",
            f"- Turnovers: {stats.turnovers_per_clutch_game:.1f}",
        ]
    )

    return "\n".join(lines)


@tool
def get_quarter_splits(
    team_name: str | None = None,
    player_name: str | None = None,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get performance breakdown by quarter (Q1, Q2, Q3, Q4, OT).

    Use this tool when users ask about:
        - Performance in specific quarters
        - "How do we perform in the 4th quarter?"
        - Quarter-by-quarter analysis

    Args:
        team_name: Team to analyze.
        player_name: Specific player (optional).
        season: Season (e.g., "2023-24"). Defaults to current.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted quarter-by-quarter stats including points,
        FG%, and plus/minus per quarter.

    Example queries this tool handles:
        - "How do we perform in the 4th quarter?"
        - "Show me quarter splits for the Lakers"
        - "Which quarter is our weakest?"
    """
    if db is None:
        return "Error: Database session not provided."

    if not team_name and not player_name:
        return "Please provide either team_name or player_name."

    # Resolve entities
    team_id = None
    player_id = None
    entity_name = ""

    if team_name:
        team = _resolve_team_by_name(db, team_name)
        if not team:
            return f"Team '{team_name}' not found."
        team_id = team.id
        entity_name = team.name

    if player_name:
        player = _resolve_player_by_name(db, player_name)
        if not player:
            return f"Player '{player_name}' not found."
        player_id = player.id
        entity_name = f"{player.first_name} {player.last_name}"

    # Resolve season
    season_obj = _resolve_season(db, season)
    if not season_obj:
        return "No current season found."

    analytics = AnalyticsService(db)
    splits = analytics.get_quarter_splits_for_season(
        season_id=season_obj.id,
        team_id=team_id,
        player_id=player_id,
    )

    if not splits:
        return f"No quarter splits found for {entity_name}."

    lines = [
        f"## Quarter Splits: {entity_name}",
        f"Season: {season_obj.name}",
        "",
    ]

    if team_id:
        lines.extend(
            [
                "| Quarter | Points | Allowed | +/- | FG% |",
                "|---------|--------|---------|-----|-----|",
            ]
        )
        for q in ["Q1", "Q2", "Q3", "Q4", "OT"]:
            if q not in splits:
                continue
            s = splits[q]
            allowed = s.points_allowed if s.points_allowed is not None else "-"
            pm = f"{s.plus_minus:+.1f}" if s.plus_minus is not None else "-"
            lines.append(
                f"| {q} | {s.points:.1f} | {allowed} | {pm} | {s.fg_pct * 100:.1f}% |"
            )
    else:
        lines.extend(
            [
                "| Quarter | Points | FG% |",
                "|---------|--------|-----|",
            ]
        )
        for q in ["Q1", "Q2", "Q3", "Q4", "OT"]:
            if q not in splits:
                continue
            s = splits[q]
            lines.append(f"| {q} | {s.points:.1f} | {s.fg_pct * 100:.1f}% |")

    # Add analysis
    lines.append("")
    quarters = [q for q in ["Q1", "Q2", "Q3", "Q4"] if q in splits]
    if quarters:
        best_q = max(quarters, key=lambda q: splits[q].points)
        worst_q = min(quarters, key=lambda q: splits[q].points)
        lines.append(
            f"**Strongest quarter:** {best_q} ({splits[best_q].points:.1f} PPG)"
        )
        lines.append(
            f"**Weakest quarter:** {worst_q} ({splits[worst_q].points:.1f} PPG)"
        )

    return "\n".join(lines)


@tool
def get_trend(
    stat: str,
    player_name: str | None = None,
    team_name: str | None = None,
    last_n_games: int = 10,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Analyze performance trend over recent games.

    Use this tool when users ask about:
        - How has a player/team been playing lately
        - Recent form or trends
        - Improvement or decline

    Args:
        stat: Statistic to track. Options: "points", "rebounds", "assists",
            "steals", "blocks", "fg_pct", "three_pct".
        player_name: Player to analyze.
        team_name: Team to analyze (alternative to player).
        last_n_games: Number of recent games (default 10).
        season: Optional season filter.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted trend analysis showing direction, recent average
        vs season average, and game-by-game values.

    Example queries this tool handles:
        - "How has LeBron been playing lately?"
        - "Is Curry's shooting improving?"
        - "Show me the team's scoring trend"
    """
    if db is None:
        return "Error: Database session not provided."

    if not player_name and not team_name:
        return "Please provide either player_name or team_name."

    # Resolve entities
    player_id = None
    team_id = None
    entity_name = ""

    if player_name:
        player = _resolve_player_by_name(db, player_name)
        if not player:
            return f"Player '{player_name}' not found."
        player_id = player.id
        entity_name = f"{player.first_name} {player.last_name}"

    if team_name:
        team = _resolve_team_by_name(db, team_name)
        if not team:
            return f"Team '{team_name}' not found."
        team_id = team.id
        entity_name = team.name

    # Resolve season
    season_id = None
    if season:
        season_obj = _resolve_season(db, season)
        if season_obj:
            season_id = season_obj.id

    analytics = AnalyticsService(db)

    try:
        trend = analytics.get_performance_trend(
            stat=stat,
            last_n_games=last_n_games,
            player_id=player_id,
            team_id=team_id,
            season_id=season_id,
        )
    except ValueError as e:
        return f"Error: {e}"

    # Format stat name
    stat_display = stat.replace("_", " ").title()
    if "pct" in stat.lower():
        stat_display = stat_display.replace("Pct", "%")

    # Direction emoji
    direction_emoji = {
        "improving": "📈",
        "declining": "📉",
        "stable": "➡️",
    }
    emoji = direction_emoji.get(trend.direction, "")

    lines = [
        f"## {stat_display} Trend: {entity_name}",
        f"*Last {len(trend.values)} games*",
        "",
        f"### Direction: {emoji} {trend.direction.title()}",
        "",
        f"- **Recent Average:** {trend.average:.1f}",
        f"- **Season Average:** {trend.season_average:.1f}",
        f"- **Change:** {trend.change_pct:+.1f}%",
        "",
        "### Recent Games",
        "",
    ]

    # Show game-by-game
    is_pct_stat = "pct" in stat.lower()
    for game, value in zip(trend.games, trend.values, strict=True):
        value_str = f"{value * 100:.1f}%" if is_pct_stat else f"{value:.1f}"
        lines.append(f"- {game}: {value_str}")

    return "\n".join(lines)


@tool
def get_lineup_stats(
    player_names: list[str],
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get statistics when specific players are on court together.

    Use this tool when users ask about:
        - How a specific lineup performs
        - Two or more players together
        - "Which lineup is most effective?"

    Args:
        player_names: List of player names (2-5 players).
        season: Optional season (e.g., "2023-24"). Defaults to current.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted lineup stats including plus/minus, minutes,
        and points scored/allowed when lineup is on court together.

    Example queries this tool handles:
        - "How do LeBron and AD play together?"
        - "What's the plus/minus for our starting five?"
        - "Show me stats when Curry and Thompson are both in"
    """
    if db is None:
        return "Error: Database session not provided."

    if len(player_names) < 2:
        return "Please provide at least 2 player names."

    if len(player_names) > 5:
        return "Maximum 5 players allowed for lineup analysis."

    # Resolve all players
    player_ids = []
    resolved_names = []
    for name in player_names:
        player = _resolve_player_by_name(db, name)
        if not player:
            return f"Player '{name}' not found."
        player_ids.append(player.id)
        resolved_names.append(f"{player.first_name} {player.last_name}")

    # Resolve season
    season_obj = _resolve_season(db, season)
    if not season_obj:
        return "No current season found."

    analytics = AnalyticsService(db)
    stats = analytics.get_lineup_stats_for_season(player_ids, season_obj.id)

    lineup_str = " + ".join(resolved_names)

    lines = [
        "## Lineup Stats",
        f"**Players:** {lineup_str}",
        f"Season: {season_obj.name}",
        "",
        "### Performance Together",
        "",
        f"- **Games Played Together:** {stats['games']}",
        f"- **Minutes Together:** {stats['minutes']:.1f}",
        f"- **Plus/Minus:** {stats['plus_minus']:+d}",
        "",
        "### Scoring",
        f"- Team Points: {stats['team_pts']}",
        f"- Opponent Points: {stats['opp_pts']}",
    ]

    if stats["minutes"] > 0:
        pts_per_min = stats["team_pts"] / stats["minutes"]
        lines.append(f"- Points/Minute: {pts_per_min:.2f}")

    return "\n".join(lines)


@tool
def get_home_away_split(
    player_name: str,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get player's home vs away performance comparison.

    Use this tool when users ask about:
        - Home/away performance differences
        - Home court advantage
        - "How does he play at home vs away?"

    Args:
        player_name: Player name to analyze.
        season: Optional season (e.g., "2023-24"). Defaults to current.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted comparison of home vs away stats including
        points, rebounds, assists per game for each.

    Example queries this tool handles:
        - "How does Curry play at home vs away?"
        - "Compare LeBron's home and road stats"
        - "Is there a home court advantage for Deni?"
    """
    if db is None:
        return "Error: Database session not provided."

    # Resolve player
    player = _resolve_player_by_name(db, player_name)
    if not player:
        return f"Player '{player_name}' not found."

    # Resolve season
    season_obj = _resolve_season(db, season)
    if not season_obj:
        return "No current season found."

    analytics = AnalyticsService(db)
    split = analytics.get_player_home_away_split(player.id, season_obj.id)

    name = f"{player.first_name} {player.last_name}"
    home = split["home"]
    away = split["away"]

    lines = [
        f"## Home/Away Split: {name}",
        f"Season: {season_obj.name}",
        "",
        "| Stat | Home | Away | Diff |",
        "|------|------|------|------|",
    ]

    # Games
    lines.append(f"| Games | {home['games']} | {away['games']} | - |")

    # Points
    diff_pts = home["avg_points"] - away["avg_points"]
    lines.append(
        f"| PPG | {home['avg_points']:.1f} | {away['avg_points']:.1f} | "
        f"{diff_pts:+.1f} |"
    )

    # Rebounds
    diff_reb = home["avg_rebounds"] - away["avg_rebounds"]
    lines.append(
        f"| RPG | {home['avg_rebounds']:.1f} | {away['avg_rebounds']:.1f} | "
        f"{diff_reb:+.1f} |"
    )

    # Assists
    diff_ast = home["avg_assists"] - away["avg_assists"]
    lines.append(
        f"| APG | {home['avg_assists']:.1f} | {away['avg_assists']:.1f} | "
        f"{diff_ast:+.1f} |"
    )

    # Add analysis
    lines.append("")
    if diff_pts > 1:
        lines.append(f"📈 {name} performs better at **home** (+{diff_pts:.1f} PPG)")
    elif diff_pts < -1:
        lines.append(f"📈 {name} performs better on the **road** ({diff_pts:.1f} PPG)")
    else:
        lines.append(f"➡️ {name} performs **consistently** regardless of location")

    return "\n".join(lines)


@tool
def get_on_off_stats(
    player_name: str,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get team's plus/minus with player on vs off the court.

    Use this tool when users ask about:
        - A player's impact on the team
        - On/off court statistics
        - "What's our plus/minus with LeBron on court?"

    Args:
        player_name: Player name to analyze.
        season: Optional season (e.g., "2023-24"). Defaults to current.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted on/off comparison showing team performance
        with the player on court vs off court.

    Example queries this tool handles:
        - "What's our plus/minus with LeBron on court?"
        - "How does the team do without Curry?"
        - "Show me Deni's on/off impact"
    """
    if db is None:
        return "Error: Database session not provided."

    # Resolve player
    player = _resolve_player_by_name(db, player_name)
    if not player:
        return f"Player '{player_name}' not found."

    # Resolve season
    season_obj = _resolve_season(db, season)
    if not season_obj:
        return "No current season found."

    analytics = AnalyticsService(db)
    stats = analytics.get_player_on_off_for_season(player.id, season_obj.id)

    name = f"{player.first_name} {player.last_name}"
    on = stats["on"]
    off = stats["off"]

    lines = [
        f"## On/Off Stats: {name}",
        f"Season: {season_obj.name}",
        "",
        "| Metric | On Court | Off Court | Net |",
        "|--------|----------|-----------|-----|",
    ]

    # Minutes
    lines.append(f"| Minutes | {on['minutes']:.1f} | {off['minutes']:.1f} | - |")

    # Team Points
    lines.append(f"| Team Points | {on['team_pts']} | {off['team_pts']} | - |")

    # Opp Points
    lines.append(f"| Opp Points | {on['opp_pts']} | {off['opp_pts']} | - |")

    # Plus/Minus
    net = on["plus_minus"] - off["plus_minus"]
    lines.append(
        f"| +/- | {on['plus_minus']:+d} | {off['plus_minus']:+d} | " f"**{net:+d}** |"
    )

    # Games
    lines.append(f"| Games | {on['games']} | {off['games']} | - |")

    # Add analysis
    lines.append("")
    if net > 5:
        lines.append(f"📈 Team performs **significantly better** with {name} on court")
    elif net > 0:
        lines.append(f"📈 Team performs **slightly better** with {name} on court")
    elif net < -5:
        lines.append(f"📉 Team performs **better** with {name} off court")
    else:
        lines.append(f"➡️ {name}'s on/off impact is **neutral**")

    return "\n".join(lines)


@tool
def get_vs_opponent(
    player_name: str,
    opponent_team: str,
    season: str | None = None,
    db: Session | None = None,
) -> str:
    """
    Get player's statistics against a specific opponent.

    Use this tool when users ask about:
        - How a player performs against a specific team
        - Head-to-head matchup stats
        - "How does Curry play against the Lakers?"

    Args:
        player_name: Player name to analyze.
        opponent_team: Opponent team name (e.g., "Lakers", "Celtics").
        season: Optional season filter. If None, uses all available data.
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted stats showing player's performance in games
        against the specified opponent.

    Example queries this tool handles:
        - "How does Curry play against the Lakers?"
        - "Show me LeBron's stats vs Boston"
        - "Deni's numbers against Maccabi"
    """
    if db is None:
        return "Error: Database session not provided."

    # Resolve player
    player = _resolve_player_by_name(db, player_name)
    if not player:
        return f"Player '{player_name}' not found."

    # Resolve opponent
    opponent = _resolve_team_by_name(db, opponent_team)
    if not opponent:
        return f"Team '{opponent_team}' not found."

    # Resolve season if provided
    season_id = None
    season_str = "All Time"
    if season:
        season_obj = _resolve_season(db, season)
        if season_obj:
            season_id = season_obj.id
            season_str = season_obj.name

    analytics = AnalyticsService(db)
    games = analytics.get_player_stats_vs_opponent(
        player_id=player.id,
        opponent_id=opponent.id,
        season_id=season_id,
    )

    if not games:
        name = f"{player.first_name} {player.last_name}"
        return f"No games found for {name} against {opponent.name}."

    # Calculate averages
    total_games = len(games)
    total_pts = sum(g.points or 0 for g in games)
    total_reb = sum(g.total_rebounds or 0 for g in games)
    total_ast = sum(g.assists or 0 for g in games)
    total_stl = sum(g.steals or 0 for g in games)
    total_blk = sum(g.blocks or 0 for g in games)

    avg_pts = total_pts / total_games
    avg_reb = total_reb / total_games
    avg_ast = total_ast / total_games
    avg_stl = total_stl / total_games
    avg_blk = total_blk / total_games

    name = f"{player.first_name} {player.last_name}"

    lines = [
        f"## {name} vs {opponent.name}",
        f"Period: {season_str}",
        f"Games: {total_games}",
        "",
        "### Averages",
        "",
        "| Stat | Average |",
        "|------|---------|",
        f"| Points | {avg_pts:.1f} |",
        f"| Rebounds | {avg_reb:.1f} |",
        f"| Assists | {avg_ast:.1f} |",
        f"| Steals | {avg_stl:.1f} |",
        f"| Blocks | {avg_blk:.1f} |",
        "",
        "### Recent Games",
        "",
    ]

    # Show recent games (up to 5)
    for game_stat in games[:5]:
        game = game_stat.game
        date_str = game.game_date.strftime("%m/%d/%Y") if game.game_date else "?"
        stat_line = _format_stat_line(
            game_stat.points or 0,
            game_stat.total_rebounds or 0,
            game_stat.assists or 0,
        )
        lines.append(f"- {date_str}: {stat_line}")

    return "\n".join(lines)


# =============================================================================
# Tool Registry
# =============================================================================

# List of all available tools for easy import
ALL_TOOLS = [
    # Basic Lookup
    search_players,
    search_teams,
    get_team_roster,
    get_game_details,
    # Stats
    get_player_stats,
    get_player_games,
    get_league_leaders,
    # Advanced Analytics
    get_clutch_stats,
    get_quarter_splits,
    get_trend,
    get_lineup_stats,
    get_home_away_split,
    get_on_off_stats,
    get_vs_opponent,
]
