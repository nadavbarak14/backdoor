"""
Search Tools Module

Provides search tools for finding basketball entities (players, teams, leagues,
seasons) by name. These tools return structured data with IDs that can be used
with the query_stats tool.

Usage:
    from src.services.search_tools import search_players, search_teams

    # Search for players
    result = search_players.invoke({"query": "Clark", "db": db_session})

    # Search for teams
    result = search_teams.invoke({"query": "Maccabi", "db": db_session})
"""

from langchain_core.tools import tool
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.models.league import League, Season
from src.schemas.player import PlayerFilter
from src.schemas.team import TeamFilter
from src.services.player import PlayerService
from src.services.team import TeamService

# =============================================================================
# Player Search
# =============================================================================


@tool
def search_players(
    query: str,
    team_id: str | None = None,
    position: str | None = None,
    limit: int = 10,
    db: Session | None = None,
) -> str:
    """
    Search for basketball players by name.

    Use this tool to find player IDs before using query_stats.
    Supports partial name matching and fuzzy search.

    Args:
        query: Player name to search for (partial match supported).
        team_id: Optional team UUID to filter by current team.
        position: Optional position filter (PG, SG, SF, PF, C).
        limit: Maximum results to return (default 10).
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted list of matching players with their IDs.
        Use the ID values with query_stats tool.

    Example:
        User: "Find players named Clark"
        -> Returns list with IDs to use in query_stats(player_ids=[...])
    """
    if db is None:
        return "Error: Database session not provided."

    if not query or len(query.strip()) < 2:
        return "Error: Search query must be at least 2 characters."

    service = PlayerService(db)

    # Build filter
    filter_params = PlayerFilter(search=query.strip(), position=position)
    if team_id:
        try:
            from uuid import UUID

            filter_params.team_id = UUID(team_id)
        except ValueError:
            return f"Error: Invalid team_id format: {team_id}"

    players, total = service.get_filtered(filter_params, limit=limit)

    if not players:
        return f"No players found matching '{query}'."

    # Format output with IDs
    lines = [
        f"## Players Matching '{query}'",
        f"Found {total} player(s). Showing top {len(players)}:",
        "",
        "| ID | Name | Team | Position |",
        "|----|------|------|----------|",
    ]

    for player in players:
        name = f"{player.first_name} {player.last_name}"
        team_name = "N/A"
        if player.current_team:
            team_name = player.current_team.short_name or player.current_team.name
        position = player.position or "N/A"

        lines.append(f"| `{player.id}` | {name} | {team_name} | {position} |")

    lines.append("")
    lines.append("*Use the ID values with `query_stats(player_ids=[...])`*")

    return "\n".join(lines)


# =============================================================================
# Team Search
# =============================================================================


@tool
def search_teams(
    query: str,
    country: str | None = None,
    limit: int = 10,
    db: Session | None = None,
) -> str:
    """
    Search for basketball teams by name.

    Use this tool to find team IDs before using query_stats.
    Supports partial name matching.

    Args:
        query: Team name to search for (partial match supported).
        country: Optional country filter (e.g., "ISR", "USA").
        limit: Maximum results to return (default 10).
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted list of matching teams with their IDs.
        Use the ID values with query_stats tool.

    Example:
        User: "Find teams named Maccabi"
        -> Returns list with IDs to use in query_stats(team_id=...)
    """
    if db is None:
        return "Error: Database session not provided."

    if not query or len(query.strip()) < 2:
        return "Error: Search query must be at least 2 characters."

    service = TeamService(db)
    filter_params = TeamFilter(search=query.strip(), country=country)

    teams, total = service.get_filtered(filter_params, limit=limit)

    if not teams:
        return f"No teams found matching '{query}'."

    # Format output with IDs
    lines = [
        f"## Teams Matching '{query}'",
        f"Found {total} team(s). Showing top {len(teams)}:",
        "",
        "| ID | Name | Short | City | Country |",
        "|----|------|-------|------|---------|",
    ]

    for team in teams:
        short_name = team.short_name or "N/A"
        city = team.city or "N/A"
        country = team.country or "N/A"

        lines.append(
            f"| `{team.id}` | {team.name} | {short_name} | {city} | {country} |"
        )

    lines.append("")
    lines.append("*Use the ID value with `query_stats(team_id=...)`*")

    return "\n".join(lines)


