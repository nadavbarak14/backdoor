"""
Games Router Module

FastAPI router for game-related endpoints.
Provides endpoints for listing games, retrieving game details with box scores,
and accessing play-by-play data.

Endpoints:
    GET /games - List games with optional filters
    GET /games/{game_id} - Get game with box score
    GET /games/{game_id}/pbp - Get play-by-play events

Usage:
    from src.api.v1.games import router

    app.include_router(router, prefix="/api/v1")
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core import get_db
from src.models.game import PlayerGameStats, TeamGameStats
from src.schemas import (
    GameFilter,
    GameListResponse,
    GameResponse,
    GameStatus,
    GameWithBoxScoreResponse,
    PlayByPlayEventResponse,
    PlayByPlayFilter,
    PlayByPlayResponse,
    PlayerBoxScoreResponse,
    TeamBoxScoreResponse,
)
from src.services import GameService, PlayByPlayService

router = APIRouter(prefix="/games", tags=["Games"])


def _compute_percentage(made: int, attempted: int) -> float:
    """
    Compute shooting percentage.

    Args:
        made: Number of shots made.
        attempted: Number of shots attempted.

    Returns:
        Percentage as float (0.0 if no attempts).

    Example:
        >>> _compute_percentage(7, 14)
        50.0
    """
    if attempted == 0:
        return 0.0
    return round((made / attempted) * 100, 1)


def _format_minutes(seconds: int) -> str:
    """
    Format seconds into MM:SS display string.

    Args:
        seconds: Playing time in seconds.

    Returns:
        Formatted string like "25:30".

    Example:
        >>> _format_minutes(1800)
        '30:00'
    """
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def _build_team_box_score(team_stats: TeamGameStats) -> TeamBoxScoreResponse:
    """
    Build TeamBoxScoreResponse from TeamGameStats model.

    Args:
        team_stats: TeamGameStats model with team loaded.

    Returns:
        TeamBoxScoreResponse with computed percentages.

    Example:
        >>> response = _build_team_box_score(team_game_stats)
        >>> print(response.field_goal_pct)
        48.5
    """
    return TeamBoxScoreResponse(
        team_id=team_stats.team_id,
        team_name=team_stats.team.name,
        is_home=team_stats.is_home,
        points=team_stats.points,
        field_goals_made=team_stats.field_goals_made,
        field_goals_attempted=team_stats.field_goals_attempted,
        field_goal_pct=_compute_percentage(
            team_stats.field_goals_made, team_stats.field_goals_attempted
        ),
        three_pointers_made=team_stats.three_pointers_made,
        three_pointers_attempted=team_stats.three_pointers_attempted,
        three_point_pct=_compute_percentage(
            team_stats.three_pointers_made, team_stats.three_pointers_attempted
        ),
        free_throws_made=team_stats.free_throws_made,
        free_throws_attempted=team_stats.free_throws_attempted,
        free_throw_pct=_compute_percentage(
            team_stats.free_throws_made, team_stats.free_throws_attempted
        ),
        offensive_rebounds=team_stats.offensive_rebounds,
        defensive_rebounds=team_stats.defensive_rebounds,
        total_rebounds=team_stats.total_rebounds,
        assists=team_stats.assists,
        turnovers=team_stats.turnovers,
        steals=team_stats.steals,
        blocks=team_stats.blocks,
        personal_fouls=team_stats.personal_fouls,
        fast_break_points=team_stats.fast_break_points,
        points_in_paint=team_stats.points_in_paint,
        second_chance_points=team_stats.second_chance_points,
        bench_points=team_stats.bench_points,
    )


def _build_player_box_score(player_stats: PlayerGameStats) -> PlayerBoxScoreResponse:
    """
    Build PlayerBoxScoreResponse from PlayerGameStats model.

    Args:
        player_stats: PlayerGameStats model with player loaded.

    Returns:
        PlayerBoxScoreResponse with computed percentages and formatted minutes.

    Example:
        >>> response = _build_player_box_score(player_game_stats)
        >>> print(response.minutes_display)
        '35:42'
    """
    return PlayerBoxScoreResponse(
        player_id=player_stats.player_id,
        player_name=player_stats.player.full_name,
        team_id=player_stats.team_id,
        is_starter=player_stats.is_starter,
        minutes_played=player_stats.minutes_played,
        minutes_display=_format_minutes(player_stats.minutes_played),
        points=player_stats.points,
        field_goals_made=player_stats.field_goals_made,
        field_goals_attempted=player_stats.field_goals_attempted,
        field_goal_pct=_compute_percentage(
            player_stats.field_goals_made, player_stats.field_goals_attempted
        ),
        three_pointers_made=player_stats.three_pointers_made,
        three_pointers_attempted=player_stats.three_pointers_attempted,
        three_point_pct=_compute_percentage(
            player_stats.three_pointers_made, player_stats.three_pointers_attempted
        ),
        free_throws_made=player_stats.free_throws_made,
        free_throws_attempted=player_stats.free_throws_attempted,
        free_throw_pct=_compute_percentage(
            player_stats.free_throws_made, player_stats.free_throws_attempted
        ),
        offensive_rebounds=player_stats.offensive_rebounds,
        defensive_rebounds=player_stats.defensive_rebounds,
        total_rebounds=player_stats.total_rebounds,
        assists=player_stats.assists,
        turnovers=player_stats.turnovers,
        steals=player_stats.steals,
        blocks=player_stats.blocks,
        personal_fouls=player_stats.personal_fouls,
        plus_minus=player_stats.plus_minus,
    )


@router.get(
    "",
    response_model=GameListResponse,
    summary="List Games",
    description="Retrieve a paginated list of games with optional filters.",
)
def list_games(
    season_id: UUID | None = Query(
        default=None,
        description="Filter by season ID",
    ),
    team_id: UUID | None = Query(
        default=None,
        description="Filter by team ID (home or away)",
    ),
    start_date: date | None = Query(
        default=None,
        description="Filter games on or after this date",
    ),
    end_date: date | None = Query(
        default=None,
        description="Filter games on or before this date",
    ),
    game_status: GameStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by game status (SCHEDULED, LIVE, FINAL, POSTPONED, CANCELLED)",
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
) -> GameListResponse:
    """
    List games with optional filtering.

    Args:
        season_id: Filter games by season.
        team_id: Filter games by team (home or away).
        start_date: Filter games on or after this date.
        end_date: Filter games on or before this date.
        game_status: Filter games by status.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
        db: Database session (injected).

    Returns:
        GameListResponse containing list of games and total count.

    Example:
        >>> response = client.get("/api/v1/games?status=FINAL&limit=10")
        >>> data = response.json()
        >>> print(data["total"])
        82
    """
    service = GameService(db)
    filter_params = GameFilter(
        season_id=season_id,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
        status=game_status,
    )

    games, total = service.get_filtered(filter_params, skip=skip, limit=limit)

    items = []
    for game in games:
        items.append(
            GameResponse(
                id=game.id,
                season_id=game.season_id,
                home_team_id=game.home_team_id,
                home_team_name=game.home_team.name,
                away_team_id=game.away_team_id,
                away_team_name=game.away_team.name,
                game_date=game.game_date,
                status=game.status,
                home_score=game.home_score,
                away_score=game.away_score,
                venue=game.venue,
                attendance=game.attendance,
                external_ids=game.external_ids or {},
                created_at=game.created_at,
                updated_at=game.updated_at,
            )
        )

    return GameListResponse(items=items, total=total)


@router.get(
    "/{game_id}",
    response_model=GameWithBoxScoreResponse,
    summary="Get Game with Box Score",
    description="Retrieve a specific game by ID including complete box score data.",
    responses={
        404: {"description": "Game not found"},
    },
)
def get_game(
    game_id: UUID,
    db: Session = Depends(get_db),
) -> GameWithBoxScoreResponse:
    """
    Get a specific game by ID with complete box score.

    Args:
        game_id: UUID of the game to retrieve.
        db: Database session (injected).

    Returns:
        GameWithBoxScoreResponse with game details and box score data.

    Raises:
        HTTPException: 404 if game not found.

    Example:
        >>> response = client.get(f"/api/v1/games/{game_id}")
        >>> data = response.json()
        >>> print(f"{data['home_team_name']} {data['home_score']} - "
        ...       f"{data['away_score']} {data['away_team_name']}")
        "Los Angeles Lakers 112 - 108 Boston Celtics"
    """
    service = GameService(db)
    game = service.get_with_box_score(game_id)

    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game with id {game_id} not found",
        )

    # Find home and away team stats
    home_team_stats = None
    away_team_stats = None
    for team_stats in game.team_game_stats:
        if team_stats.is_home:
            home_team_stats = _build_team_box_score(team_stats)
        else:
            away_team_stats = _build_team_box_score(team_stats)

    # Build player box scores separated by team
    home_players = []
    away_players = []
    for player_stats in game.player_game_stats:
        player_box = _build_player_box_score(player_stats)
        if player_stats.team_id == game.home_team_id:
            home_players.append(player_box)
        else:
            away_players.append(player_box)

    # Sort players: starters first, then by points
    home_players.sort(key=lambda p: (not p.is_starter, -p.points))
    away_players.sort(key=lambda p: (not p.is_starter, -p.points))

    return GameWithBoxScoreResponse(
        id=game.id,
        season_id=game.season_id,
        home_team_id=game.home_team_id,
        home_team_name=game.home_team.name,
        away_team_id=game.away_team_id,
        away_team_name=game.away_team.name,
        game_date=game.game_date,
        status=game.status,
        home_score=game.home_score,
        away_score=game.away_score,
        venue=game.venue,
        attendance=game.attendance,
        external_ids=game.external_ids or {},
        home_team_stats=home_team_stats,
        away_team_stats=away_team_stats,
        home_players=home_players,
        away_players=away_players,
        created_at=game.created_at,
        updated_at=game.updated_at,
    )


@router.get(
    "/{game_id}/pbp",
    response_model=PlayByPlayResponse,
    summary="Get Play-by-Play",
    description="Retrieve play-by-play events for a game with optional filters.",
    responses={
        404: {"description": "Game not found"},
    },
)
def get_play_by_play(
    game_id: UUID,
    period: int | None = Query(
        default=None,
        ge=1,
        description="Filter by period number",
    ),
    event_type: str | None = Query(
        default=None,
        description="Filter by event type (SHOT, REBOUND, TURNOVER, etc.)",
    ),
    player_id: UUID | None = Query(
        default=None,
        description="Filter by player ID",
    ),
    team_id: UUID | None = Query(
        default=None,
        description="Filter by team ID",
    ),
    db: Session = Depends(get_db),
) -> PlayByPlayResponse:
    """
    Get play-by-play events for a game.

    Args:
        game_id: UUID of the game.
        period: Optional filter by period number.
        event_type: Optional filter by event type.
        player_id: Optional filter by player.
        team_id: Optional filter by team.
        db: Database session (injected).

    Returns:
        PlayByPlayResponse with list of events.

    Raises:
        HTTPException: 404 if game not found.

    Example:
        >>> response = client.get(f"/api/v1/games/{game_id}/pbp?period=4")
        >>> data = response.json()
        >>> print(f"Fourth quarter: {data['total_events']} events")
    """
    # First verify game exists
    game_service = GameService(db)
    game = game_service.get_by_id(game_id)

    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game with id {game_id} not found",
        )

    pbp_service = PlayByPlayService(db)
    filter_params = PlayByPlayFilter(
        period=period,
        event_type=event_type,
        player_id=player_id,
        team_id=team_id,
    )

    events = pbp_service.get_by_game(game_id, filter_params)

    event_responses = []
    for event in events:
        # Get related event IDs
        related_ids = [related.id for related in event.related_events]

        event_responses.append(
            PlayByPlayEventResponse(
                id=event.id,
                game_id=event.game_id,
                event_number=event.event_number,
                period=event.period,
                clock=event.clock,
                event_type=event.event_type,
                event_subtype=event.event_subtype,
                player_id=event.player_id,
                player_name=event.player.full_name if event.player else None,
                team_id=event.team_id,
                team_name=event.team.name if event.team else "",
                success=event.success,
                coord_x=event.coord_x,
                coord_y=event.coord_y,
                attributes=event.attributes or {},
                description=event.description,
                related_event_ids=related_ids,
            )
        )

    return PlayByPlayResponse(
        game_id=game_id,
        events=event_responses,
        total_events=len(event_responses),
    )
