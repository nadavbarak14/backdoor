"""
Teams Router Module

FastAPI router for team-related endpoints.
Provides endpoints for listing teams, retrieving team details,
accessing team rosters, and viewing team game history.

Endpoints:
    GET /teams - List teams with optional filters
    GET /teams/{team_id} - Get a specific team
    GET /teams/{team_id}/roster - Get team roster for a season
    GET /teams/{team_id}/games - Get team game history

Usage:
    from src.api.v1.teams import router

    app.include_router(router, prefix="/api/v1")
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core import get_db
from src.schemas import (
    TeamFilter,
    TeamGameHistoryResponse,
    TeamGameSummaryResponse,
    TeamListResponse,
    TeamResponse,
    TeamRosterPlayerResponse,
    TeamRosterResponse,
)
from src.services import SeasonService, TeamGameStatsService, TeamService

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get(
    "",
    response_model=TeamListResponse,
    summary="List Teams",
    description="Retrieve a paginated list of teams with optional filters.",
)
def list_teams(
    league_id: UUID | None = Query(
        default=None,
        description="Filter by league ID",
    ),
    season_id: UUID | None = Query(
        default=None,
        description="Filter by season ID",
    ),
    country: str | None = Query(
        default=None,
        description="Filter by country",
    ),
    search: str | None = Query(
        default=None,
        description="Search by team name",
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
) -> TeamListResponse:
    """
    List teams with optional filtering.

    Args:
        league_id: Filter teams by league.
        season_id: Filter teams by season participation.
        country: Filter teams by country.
        search: Search teams by name (partial match).
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
        db: Database session (injected).

    Returns:
        TeamListResponse containing list of teams and total count.

    Example:
        >>> response = client.get("/api/v1/teams?country=USA&limit=10")
        >>> data = response.json()
        >>> print(data["total"])
        30
    """
    service = TeamService(db)
    filter_params = TeamFilter(
        league_id=league_id,
        season_id=season_id,
        country=country,
        search=search,
    )

    teams, total = service.get_filtered(filter_params, skip=skip, limit=limit)

    return TeamListResponse(
        items=[TeamResponse.model_validate(team) for team in teams],
        total=total,
    )


@router.get(
    "/{team_id}",
    response_model=TeamResponse,
    summary="Get Team",
    description="Retrieve a specific team by its ID.",
    responses={
        404: {"description": "Team not found"},
    },
)
def get_team(
    team_id: UUID,
    db: Session = Depends(get_db),
) -> TeamResponse:
    """
    Get a specific team by ID.

    Args:
        team_id: UUID of the team to retrieve.
        db: Database session (injected).

    Returns:
        TeamResponse with team details.

    Raises:
        HTTPException: 404 if team not found.

    Example:
        >>> response = client.get(f"/api/v1/teams/{team_id}")
        >>> data = response.json()
        >>> print(data["name"])
        "Los Angeles Lakers"
    """
    service = TeamService(db)
    team = service.get_by_id(team_id)

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with id {team_id} not found",
        )

    return TeamResponse.model_validate(team)


@router.get(
    "/{team_id}/roster",
    response_model=TeamRosterResponse,
    summary="Get Team Roster",
    description="Retrieve the roster of a team for a specific season. "
    "If no season is specified, defaults to the current season.",
    responses={
        404: {"description": "Team or season not found"},
    },
)
def get_team_roster(
    team_id: UUID,
    season_id: UUID | None = Query(
        default=None,
        description="Season ID. If not provided, uses the current season.",
    ),
    db: Session = Depends(get_db),
) -> TeamRosterResponse:
    """
    Get the roster for a team in a specific season.

    Args:
        team_id: UUID of the team.
        season_id: Optional UUID of the season. Defaults to current season.
        db: Database session (injected).

    Returns:
        TeamRosterResponse with team info, season info, and player list.

    Raises:
        HTTPException: 404 if team not found or no current season exists.

    Example:
        >>> response = client.get(f"/api/v1/teams/{team_id}/roster")
        >>> data = response.json()
        >>> print(len(data["players"]))
        15
    """
    team_service = TeamService(db)
    team = team_service.get_by_id(team_id)

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with id {team_id} not found",
        )

    # If no season specified, find the most recent season the team participated in
    if season_id is None:
        season_service = SeasonService(db)
        # Get seasons this team has participated in (via TeamSeason)
        team_seasons = team_service.get_team_seasons(team_id)
        current_season = None
        if team_seasons:
            # Use the most recent season (last in list or find current)
            for ts in team_seasons:
                season = season_service.get_by_id(ts.season_id)
                if season and season.is_current:
                    current_season = season
                    break
            # Fall back to the most recent season
            if current_season is None:
                current_season = season_service.get_by_id(team_seasons[-1].season_id)

        if current_season is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No season found for this team. Please specify a season_id.",
            )
        season_id = current_season.id
        season_name = current_season.name
    else:
        season_service = SeasonService(db)
        season = season_service.get_by_id(season_id)
        if season is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Season with id {season_id} not found",
            )
        season_name = season.name

    roster = team_service.get_roster(team_id, season_id)

    players = [
        TeamRosterPlayerResponse(
            id=pth.player.id,
            first_name=pth.player.first_name,
            last_name=pth.player.last_name,
            full_name=pth.player.full_name,
            jersey_number=pth.jersey_number,
            # Use PlayerTeamHistory.positions if set, otherwise fall back to Player.positions
            positions=[p.value for p in (pth.positions or pth.player.positions)],
        )
        for pth in roster
    ]

    return TeamRosterResponse(
        team=TeamResponse.model_validate(team),
        season_id=season_id,
        season_name=season_name,
        players=players,
    )


@router.get(
    "/{team_id}/games",
    response_model=TeamGameHistoryResponse,
    summary="Get Team Game History",
    description="Retrieve a team's game history with results.",
    responses={
        404: {"description": "Team not found"},
    },
)
def get_team_games(
    team_id: UUID,
    season_id: UUID | None = Query(
        default=None,
        description="Filter by season ID",
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of records to return",
    ),
    db: Session = Depends(get_db),
) -> TeamGameHistoryResponse:
    """
    Get a team's game history with results.

    Args:
        team_id: UUID of the team.
        season_id: Optional filter by season.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
        db: Database session (injected).

    Returns:
        TeamGameHistoryResponse with list of game summaries.

    Raises:
        HTTPException: 404 if team not found.

    Example:
        >>> response = client.get(f"/api/v1/teams/{team_id}/games")
        >>> data = response.json()
        >>> for game in data["items"]:
        ...     print(f"{game['result']} vs {game['opponent_team_name']}")
    """
    team_service = TeamService(db)
    team = team_service.get_by_id(team_id)

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with id {team_id} not found",
        )

    stats_service = TeamGameStatsService(db)
    game_history, total = stats_service.get_team_game_history(
        team_id=team_id,
        season_id=season_id,
        skip=skip,
        limit=limit,
    )

    items = []
    for stat in game_history:
        game = stat.game
        # Determine opponent
        is_home = stat.is_home
        if is_home:
            opponent_team_id = game.away_team_id
            opponent_team_name = game.away_team.name
            team_score = game.home_score or 0
            opponent_score = game.away_score or 0
        else:
            opponent_team_id = game.home_team_id
            opponent_team_name = game.home_team.name
            team_score = game.away_score or 0
            opponent_score = game.home_score or 0

        items.append(
            TeamGameSummaryResponse(
                game_id=game.id,
                game_date=game.game_date,
                opponent_team_id=opponent_team_id,
                opponent_team_name=opponent_team_name,
                is_home=is_home,
                team_score=team_score,
                opponent_score=opponent_score,
                venue=game.venue,
            )
        )

    return TeamGameHistoryResponse(items=items, total=total)