# =============================================================================
# League Search
# =============================================================================


@tool
def search_leagues(
    query: str | None = None,
    limit: int = 10,
    db: Session | None = None,
) -> str:
    """
    Search for basketball leagues/competitions.

    Use this tool to find league IDs before using query_stats.
    If no query provided, lists all available leagues.

    Args:
        query: Optional league name to search for (partial match).
            If not provided, lists all leagues.
        limit: Maximum results to return (default 10).
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted list of leagues with their IDs.
        Use the ID values with query_stats tool.

    Example:
        User: "What leagues are available?"
        -> Returns list with IDs to use in query_stats(league_id=...)
    """
    if db is None:
        return "Error: Database session not provided."

    # Build query
    stmt = select(League)
    if query and query.strip():
        search_term = query.strip()
        stmt = stmt.where(
            or_(
                League.name.ilike(f"%{search_term}%"),
                League.code.ilike(f"%{search_term}%"),
            )
        )
    stmt = stmt.order_by(League.name).limit(limit)

    leagues = list(db.scalars(stmt).all())

    if not leagues:
        if query:
            return f"No leagues found matching '{query}'."
        return "No leagues found in the database."

    # Format output with IDs
    title = f"## Leagues Matching '{query}'" if query else "## Available Leagues"
    lines = [
        title,
        "",
        "| ID | Name | Code |",
        "|----|------|------|",
    ]

    for league in leagues:
        code = league.code or "N/A"
        lines.append(f"| `{league.id}` | {league.name} | {code} |")

    lines.append("")
    lines.append("*Use the ID value with `query_stats(league_id=...)`*")

    return "\n".join(lines)


# =============================================================================
# Season Search
# =============================================================================


@tool
def search_seasons(
    league_id: str | None = None,
    query: str | None = None,
    limit: int = 10,
    db: Session | None = None,
) -> str:
    """
    Search for basketball seasons.

    Use this tool to find season IDs before using query_stats.
    Can filter by league and search by season name (e.g., "2024-25").

    Args:
        league_id: Optional league UUID to filter seasons.
        query: Optional season name to search (e.g., "2024", "2024-25").
        limit: Maximum results to return (default 10).
        db: Database session (injected at runtime).

    Returns:
        Markdown-formatted list of seasons with their IDs.
        Use the ID values with query_stats tool.

    Example:
        User: "What seasons are available for the Israeli league?"
        -> Returns list with IDs to use in query_stats(season_id=...)
    """
    if db is None:
        return "Error: Database session not provided."

    from uuid import UUID

    # Build query
    stmt = select(Season).join(League)

    if league_id:
        try:
            league_uuid = UUID(league_id)
            stmt = stmt.where(Season.league_id == league_uuid)
        except ValueError:
            return f"Error: Invalid league_id format: {league_id}"

    if query and query.strip():
        stmt = stmt.where(Season.name.ilike(f"%{query.strip()}%"))

    stmt = stmt.order_by(Season.start_date.desc()).limit(limit)

    seasons = list(db.scalars(stmt).all())

    if not seasons:
        if query:
            return f"No seasons found matching '{query}'."
        return "No seasons found."

    # Format output with IDs
    title = f"## Seasons Matching '{query}'" if query else "## Available Seasons"
    lines = [
        title,
        "",
        "| ID | Name | League | Current |",
        "|----|------|--------|---------|",
    ]

    for season in seasons:
        league_name = season.league.name if season.league else "N/A"
        is_current = "Yes" if season.is_current else "No"
        lines.append(
            f"| `{season.id}` | {season.name} | {league_name} | {is_current} |"
        )

    lines.append("")
    lines.append("*Use the ID value with `query_stats(season_id=...)`*")
    lines.append(
        "*Note: If season_id is not specified, query_stats uses the current season.*"
    )

    return "\n".join(lines)


# =============================================================================
# Tool List for Export
# =============================================================================

SEARCH_TOOLS = [
    search_players,
    search_teams,
    search_leagues,
    search_seasons,
]
