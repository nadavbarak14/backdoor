"""
Leagues Router Module

FastAPI router for league-related endpoints.
Provides endpoints for listing leagues, retrieving league details,
and accessing seasons within a league.

Endpoints:
    GET /leagues - List all leagues with season counts
    GET /leagues/{league_id} - Get a specific league
    GET /leagues/{league_id}/seasons - List seasons for a league

Usage:
    from src.api.v1.leagues import router

    app.include_router(router, prefix="/api/v1")
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core import get_db
from src.schemas import LeagueListResponse, LeagueResponse, SeasonResponse
from src.services import LeagueService, SeasonService

router = APIRouter(prefix="/leagues", tags=["Leagues"])


@router.get(
    "",
    response_model=LeagueListResponse,
    summary="List Leagues",
    description="Retrieve a paginated list of all leagues with their season counts.",
)
def list_leagues(
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of records to return",
    ),
    db: Session = Depends(get_db),
) -> LeagueListResponse:
    """
    List all leagues with their season counts.

    Args:
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
        db: Database session (injected).

    Returns:
        LeagueListResponse containing list of leagues and total count.

    Example:
        >>> response = client.get("/api/v1/leagues?skip=0&limit=10")
        >>> data = response.json()
        >>> print(data["total"])
        5
    """
    service = LeagueService(db)
    leagues_with_counts = service.get_all_with_season_counts(skip=skip, limit=limit)
    total = service.count()

    items = [
        LeagueResponse(
            id=league.id,
            name=league.name,
            code=league.code,
            country=league.country,
            season_count=count,
            created_at=league.created_at,
            updated_at=league.updated_at,
        )
        for league, count in leagues_with_counts
    ]

    return LeagueListResponse(items=items, total=total)


@router.get(
    "/{league_id}",
    response_model=LeagueResponse,
    summary="Get League",
    description="Retrieve a specific league by its ID.",
    responses={
        404: {"description": "League not found"},
    },
)
def get_league(
    league_id: UUID,
    db: Session = Depends(get_db),
) -> LeagueResponse:
    """
    Get a specific league by ID.

    Args:
        league_id: UUID of the league to retrieve.
        db: Database session (injected).

    Returns:
        LeagueResponse with league details and season count.

    Raises:
        HTTPException: 404 if league not found.

    Example:
        >>> response = client.get(f"/api/v1/leagues/{league_id}")
        >>> data = response.json()
        >>> print(data["name"])
        "NBA"
    """
    service = LeagueService(db)
    league, season_count = service.get_with_season_count(league_id)

    if league is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League with id {league_id} not found",
        )

    return LeagueResponse(
        id=league.id,
        name=league.name,
        code=league.code,
        country=league.country,
        season_count=season_count,
        created_at=league.created_at,
        updated_at=league.updated_at,
    )


@router.get(
    "/{league_id}/seasons",
    response_model=list[SeasonResponse],
    summary="List League Seasons",
    description="Retrieve all seasons for a specific league.",
    responses={
        404: {"description": "League not found"},
    },
)
def list_league_seasons(
    league_id: UUID,
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of records to return",
    ),
    db: Session = Depends(get_db),
) -> list[SeasonResponse]:
    """
    List all seasons for a specific league.

    Args:
        league_id: UUID of the league.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
        db: Database session (injected).

    Returns:
        List of SeasonResponse objects.

    Raises:
        HTTPException: 404 if league not found.

    Example:
        >>> response = client.get(f"/api/v1/leagues/{league_id}/seasons")
        >>> seasons = response.json()
        >>> print(seasons[0]["name"])
        "2023-24"
    """
    league_service = LeagueService(db)
    league = league_service.get_by_id(league_id)

    if league is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League with id {league_id} not found",
        )

    season_service = SeasonService(db)
    seasons = season_service.get_by_league(league_id, skip=skip, limit=limit)

    return [SeasonResponse.model_validate(season) for season in seasons]
