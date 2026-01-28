"""
Browse API Endpoints Module

Provides hierarchical browse endpoints for the @-mention feature.
Enables navigation through League -> Season -> Team -> Player hierarchy.

Endpoints:
    GET /browse/leagues - List all leagues (root level)
    GET /browse/leagues/{league_id}/seasons - List seasons in a league
    GET /browse/seasons/{season_id}/teams - List teams in a season
    GET /browse/teams/{team_id}/players - List players on a team

Usage:
    # Start at root
    GET /api/v1/browse/leagues

    # Navigate to seasons
    GET /api/v1/browse/leagues/{league_id}/seasons

    # Navigate to teams
    GET /api/v1/browse/seasons/{season_id}/teams

    # Navigate to players
    GET /api/v1/browse/teams/{team_id}/players
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.schemas.search import BrowseResponse
from src.services.search_service import SearchService

router = APIRouter(prefix="/browse", tags=["browse"])


@router.get(
    "/leagues",
    response_model=BrowseResponse,
    summary="List all leagues",
    description="Get all leagues for the root level of the browse hierarchy.",
    responses={
        200: {
            "description": "List of leagues",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "type": "league",
                                "name": "Israeli Basketball League",
                                "has_children": True,
                            }
                        ],
                        "parent": None,
                    }
                }
            },
        }
    },
)
def browse_leagues(db: Session = Depends(get_db)) -> BrowseResponse:
    """
    List all leagues (root browse level).

    Args:
        db: Database session (injected)

    Returns:
        BrowseResponse with all leagues, no parent (root level)

    Example:
        >>> # GET /api/v1/browse/leagues
        >>> response.items[0].name
        "Israeli Basketball League"
    """
    service = SearchService(db)
    return service.browse_leagues()


@router.get(
    "/leagues/{league_id}/seasons",
    response_model=BrowseResponse,
    summary="List seasons in a league",
    description="Get all seasons for a specific league.",
    responses={
        200: {
            "description": "List of seasons with league as parent",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440001",
                                "type": "season",
                                "name": "2024-25",
                                "has_children": True,
                            }
                        ],
                        "parent": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "type": "league",
                            "name": "Israeli Basketball League",
                        },
                    }
                }
            },
        },
        404: {"description": "League not found"},
    },
)
def browse_seasons(
    league_id: UUID,
    db: Session = Depends(get_db),
) -> BrowseResponse:
    """
    List seasons in a specific league.

    Args:
        league_id: UUID of the league
        db: Database session (injected)

    Returns:
        BrowseResponse with seasons and league as parent

    Raises:
        HTTPException 404: If league_id doesn't exist

    Example:
        >>> # GET /api/v1/browse/leagues/{id}/seasons
        >>> response.items[0].name
        "2024-25"
        >>> response.parent.name
        "Israeli Basketball League"
    """
    service = SearchService(db)
    try:
        return service.browse_seasons(league_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/seasons/{season_id}/teams",
    response_model=BrowseResponse,
    summary="List teams in a season",
    description="Get all teams participating in a specific season.",
    responses={
        200: {
            "description": "List of teams with season as parent",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440002",
                                "type": "team",
                                "name": "Maccabi Tel Aviv",
                                "has_children": True,
                            }
                        ],
                        "parent": {
                            "id": "550e8400-e29b-41d4-a716-446655440001",
                            "type": "season",
                            "name": "2024-25",
                        },
                    }
                }
            },
        },
        404: {"description": "Season not found"},
    },
)
def browse_teams(
    season_id: UUID,
    db: Session = Depends(get_db),
) -> BrowseResponse:
    """
    List teams in a specific season.

    Args:
        season_id: UUID of the season
        db: Database session (injected)

    Returns:
        BrowseResponse with teams and season as parent

    Raises:
        HTTPException 404: If season_id doesn't exist

    Example:
        >>> # GET /api/v1/browse/seasons/{id}/teams
        >>> response.items[0].name
        "Maccabi Tel Aviv"
        >>> response.parent.name
        "2024-25"
    """
    service = SearchService(db)
    try:
        return service.browse_teams(season_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/teams/{team_id}/players",
    response_model=BrowseResponse,
    summary="List players on a team",
    description="Get all players on a specific team, optionally filtered by season.",
    responses={
        200: {
            "description": "List of players with team as parent",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440003",
                                "type": "player",
                                "name": "Jaylen Hoard",
                                "has_children": False,
                            }
                        ],
                        "parent": {
                            "id": "550e8400-e29b-41d4-a716-446655440002",
                            "type": "team",
                            "name": "Maccabi Tel Aviv",
                        },
                    }
                }
            },
        },
        404: {"description": "Team not found"},
    },
)
def browse_players(
    team_id: UUID,
    season_id: UUID | None = Query(
        None,
        description="Optional season ID to filter roster",
    ),
    db: Session = Depends(get_db),
) -> BrowseResponse:
    """
    List players on a specific team.

    Args:
        team_id: UUID of the team
        season_id: Optional season to filter roster
        db: Database session (injected)

    Returns:
        BrowseResponse with players and team as parent

    Raises:
        HTTPException 404: If team_id doesn't exist

    Example:
        >>> # GET /api/v1/browse/teams/{id}/players
        >>> response.items[0].name
        "Jaylen Hoard"
        >>> response.items[0].has_children
        False  # Players are leaf nodes
    """
    service = SearchService(db)
    try:
        return service.browse_players(team_id, season_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
