"""
Players Router Module

FastAPI router for player-related endpoints.
Provides endpoints for searching players and retrieving player details
with team history.

Endpoints:
    GET /players - Search players with filters
    GET /players/{player_id} - Get player with team history

Usage:
    from src.api.v1.players import router

    app.include_router(router, prefix="/api/v1")
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core import get_db
from src.schemas import (
    PlayerFilter,
    PlayerListResponse,
    PlayerResponse,
    PlayerTeamHistoryResponse,
    PlayerWithHistoryResponse,
)
from src.services import PlayerService

router = APIRouter(prefix="/players", tags=["Players"])


@router.get(
    "",
    response_model=PlayerListResponse,
    summary="List Players",
    description="Search and filter players with pagination.",
)
def list_players(
    team_id: UUID | None = Query(
        default=None,
        description="Filter by current team ID",
    ),
    season_id: UUID | None = Query(
        default=None,
        description="Filter by season ID",
    ),
    position: str | None = Query(
        default=None,
        description="Filter by position (e.g., PG, SG, SF, PF, C)",
    ),
    nationality: str | None = Query(
        default=None,
        description="Filter by nationality",
    ),
    search: str | None = Query(
        default=None,
        description="Search by player name",
    ),
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
) -> PlayerListResponse:
    """
    Search and list players with optional filtering.

    Args:
        team_id: Filter players by team.
        season_id: Filter players by season participation.
        position: Filter players by position.
        nationality: Filter players by nationality.
        search: Search players by name (partial match).
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
        db: Database session (injected).

    Returns:
        PlayerListResponse containing list of players and total count.

    Example:
        >>> response = client.get("/api/v1/players?position=PG&search=curry")
        >>> data = response.json()
        >>> print(data["items"][0]["full_name"])
        "Stephen Curry"
    """
    service = PlayerService(db)
    filter_params = PlayerFilter(
        team_id=team_id,
        season_id=season_id,
        position=position,
        nationality=nationality,
        search=search,
    )

    players, total = service.get_filtered(filter_params, skip=skip, limit=limit)

    return PlayerListResponse(
        items=[PlayerResponse.model_validate(player) for player in players],
        total=total,
    )


@router.get(
    "/{player_id}",
    response_model=PlayerWithHistoryResponse,
    summary="Get Player",
    description="Retrieve a specific player by ID including their complete team history.",
    responses={
        404: {"description": "Player not found"},
    },
)
def get_player(
    player_id: UUID,
    db: Session = Depends(get_db),
) -> PlayerWithHistoryResponse:
    """
    Get a specific player by ID with their team history.

    Args:
        player_id: UUID of the player to retrieve.
        db: Database session (injected).

    Returns:
        PlayerWithHistoryResponse with player details and team history.

    Raises:
        HTTPException: 404 if player not found.

    Example:
        >>> response = client.get(f"/api/v1/players/{player_id}")
        >>> data = response.json()
        >>> print(data["full_name"])
        "LeBron James"
        >>> print(len(data["team_history"]))
        4
    """
    service = PlayerService(db)
    player = service.get_with_history(player_id)

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with id {player_id} not found",
        )

    team_history = [
        PlayerTeamHistoryResponse(
            team_id=pth.team_id,
            team_name=pth.team.name,
            season_id=pth.season_id,
            season_name=pth.season.name,
            jersey_number=pth.jersey_number,
            position=pth.position,
        )
        for pth in player.team_histories
    ]

    return PlayerWithHistoryResponse(
        id=player.id,
        first_name=player.first_name,
        last_name=player.last_name,
        full_name=player.full_name,
        birth_date=player.birth_date,
        nationality=player.nationality,
        height_cm=player.height_cm,
        position=player.position,
        external_ids=player.external_ids or {},
        created_at=player.created_at,
        updated_at=player.updated_at,
        team_history=team_history,
    )
