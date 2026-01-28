"""
Search Tools Module

Provides search tools for finding basketball entities (players, teams, leagues,
seasons) by name. These tools return JSON-formatted data with IDs that can be
used with the query_stats tool.

Usage:
    from src.services.search_tools import search_players, search_teams

    # Search for players
    result = search_players.invoke({"query": "Clark", "db": db_session})

    # Search for teams
    result = search_teams.invoke({"query": "Maccabi", "db": db_session})
"""

import json

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
        JSON object with total count and list of matching players.
        Each player includes id, name, team, and position.

    Example:
        User: "Find players named Clark"
        -> Returns JSON with IDs to use in query_stats(player_ids=[...])
    """
    if db is None:
        return json.dumps({"error": "Database session not provided."})

    if not query or len(query.strip()) < 2:
        return json.dumps({"error": "Search query must be at least 2 characters."})

    service = PlayerService(db)

    # Build filter
    filter_params = PlayerFilter(search=query.strip(), position=position)
    if team_id:
        try:
            from uuid import UUID

            filter_params.team_id = UUID(team_id)
        except ValueError:
            return json.dumps({"error": f"Invalid team_id format: {team_id}"})

    players, total = service.get_filtered(filter_params, limit=limit)

    if not players:
        return json.dumps({"total": 0, "players": []})

    # Build JSON response
    player_list = []
    for player in players:
        name = f"{player.first_name} {player.last_name}"
        team_name = None
        if player.current_team:
            team_name = player.current_team.short_name or player.current_team.name

        player_list.append(
            {
                "id": str(player.id),
                "name": name,
                "team": team_name,
                "position": player.position or None,
            }
        )

    result = {
        "total": total,
        "players": player_list,
    }

    return json.dumps(result)


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
        JSON object with total count and list of matching teams.
        Each team includes id, name, short_name, city, and country.

    Example:
        User: "Find teams named Maccabi"
        -> Returns JSON with IDs to use in query_stats(team_id=...)
    """
    if db is None:
        return json.dumps({"error": "Database session not provided."})

    if not query or len(query.strip()) < 2:
        return json.dumps({"error": "Search query must be at least 2 characters."})

    service = TeamService(db)
    filter_params = TeamFilter(search=query.strip(), country=country)

    teams, total = service.get_filtered(filter_params, limit=limit)

    if not teams:
        return json.dumps({"total": 0, "teams": []})

    # Build JSON response
    team_list = []
    for team in teams:
        team_list.append(
            {
                "id": str(team.id),
                "name": team.name,
                "short_name": team.short_name or None,
                "city": team.city or None,
                "country": team.country or None,
            }
        )

    result = {
        "total": total,
        "teams": team_list,
    }

    return json.dumps(result)


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
        JSON object with list of leagues.
        Each league includes id, name, and code.

    Example:
        User: "What leagues are available?"
        -> Returns JSON with IDs to use in query_stats(league_id=...)
    """
    if db is None:
        return json.dumps({"error": "Database session not provided."})

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
        return json.dumps({"leagues": []})

    # Build JSON response
    league_list = []
    for league in leagues:
        league_list.append(
            {
                "id": str(league.id),
                "name": league.name,
                "code": league.code or None,
            }
        )

    result = {
        "leagues": league_list,
    }

    return json.dumps(result)


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
        JSON object with list of seasons.
        Each season includes id, name, league, and is_current flag.

    Example:
        User: "What seasons are available for the Israeli league?"
        -> Returns JSON with IDs to use in query_stats(season_id=...)
    """
    if db is None:
        return json.dumps({"error": "Database session not provided."})

    from uuid import UUID

    # Build query
    stmt = select(Season).join(League)

    if league_id:
        try:
            league_uuid = UUID(league_id)
            stmt = stmt.where(Season.league_id == league_uuid)
        except ValueError:
            return json.dumps({"error": f"Invalid league_id format: {league_id}"})

    if query and query.strip():
        stmt = stmt.where(Season.name.ilike(f"%{query.strip()}%"))

    stmt = stmt.order_by(Season.start_date.desc()).limit(limit)

    seasons = list(db.scalars(stmt).all())

    if not seasons:
        return json.dumps({"seasons": []})

    # Build JSON response
    season_list = []
    for season in seasons:
        league_name = season.league.name if season.league else None
        season_list.append(
            {
                "id": str(season.id),
                "name": season.name,
                "league": league_name,
                "is_current": season.is_current,
            }
        )

    result = {
        "seasons": season_list,
    }

    return json.dumps(result)


# =============================================================================
# Tool List for Export
# =============================================================================

SEARCH_TOOLS = [
    search_players,
    search_teams,
    search_leagues,
    search_seasons,
]
