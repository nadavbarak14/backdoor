"""
LangChain Chat Tools Module

Provides LangChain @tool wrappers for the chat agent.

This module exports 4 LangChain tools:
- search_players: Search for players by name (returns JSON with IDs)
- search_teams: Search for teams by name (returns JSON with IDs)
- search_leagues: Search for leagues by name (imported from search_tools)
- query_stats: Universal stats query tool (imported from query_stats)

The search tools resolve human-friendly names to entity IDs, which are then
used with query_stats for all statistical queries.

Usage:
    from src.services.chat_tools import ALL_TOOLS

    # Tools are sync and require a database session
    result = search_players.invoke({"query": "Curry", "db": db_session})
    print(result)  # JSON formatted player list with IDs

The tools are designed to be used with LangChain agents for natural language
basketball analytics queries.
"""

import json
import logging

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from src.models.team import Team
from src.schemas.player import PlayerFilter
from src.schemas.team import TeamFilter
from src.services.player import PlayerService
from src.services.query_stats import query_stats
from src.services.search_tools import search_leagues
from src.services.team import TeamService

# Response size limits to prevent context blowup
MAX_ROWS = 30  # Hard limit for any tool response

logger = logging.getLogger(__name__)


def _log_response(tool_name: str, response: str) -> str:
    """Log tool response size for debugging token usage."""
    char_count = len(response)
    line_count = response.count("\n") + 1
    # Rough token estimate: ~4 chars per token
    token_estimate = char_count // 4
    logger.info(
        f"[TOOL_RESPONSE] {tool_name}: {char_count} chars, "
        f"{line_count} lines, ~{token_estimate} tokens"
    )
    return response


# =============================================================================
# Helper Functions for Name Resolution
# =============================================================================


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


# =============================================================================
# Search Tools
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
        JSON object with total count and list of matching players.
        Each player includes id, name, position, and team.

    Example queries this tool handles:
        - "Find players named Curry"
        - "Who are the point guards on the Lakers?"
        - "Search for James"
    """
    if db is None:
        return json.dumps({"error": "Database session not provided."})

    service = PlayerService(db)

    # Build filter
    filter_params = PlayerFilter(search=query, position=position)

    # Resolve team name to ID if provided
    if team_name:
        team = _resolve_team_by_name(db, team_name)
        if team:
            filter_params.team_id = team.id

    # Enforce hard limit
    limit = min(limit, MAX_ROWS)
    players, total = service.get_filtered(filter_params, limit=limit)

    if not players:
        return json.dumps({"total": 0, "players": []})

    # Build JSON response
    player_list = []
    for player in players:
        # Get current team from history
        history = service.get_team_history(player.id)
        current_team = history[0].team.name if history else "Free Agent"

        player_list.append(
            {
                "id": str(player.id),
                "name": f"{player.first_name} {player.last_name}",
                "position": player.position or None,
                "team": current_team,
            }
        )

    result = {
        "total": total,
        "players": player_list,
    }

    return _log_response("search_players", json.dumps(result))


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
        JSON object with total count and list of matching teams.
        Each team includes id, name, short_name, city, and country.

    Example queries this tool handles:
        - "Find teams in Israel"
        - "Search for Maccabi"
        - "Show me NBA teams"
    """
    if db is None:
        return json.dumps({"error": "Database session not provided."})

    service = TeamService(db)
    filter_params = TeamFilter(search=query, country=country)

    # Enforce hard limit
    limit = min(limit, MAX_ROWS)
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

    return _log_response("search_teams", json.dumps(result))


# =============================================================================
# Tool Registry
# =============================================================================

# List of all available tools for easy import
# Simplified to essential tools only - query_stats handles all analytics
ALL_TOOLS = [
    # Search Tools (use these first to find entity IDs)
    search_players,
    search_teams,
    search_leagues,
    # Universal Query Tool (handles ALL stats queries)
    query_stats,
]
