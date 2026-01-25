"""
Stats Router Module

FastAPI router for statistics-related endpoints.
Provides endpoints for retrieving league leaders across various categories.

Endpoints:
    GET /stats/leaders - Get league leaders by category

Usage:
    from src.api.v1.stats import router

    app.include_router(router, prefix="/api/v1")
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core import get_db
from src.schemas import (
    LeagueLeaderEntry,
    LeagueLeadersResponse,
    StatsCategory,
)
from src.services import PlayerSeasonStatsService, SeasonService

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get(
    "/leaders",
    response_model=LeagueLeadersResponse,
    summary="Get League Leaders",
    description="Retrieve league leaders for a statistical category in a season.",
    responses={
        400: {"description": "Invalid category"},
        404: {"description": "Season not found"},
    },
)
def get_league_leaders(
    season_id: UUID = Query(
        ...,
        description="UUID of the season to query",
    ),
    category: StatsCategory = Query(
        default=StatsCategory.POINTS,
        description="Statistical category to rank by",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of leaders to return",
    ),
    min_games: int = Query(
        default=1,
        ge=0,
        description="Minimum games played to qualify",
    ),
    db: Session = Depends(get_db),
) -> LeagueLeadersResponse:
    """
    Get league leaders for a statistical category.

    Returns the top players ranked by the specified category for a given season.
    Players must meet the minimum games requirement to qualify.

    Args:
        season_id: UUID of the season.
        category: Statistical category to rank by.
        limit: Maximum number of leaders to return.
        min_games: Minimum games played to qualify.
        db: Database session (injected).

    Returns:
        LeagueLeadersResponse with category and list of leaders.

    Raises:
        HTTPException: 404 if season not found.
        HTTPException: 400 if category is invalid.

    Example:
        >>> response = client.get(
        ...     "/api/v1/stats/leaders",
        ...     params={"season_id": season_id, "category": "points", "min_games": 20}
        ... )
        >>> data = response.json()
        >>> for leader in data["leaders"]:
        ...     print(f"{leader['rank']}. {leader['player_name']}: {leader['value']}")
    """
    # Check season exists
    season_service = SeasonService(db)
    season = season_service.get_by_id(season_id)

    if season is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Season with id {season_id} not found",
        )

    # Map StatsCategory enum to service category names
    category_mapping = {
        StatsCategory.POINTS: "points",
        StatsCategory.REBOUNDS: "rebounds",
        StatsCategory.ASSISTS: "assists",
        StatsCategory.STEALS: "steals",
        StatsCategory.BLOCKS: "blocks",
        StatsCategory.FIELD_GOAL_PCT: "field_goal_pct",
        StatsCategory.THREE_POINT_PCT: "three_point_pct",
        StatsCategory.FREE_THROW_PCT: "free_throw_pct",
        StatsCategory.MINUTES: "avg_minutes",
        StatsCategory.EFFICIENCY: "efficiency",
    }

    service_category = category_mapping.get(category)
    if service_category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}",
        )

    stats_service = PlayerSeasonStatsService(db)

    try:
        leader_stats = stats_service.get_league_leaders(
            season_id=season_id,
            category=service_category,
            limit=limit,
            min_games=min_games,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Map category to the value attribute
    value_mapping = {
        StatsCategory.POINTS: lambda s: s.avg_points,
        StatsCategory.REBOUNDS: lambda s: s.avg_rebounds,
        StatsCategory.ASSISTS: lambda s: s.avg_assists,
        StatsCategory.STEALS: lambda s: s.avg_steals,
        StatsCategory.BLOCKS: lambda s: s.avg_blocks,
        StatsCategory.FIELD_GOAL_PCT: lambda s: (
            s.field_goal_pct * 100 if s.field_goal_pct else 0.0
        ),
        StatsCategory.THREE_POINT_PCT: lambda s: (
            s.three_point_pct * 100 if s.three_point_pct else 0.0
        ),
        StatsCategory.FREE_THROW_PCT: lambda s: (
            s.free_throw_pct * 100 if s.free_throw_pct else 0.0
        ),
        StatsCategory.MINUTES: lambda s: s.avg_minutes / 60,  # Convert to minutes
        StatsCategory.EFFICIENCY: lambda s: (
            s.true_shooting_pct * 100 if s.true_shooting_pct else 0.0
        ),
    }

    get_value = value_mapping[category]

    leaders = [
        LeagueLeaderEntry(
            rank=i + 1,
            player_id=stats.player_id,
            player_name=stats.player.full_name,
            team_id=stats.team_id,
            team_name=stats.team.name,
            value=round(get_value(stats), 1),
            games_played=stats.games_played,
        )
        for i, stats in enumerate(leader_stats)
    ]

    return LeagueLeadersResponse(
        category=category,
        season_id=season.id,
        season_name=season.name,
        min_games=min_games,
        leaders=leaders,
    )
