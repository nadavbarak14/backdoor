"""
Players Router Module

FastAPI router for player-related endpoints.
Provides endpoints for searching players, retrieving player details
with team history, accessing player game logs, and player statistics.

Endpoints:
    GET /players - Search players with filters
    GET /players/{player_id} - Get player with team history
    GET /players/{player_id}/games - Get player game log
    GET /players/{player_id}/stats - Get player career stats
    GET /players/{player_id}/stats/{season_id} - Get player season stats

Usage:
    from src.api.v1.players import router

    app.include_router(router, prefix="/api/v1")
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core import get_db
from src.schemas import (
    PlayerCareerStatsResponse,
    PlayerFilter,
    PlayerGameLogResponse,
    PlayerGameStatsWithGameResponse,
    PlayerListResponse,
    PlayerResponse,
    PlayerSeasonStatsResponse,
    PlayerTeamHistoryResponse,
    PlayerWithHistoryResponse,
)
from src.services import PlayerGameStatsService, PlayerSeasonStatsService, PlayerService

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
            positions=[p.value for p in pth.positions],
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
        positions=[p.value for p in player.positions],
        external_ids=player.external_ids or {},
        created_at=player.created_at,
        updated_at=player.updated_at,
        team_history=team_history,
    )


@router.get(
    "/{player_id}/games",
    response_model=PlayerGameLogResponse,
    summary="Get Player Game Log",
    description="Retrieve a player's game-by-game statistics.",
    responses={
        404: {"description": "Player not found"},
    },
)
def get_player_games(
    player_id: UUID,
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
) -> PlayerGameLogResponse:
    """
    Get a player's game log with statistics.

    Args:
        player_id: UUID of the player.
        season_id: Optional filter by season.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.
        db: Database session (injected).

    Returns:
        PlayerGameLogResponse with list of games and stats.

    Raises:
        HTTPException: 404 if player not found.

    Example:
        >>> response = client.get(f"/api/v1/players/{player_id}/games")
        >>> data = response.json()
        >>> for game in data["items"]:
        ...     print(f"{game['game_date']}: {game['points']} pts ({game['result']})")
    """
    # Check player exists
    player_service = PlayerService(db)
    player = player_service.get_by_id(player_id)

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with id {player_id} not found",
        )

    stats_service = PlayerGameStatsService(db)
    game_log, total = stats_service.get_player_game_log(
        player_id=player_id,
        season_id=season_id,
        skip=skip,
        limit=limit,
    )

    items = []
    for stat in game_log:
        game = stat.game
        # Determine opponent and if player's team was home
        is_home = stat.team_id == game.home_team_id
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
            PlayerGameStatsWithGameResponse(
                id=stat.id,
                game_id=stat.game_id,
                player_id=stat.player_id,
                player_name=stat.player.full_name,
                team_id=stat.team_id,
                minutes_played=stat.minutes_played,
                is_starter=stat.is_starter,
                points=stat.points,
                field_goals_made=stat.field_goals_made,
                field_goals_attempted=stat.field_goals_attempted,
                two_pointers_made=stat.two_pointers_made,
                two_pointers_attempted=stat.two_pointers_attempted,
                three_pointers_made=stat.three_pointers_made,
                three_pointers_attempted=stat.three_pointers_attempted,
                free_throws_made=stat.free_throws_made,
                free_throws_attempted=stat.free_throws_attempted,
                offensive_rebounds=stat.offensive_rebounds,
                defensive_rebounds=stat.defensive_rebounds,
                total_rebounds=stat.total_rebounds,
                assists=stat.assists,
                turnovers=stat.turnovers,
                steals=stat.steals,
                blocks=stat.blocks,
                personal_fouls=stat.personal_fouls,
                plus_minus=stat.plus_minus,
                efficiency=stat.efficiency,
                extra_stats=stat.extra_stats or {},
                game_date=game.game_date,
                opponent_team_id=opponent_team_id,
                opponent_team_name=opponent_team_name,
                is_home=is_home,
                team_score=team_score,
                opponent_score=opponent_score,
            )
        )

    return PlayerGameLogResponse(items=items, total=total)


@router.get(
    "/{player_id}/stats",
    response_model=PlayerCareerStatsResponse,
    summary="Get Player Career Stats",
    description="Retrieve a player's career statistics including all season stats.",
    responses={
        404: {"description": "Player not found"},
    },
)
def get_player_career_stats(
    player_id: UUID,
    db: Session = Depends(get_db),
) -> PlayerCareerStatsResponse:
    """
    Get a player's career statistics.

    Returns aggregated career totals and a list of individual season stats.
    If a player was traded mid-season, they will have multiple entries for
    that season (one per team).

    Args:
        player_id: UUID of the player.
        db: Database session (injected).

    Returns:
        PlayerCareerStatsResponse with career totals and season breakdown.

    Raises:
        HTTPException: 404 if player not found.

    Example:
        >>> response = client.get(f"/api/v1/players/{player_id}/stats")
        >>> data = response.json()
        >>> print(f"Career PPG: {data['career_avg_points']}")
        >>> for season in data["seasons"]:
        ...     print(f"{season['season_name']}: {season['avg_points']} PPG")
    """
    # Check player exists
    player_service = PlayerService(db)
    player = player_service.get_by_id(player_id)

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with id {player_id} not found",
        )

    stats_service = PlayerSeasonStatsService(db)
    season_stats = stats_service.get_player_career(player_id)

    # Calculate career totals
    career_games_played = sum(s.games_played for s in season_stats)
    career_games_started = sum(s.games_started for s in season_stats)
    career_points = sum(s.total_points for s in season_stats)
    career_rebounds = sum(s.total_rebounds for s in season_stats)
    career_assists = sum(s.total_assists for s in season_stats)
    career_steals = sum(s.total_steals for s in season_stats)
    career_blocks = sum(s.total_blocks for s in season_stats)
    career_turnovers = sum(s.total_turnovers for s in season_stats)

    # Calculate career averages
    if career_games_played > 0:
        career_avg_points = round(career_points / career_games_played, 1)
        career_avg_rebounds = round(career_rebounds / career_games_played, 1)
        career_avg_assists = round(career_assists / career_games_played, 1)
    else:
        career_avg_points = 0.0
        career_avg_rebounds = 0.0
        career_avg_assists = 0.0

    # Convert season stats to response models
    seasons = [
        PlayerSeasonStatsResponse(
            id=s.id,
            player_id=s.player_id,
            player_name=s.player.full_name,
            team_id=s.team_id,
            team_name=s.team.name,
            season_id=s.season_id,
            season_name=s.season.name,
            league_code=s.season.league.code if s.season.league else None,
            games_played=s.games_played,
            games_started=s.games_started,
            total_minutes=s.total_minutes,
            total_points=s.total_points,
            total_field_goals_made=s.total_field_goals_made,
            total_field_goals_attempted=s.total_field_goals_attempted,
            total_two_pointers_made=s.total_two_pointers_made,
            total_two_pointers_attempted=s.total_two_pointers_attempted,
            total_three_pointers_made=s.total_three_pointers_made,
            total_three_pointers_attempted=s.total_three_pointers_attempted,
            total_free_throws_made=s.total_free_throws_made,
            total_free_throws_attempted=s.total_free_throws_attempted,
            total_offensive_rebounds=s.total_offensive_rebounds,
            total_defensive_rebounds=s.total_defensive_rebounds,
            total_rebounds=s.total_rebounds,
            total_assists=s.total_assists,
            total_turnovers=s.total_turnovers,
            total_steals=s.total_steals,
            total_blocks=s.total_blocks,
            total_personal_fouls=s.total_personal_fouls,
            total_plus_minus=s.total_plus_minus,
            avg_minutes=s.avg_minutes,
            avg_points=s.avg_points,
            avg_rebounds=s.avg_rebounds,
            avg_assists=s.avg_assists,
            avg_turnovers=s.avg_turnovers,
            avg_steals=s.avg_steals,
            avg_blocks=s.avg_blocks,
            field_goal_pct=s.field_goal_pct * 100 if s.field_goal_pct else None,
            two_point_pct=s.two_point_pct * 100 if s.two_point_pct else None,
            three_point_pct=s.three_point_pct * 100 if s.three_point_pct else None,
            free_throw_pct=s.free_throw_pct * 100 if s.free_throw_pct else None,
            true_shooting_pct=(
                s.true_shooting_pct * 100 if s.true_shooting_pct else None
            ),
            effective_field_goal_pct=(
                s.effective_field_goal_pct * 100 if s.effective_field_goal_pct else None
            ),
            assist_turnover_ratio=s.assist_turnover_ratio,
            last_calculated=s.last_calculated,
        )
        for s in season_stats
    ]

    return PlayerCareerStatsResponse(
        player_id=player.id,
        player_name=player.full_name,
        career_games_played=career_games_played,
        career_games_started=career_games_started,
        career_points=career_points,
        career_rebounds=career_rebounds,
        career_assists=career_assists,
        career_steals=career_steals,
        career_blocks=career_blocks,
        career_turnovers=career_turnovers,
        career_avg_points=career_avg_points,
        career_avg_rebounds=career_avg_rebounds,
        career_avg_assists=career_avg_assists,
        seasons=seasons,
    )


@router.get(
    "/{player_id}/stats/{season_id}",
    response_model=list[PlayerSeasonStatsResponse],
    summary="Get Player Season Stats",
    description="Retrieve a player's statistics for a specific season.",
    responses={
        404: {"description": "Player or season not found"},
    },
)
def get_player_season_stats(
    player_id: UUID,
    season_id: UUID,
    db: Session = Depends(get_db),
) -> list[PlayerSeasonStatsResponse]:
    """
    Get a player's statistics for a specific season.

    If a player was traded mid-season, this returns multiple entries
    (one per team they played for during the season).

    Args:
        player_id: UUID of the player.
        season_id: UUID of the season.
        db: Database session (injected).

    Returns:
        List of PlayerSeasonStatsResponse (one per team if traded).

    Raises:
        HTTPException: 404 if player not found or no stats for season.

    Example:
        >>> response = client.get(f"/api/v1/players/{player_id}/stats/{season_id}")
        >>> data = response.json()
        >>> for team_stats in data:
        ...     print(f"{team_stats['team_name']}: {team_stats['avg_points']} PPG")
    """
    # Check player exists
    player_service = PlayerService(db)
    player = player_service.get_by_id(player_id)

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with id {player_id} not found",
        )

    stats_service = PlayerSeasonStatsService(db)
    season_stats = stats_service.get_player_season(player_id, season_id)

    if not season_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stats found for player {player_id} in season {season_id}",
        )

    return [
        PlayerSeasonStatsResponse(
            id=s.id,
            player_id=s.player_id,
            player_name=s.player.full_name,
            team_id=s.team_id,
            team_name=s.team.name,
            season_id=s.season_id,
            season_name=s.season.name,
            games_played=s.games_played,
            games_started=s.games_started,
            total_minutes=s.total_minutes,
            total_points=s.total_points,
            total_field_goals_made=s.total_field_goals_made,
            total_field_goals_attempted=s.total_field_goals_attempted,
            total_two_pointers_made=s.total_two_pointers_made,
            total_two_pointers_attempted=s.total_two_pointers_attempted,
            total_three_pointers_made=s.total_three_pointers_made,
            total_three_pointers_attempted=s.total_three_pointers_attempted,
            total_free_throws_made=s.total_free_throws_made,
            total_free_throws_attempted=s.total_free_throws_attempted,
            total_offensive_rebounds=s.total_offensive_rebounds,
            total_defensive_rebounds=s.total_defensive_rebounds,
            total_rebounds=s.total_rebounds,
            total_assists=s.total_assists,
            total_turnovers=s.total_turnovers,
            total_steals=s.total_steals,
            total_blocks=s.total_blocks,
            total_personal_fouls=s.total_personal_fouls,
            total_plus_minus=s.total_plus_minus,
            avg_minutes=s.avg_minutes,
            avg_points=s.avg_points,
            avg_rebounds=s.avg_rebounds,
            avg_assists=s.avg_assists,
            avg_turnovers=s.avg_turnovers,
            avg_steals=s.avg_steals,
            avg_blocks=s.avg_blocks,
            field_goal_pct=s.field_goal_pct * 100 if s.field_goal_pct else None,
            two_point_pct=s.two_point_pct * 100 if s.two_point_pct else None,
            three_point_pct=s.three_point_pct * 100 if s.three_point_pct else None,
            free_throw_pct=s.free_throw_pct * 100 if s.free_throw_pct else None,
            true_shooting_pct=(
                s.true_shooting_pct * 100 if s.true_shooting_pct else None
            ),
            effective_field_goal_pct=(
                s.effective_field_goal_pct * 100 if s.effective_field_goal_pct else None
            ),
            assist_turnover_ratio=s.assist_turnover_ratio,
            last_calculated=s.last_calculated,
        )
        for s in season_stats
    ]
