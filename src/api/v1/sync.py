"""
Sync Router Module

FastAPI router for data synchronization endpoints.
Provides endpoints for viewing sync history, triggering syncs,
and checking sync status.

Endpoints:
    GET /sync/logs - Get sync operation history with filters
    GET /sync/status - Get current sync status for all sources
    POST /sync/{source}/season/{season_id} - Trigger sync for a season
    POST /sync/{source}/season/{season_id}/stream - Stream sync progress via SSE
    POST /sync/{source}/game/{game_id} - Trigger sync for a single game
    POST /sync/{source}/teams/{season_id} - Sync team rosters for a season

Usage:
    from src.api.v1.sync import router

    app.include_router(router, prefix="/api/v1")
"""

import json
from collections.abc import AsyncGenerator
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core import get_db
from src.models.league import Season
from src.schemas import (
    SeasonSyncCoverage,
    SyncCoverageResponse,
    SyncLogFilter,
    SyncLogListResponse,
    SyncLogResponse,
    SyncStatus,
)
from src.schemas.sync import (
    SyncSourceStatus,
    SyncStatusResponse,
)
from src.services import SyncCoverageService, SyncLogService
from src.sync import SyncConfig
from src.sync.manager import SyncManager

router = APIRouter(prefix="/sync", tags=["Sync"])


def _get_sync_manager(db: Session) -> SyncManager:
    """
    Create a SyncManager with configured adapters.

    This is a factory function that creates adapters and the manager
    for each request. In production, adapters should be cached.

    Args:
        db: Database session.

    Returns:
        Configured SyncManager instance.
    """
    from src.sync.euroleague import (
        EuroleagueClient,
        EuroleagueDirectClient,
    )
    from src.sync.euroleague.adapter import EuroleagueAdapter
    from src.sync.euroleague.mapper import EuroleagueMapper
    from src.sync.ibasketball import (
        IBasketballApiClient,
        IBasketballMapper,
        IBasketballScraper,
    )
    from src.sync.ibasketball.adapter import IBasketballAdapter
    from src.sync.nba import NBAClient, NBAConfig, NBAMapper
    from src.sync.nba.adapter import NBAAdapter
    from src.sync.winner import WinnerClient, WinnerScraper
    from src.sync.winner.adapter import WinnerAdapter
    from src.sync.winner.mapper import WinnerMapper

    # Initialize Winner adapter
    winner_client = WinnerClient(db)
    winner_scraper = WinnerScraper(db)
    winner_mapper = WinnerMapper()
    winner_adapter = WinnerAdapter(winner_client, winner_scraper, winner_mapper)

    # Initialize Euroleague adapter
    euroleague_client = EuroleagueClient(db)
    euroleague_direct_client = EuroleagueDirectClient(db)
    euroleague_mapper = EuroleagueMapper()
    euroleague_adapter = EuroleagueAdapter(
        euroleague_client, euroleague_direct_client, euroleague_mapper
    )

    # Initialize iBasketball adapter
    ibasketball_client = IBasketballApiClient(db)
    ibasketball_mapper = IBasketballMapper()
    ibasketball_scraper = IBasketballScraper(db)
    ibasketball_adapter = IBasketballAdapter(
        ibasketball_client, ibasketball_mapper, ibasketball_scraper
    )

    # Initialize NBA adapter
    nba_config = NBAConfig()
    nba_client = NBAClient(nba_config)
    nba_mapper = NBAMapper()
    nba_adapter = NBAAdapter(nba_client, nba_mapper, nba_config)

    # Create config
    config = SyncConfig.from_settings()

    # Create manager with all adapters
    return SyncManager(
        db=db,
        adapters={
            "winner": winner_adapter,
            "euroleague": euroleague_adapter,
            "ibasketball": ibasketball_adapter,
            "nba": nba_adapter,
        },
        config=config,
    )


@router.get(
    "/logs",
    response_model=SyncLogListResponse,
    summary="List Sync Logs",
    description="Retrieve sync operation history with optional filters.",
)
def list_sync_logs(
    source: str | None = Query(
        default=None,
        description="Filter by data source (e.g., 'winner', 'euroleague')",
    ),
    entity_type: str | None = Query(
        default=None,
        description="Filter by entity type (e.g., 'games', 'players', 'stats', 'pbp')",
    ),
    status: SyncStatus | None = Query(
        default=None,
        description="Filter by sync status",
    ),
    season_id: UUID | None = Query(
        default=None,
        description="Filter by season ID",
    ),
    start_date: datetime | None = Query(
        default=None,
        description="Filter logs started on or after this datetime",
    ),
    end_date: datetime | None = Query(
        default=None,
        description="Filter logs started on or before this datetime",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page",
    ),
    db: Session = Depends(get_db),
) -> SyncLogListResponse:
    """
    Get sync operation history with optional filters.

    Returns paginated list of sync logs ordered by most recent first.
    Supports filtering by source, entity type, status, season, and date range.

    Args:
        source: Filter by external data source.
        entity_type: Filter by type of entity synced.
        status: Filter by sync status.
        season_id: Filter by season.
        start_date: Filter logs started on or after this date.
        end_date: Filter logs started on or before this date.
        page: Page number for pagination.
        page_size: Number of items per page.
        db: Database session (injected).

    Returns:
        SyncLogListResponse with list of sync logs and total count.

    Example:
        >>> response = client.get(
        ...     "/api/v1/sync/logs",
        ...     params={"source": "winner", "status": "COMPLETED"}
        ... )
        >>> data = response.json()
        >>> for log in data["items"]:
        ...     print(f"{log['entity_type']}: {log['records_processed']} records")
    """
    service = SyncLogService(db)

    filter_params = SyncLogFilter(
        source=source,
        entity_type=entity_type,
        status=status,
        season_id=season_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    logs, total = service.get_filtered(filter_params)

    items = [
        SyncLogResponse(
            id=log.id,
            source=log.source,
            entity_type=log.entity_type,
            status=SyncStatus(log.status),
            season_id=log.season_id,
            season_name=log.season.name if log.season else None,
            game_id=log.game_id,
            records_processed=log.records_processed,
            records_created=log.records_created,
            records_updated=log.records_updated,
            records_skipped=log.records_skipped,
            error_message=log.error_message,
            error_details=log.error_details,
            started_at=log.started_at,
            completed_at=log.completed_at,
        )
        for log in logs
    ]

    return SyncLogListResponse(items=items, total=total)


@router.get(
    "/status",
    response_model=SyncStatusResponse,
    summary="Get Sync Status",
    description="Get current sync status for all configured sources.",
)
def get_sync_status(
    db: Session = Depends(get_db),
) -> SyncStatusResponse:
    """
    Get current sync status for all sources.

    Returns status information including enabled sources, running syncs,
    and latest sync info for each source.

    Args:
        db: Database session (injected).

    Returns:
        SyncStatusResponse with source statuses.

    Example:
        >>> response = client.get("/api/v1/sync/status")
        >>> data = response.json()
        >>> for source in data["sources"]:
        ...     print(f"{source['name']}: enabled={source['enabled']}")
    """
    manager = _get_sync_manager(db)
    status_data = manager.get_sync_status()

    sources = [
        SyncSourceStatus(
            name=s["name"],
            enabled=s["enabled"],
            auto_sync_enabled=s.get("auto_sync_enabled", False),
            sync_interval_minutes=s.get("sync_interval_minutes", 60),
            running_syncs=s.get("running_syncs", 0),
            latest_season_sync=s.get("latest_season_sync"),
            latest_game_sync=s.get("latest_game_sync"),
        )
        for s in status_data["sources"]
    ]

    return SyncStatusResponse(
        sources=sources,
        total_running_syncs=status_data.get("total_running_syncs", 0),
    )


@router.get(
    "/coverage",
    response_model=SyncCoverageResponse,
    summary="Get Sync Coverage",
    description="Get detailed sync coverage statistics per season.",
)
def get_sync_coverage(
    db: Session = Depends(get_db),
) -> SyncCoverageResponse:
    """
    Get detailed sync coverage statistics for all seasons.

    Returns per-season breakdown of what data has been synced including:
    - Total games vs games with boxscore vs games with play-by-play
    - Total players vs players with bio data (position/height)
    - Percentages for each category

    This endpoint is useful for identifying what data needs to be synced
    and for monitoring overall sync progress.

    Args:
        db: Database session (injected).

    Returns:
        SyncCoverageResponse with per-season coverage statistics.

    Example:
        >>> response = client.get("/api/v1/sync/coverage")
        >>> data = response.json()
        >>> for season in data["seasons"]:
        ...     print(f"{season['season_name']}: {season['boxscore_pct']}% boxscore")
    """
    service = SyncCoverageService(db)
    coverage_list = service.get_all_seasons_coverage()

    seasons = [
        SeasonSyncCoverage(
            season_id=c.season_id,
            season_name=c.season_name,
            league_name=c.league_name,
            games_total=c.games_total,
            games_with_boxscore=c.games_with_boxscore,
            games_with_pbp=c.games_with_pbp,
            players_total=c.players_total,
            players_with_bio=c.players_with_bio,
            boxscore_pct=c.boxscore_pct,
            pbp_pct=c.pbp_pct,
            bio_pct=c.bio_pct,
        )
        for c in coverage_list
    ]

    return SyncCoverageResponse(
        seasons=seasons,
        total_games=sum(c.games_total for c in coverage_list),
        total_games_with_boxscore=sum(c.games_with_boxscore for c in coverage_list),
        total_games_with_pbp=sum(c.games_with_pbp for c in coverage_list),
    )


@router.post(
    "/{source}/season/{season_id}",
    response_model=SyncLogResponse,
    summary="Sync Season",
    description="Trigger sync for all games in a season.",
)
async def sync_season(
    source: str,
    season_id: str,
    include_pbp: bool = Query(
        default=True,
        description="Whether to sync play-by-play data",
    ),
    db: Session = Depends(get_db),
) -> SyncLogResponse:
    """
    Trigger sync for a season.

    Syncs all final games for the specified season that haven't been
    synced yet. Each game includes box score and optionally PBP data.

    Args:
        source: Data source name (e.g., "winner", "euroleague").
        season_id: External season identifier (e.g., "2024-25").
        include_pbp: Whether to sync play-by-play data.
        db: Database session (injected).

    Returns:
        SyncLogResponse with sync operation results.

    Raises:
        HTTPException: If source is not found or not enabled.

    Example:
        >>> response = client.post(
        ...     "/api/v1/sync/winner/season/2024-25",
        ...     params={"include_pbp": True}
        ... )
        >>> data = response.json()
        >>> print(f"Synced {data['records_created']} games")
    """
    manager = _get_sync_manager(db)

    try:
        sync_log = await manager.sync_season(
            source=source,
            season_external_id=season_id,
            include_pbp=include_pbp,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

    return SyncLogResponse(
        id=sync_log.id,
        source=sync_log.source,
        entity_type=sync_log.entity_type,
        status=SyncStatus(sync_log.status),
        season_id=sync_log.season_id,
        season_name=sync_log.season.name if sync_log.season else None,
        game_id=sync_log.game_id,
        records_processed=sync_log.records_processed,
        records_created=sync_log.records_created,
        records_updated=sync_log.records_updated,
        records_skipped=sync_log.records_skipped,
        error_message=sync_log.error_message,
        error_details=sync_log.error_details,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
    )


async def _format_sse_events(
    manager: "SyncManager",
    source: str,
    season_id: str,
    include_pbp: bool,
) -> AsyncGenerator[str, None]:
    """
    Format sync progress events as Server-Sent Events.

    Args:
        manager: SyncManager instance.
        source: Data source name.
        season_id: External season identifier.
        include_pbp: Whether to sync play-by-play data.

    Yields:
        SSE-formatted strings for streaming response.
    """
    async for event in manager.sync_season_with_progress(
        source=source,
        season_external_id=season_id,
        include_pbp=include_pbp,
    ):
        event_type = event.get("event", "message")
        data = json.dumps(event)
        yield f"event: {event_type}\ndata: {data}\n\n"


@router.post(
    "/{source}/season/{season_id}/stream",
    summary="Stream Season Sync Progress",
    description="Trigger sync for a season with real-time progress via SSE.",
    responses={
        200: {
            "description": "SSE stream of sync progress events",
            "content": {"text/event-stream": {}},
        }
    },
)
async def sync_season_stream(
    source: str,
    season_id: str,
    include_pbp: bool = Query(
        default=True,
        description="Whether to sync play-by-play data",
    ),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Trigger sync for a season with streaming progress.

    Returns a Server-Sent Events stream with real-time progress updates.
    Each event contains JSON data about the current sync state.

    Event types:
    - start: Sync has started, includes total game count
    - progress: Currently syncing a game
    - synced: A game was successfully synced
    - error: A game failed to sync (sync continues)
    - complete: Sync finished, includes final summary

    Args:
        source: Data source name (e.g., "winner", "euroleague").
        season_id: External season identifier (e.g., "2024-25").
        include_pbp: Whether to sync play-by-play data.
        db: Database session (injected).

    Returns:
        StreamingResponse with text/event-stream content type.

    Raises:
        HTTPException: If source is not found or not enabled.

    Example:
        >>> # Using curl with streaming
        >>> curl -N -X POST "http://localhost:8000/api/v1/sync/winner/season/2024-25/stream"
        event: start
        data: {"event": "start", "phase": "games", "total": 120, "skipped": 50}

        event: progress
        data: {"event": "progress", "current": 1, "total": 70, "game_id": "12345", "status": "syncing"}

        event: synced
        data: {"event": "synced", "game_id": "12345"}

        event: complete
        data: {"event": "complete", "sync_log": {"id": "uuid", "status": "COMPLETED", ...}}
    """
    manager = _get_sync_manager(db)

    # Validate source upfront
    try:
        manager._get_adapter(source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return StreamingResponse(
        _format_sse_events(manager, source, season_id, include_pbp),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{source}/game/{game_id}",
    response_model=SyncLogResponse,
    summary="Sync Game",
    description="Trigger sync for a single game.",
)
async def sync_game(
    source: str,
    game_id: str,
    include_pbp: bool = Query(
        default=True,
        description="Whether to sync play-by-play data",
    ),
    db: Session = Depends(get_db),
) -> SyncLogResponse:
    """
    Trigger sync for a single game.

    Syncs the specified game with box score and optionally PBP data.
    If the game is already synced, returns immediately with skipped status.

    Args:
        source: Data source name (e.g., "winner", "euroleague").
        game_id: External game identifier.
        include_pbp: Whether to sync play-by-play data.
        db: Database session (injected).

    Returns:
        SyncLogResponse with sync operation results.

    Raises:
        HTTPException: If source is not found or not enabled.

    Example:
        >>> response = client.post(
        ...     "/api/v1/sync/winner/game/12345",
        ...     params={"include_pbp": True}
        ... )
    """
    manager = _get_sync_manager(db)

    try:
        sync_log = await manager.sync_game(
            source=source,
            game_external_id=game_id,
            include_pbp=include_pbp,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

    return SyncLogResponse(
        id=sync_log.id,
        source=sync_log.source,
        entity_type=sync_log.entity_type,
        status=SyncStatus(sync_log.status),
        season_id=sync_log.season_id,
        season_name=sync_log.season.name if sync_log.season else None,
        game_id=sync_log.game_id,
        records_processed=sync_log.records_processed,
        records_created=sync_log.records_created,
        records_updated=sync_log.records_updated,
        records_skipped=sync_log.records_skipped,
        error_message=sync_log.error_message,
        error_details=sync_log.error_details,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
    )


@router.post(
    "/{source}/teams/{season_id}",
    response_model=SyncLogResponse,
    summary="Sync Teams",
    description="Sync team rosters for a season.",
)
async def sync_teams(
    source: str,
    season_id: str,
    db: Session = Depends(get_db),
) -> SyncLogResponse:
    """
    Sync team rosters for a season.

    Fetches all teams for the season and creates/updates team records
    along with their season-specific data.

    Args:
        source: Data source name (e.g., "winner", "euroleague").
        season_id: External season identifier (e.g., "2024-25").
        db: Database session (injected).

    Returns:
        SyncLogResponse with sync operation results.

    Raises:
        HTTPException: If source is not found or not enabled.

    Example:
        >>> response = client.post("/api/v1/sync/winner/teams/2024-25")
    """
    manager = _get_sync_manager(db)

    try:
        sync_log = await manager.sync_teams(
            source=source,
            season_external_id=season_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

    return SyncLogResponse(
        id=sync_log.id,
        source=sync_log.source,
        entity_type=sync_log.entity_type,
        status=SyncStatus(sync_log.status),
        season_id=sync_log.season_id,
        season_name=sync_log.season.name if sync_log.season else None,
        game_id=sync_log.game_id,
        records_processed=sync_log.records_processed,
        records_created=sync_log.records_created,
        records_updated=sync_log.records_updated,
        records_skipped=sync_log.records_skipped,
        error_message=sync_log.error_message,
        error_details=sync_log.error_details,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
    )


@router.post(
    "/{source}/rosters/{season_id}",
    response_model=SyncLogResponse,
    summary="Sync Rosters",
    description="Sync player roster data (positions) for all teams in a season.",
)
async def sync_rosters(
    source: str,
    season_id: str,
    db: Session = Depends(get_db),
) -> SyncLogResponse:
    """
    Sync player roster data for all teams in a season.

    Fetches team rosters from the source and updates player positions
    in PlayerTeamHistory records. Only updates players that don't have
    position data yet.

    Args:
        source: Data source name (e.g., "winner").
        season_id: External season identifier (e.g., "2025-26").
        db: Database session (injected).

    Returns:
        SyncLogResponse with sync operation results.

    Raises:
        HTTPException: If source is not found or not enabled.

    Example:
        >>> response = client.post("/api/v1/sync/winner/rosters/2025-26")
        >>> data = response.json()
        >>> print(f"Updated {data['records_updated']} player positions")
    """
    from src.models.league import Season

    manager = _get_sync_manager(db)

    # Find internal season by name
    from sqlalchemy import select

    stmt = select(Season).where(Season.name == season_id)
    season = db.scalars(stmt).first()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {season_id} not found")

    try:
        sync_log = await manager.sync_all_player_bios(
            source=source,
            season_id=season.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

    return SyncLogResponse(
        id=sync_log.id,
        source=sync_log.source,
        entity_type=sync_log.entity_type,
        status=SyncStatus(sync_log.status),
        season_id=sync_log.season_id,
        season_name=sync_log.season.name if sync_log.season else None,
        game_id=sync_log.game_id,
        records_processed=sync_log.records_processed,
        records_created=sync_log.records_created,
        records_updated=sync_log.records_updated,
        records_skipped=sync_log.records_skipped,
        error_message=sync_log.error_message,
        error_details=sync_log.error_details,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
    )


@router.get(
    "/completeness",
    summary="Get Sync Completeness Report",
    description="Get overall sync completeness statistics for all data.",
)
def get_sync_completeness(
    source: str | None = Query(
        default=None,
        description="Filter by data source (e.g., 'winner', 'euroleague')",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get overall sync completeness statistics.

    Unlike /coverage which is per-season, this endpoint returns
    aggregate completeness stats across all data, identifying what
    needs to be resynced.

    A record is incomplete when:
    - Player: missing height, birth_date, or has empty positions
    - Game: missing PlayerGameStats or PlayByPlayEvents
    - Team: missing name or short_name

    Args:
        source: Optional filter by data source.
        db: Database session (injected).

    Returns:
        Dict with completeness stats per entity type.

    Example:
        >>> response = client.get("/api/v1/sync/completeness?source=winner")
        >>> data = response.json()
        >>> print(f"Players: {data['players']['complete_pct']}% complete")
    """
    from src.sync.completeness import get_sync_completeness_report

    return get_sync_completeness_report(db, source)


@router.get(
    "/incomplete/players",
    summary="List Incomplete Players",
    description="Get list of players missing bio data.",
)
def list_incomplete_players(
    source: str | None = Query(
        default=None,
        description="Filter by data source",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of players to return",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get players with missing bio data.

    Returns players that are missing height, birth_date, or have
    empty positions list. These players need to have their bio
    data fetched from the source.

    Args:
        source: Optional filter by data source.
        limit: Maximum number of results.
        db: Database session (injected).

    Returns:
        Dict with count and list of incomplete player details.

    Example:
        >>> response = client.get("/api/v1/sync/incomplete/players?source=euroleague")
        >>> data = response.json()
        >>> for player in data["players"]:
        ...     print(f"{player['name']}: missing {player['missing']}")
    """
    from src.sync.completeness import get_incomplete_players

    incomplete = get_incomplete_players(db, source, limit)

    players = []
    for p in incomplete:
        missing = []
        if p.height_cm is None:
            missing.append("height")
        if p.birth_date is None:
            missing.append("birth_date")
        if not p.positions:
            missing.append("positions")

        players.append({
            "id": str(p.id),
            "name": p.full_name,
            "external_ids": p.external_ids,
            "missing": missing,
        })

    return {
        "count": len(players),
        "source": source,
        "players": players,
    }


@router.get(
    "/incomplete/games",
    summary="List Incomplete Games",
    description="Get list of games missing stats or play-by-play data.",
)
def list_incomplete_games(
    source: str | None = Query(
        default=None,
        description="Filter by data source",
    ),
    missing: str = Query(
        default="stats",
        description="What data is missing: 'stats', 'pbp', or 'both'",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of games to return",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get FINAL games with missing data.

    Returns games that are marked as FINAL but are missing either
    boxscore stats, play-by-play events, or both.

    Args:
        source: Optional filter by data source.
        missing: What type of data to check for ('stats', 'pbp', 'both').
        limit: Maximum number of results.
        db: Database session (injected).

    Returns:
        Dict with count and list of incomplete game details.

    Example:
        >>> response = client.get("/api/v1/sync/incomplete/games?missing=both")
    """
    from src.sync.completeness import get_games_without_pbp, get_games_without_stats

    games = []
    game_ids_seen = set()

    if missing in ("stats", "both"):
        for g in get_games_without_stats(db, source, limit):
            if g.id not in game_ids_seen:
                games.append({
                    "id": str(g.id),
                    "external_ids": g.external_ids,
                    "game_date": g.game_date.isoformat() if g.game_date else None,
                    "missing": ["stats"],
                })
                game_ids_seen.add(g.id)

    if missing in ("pbp", "both"):
        for g in get_games_without_pbp(db, source, limit):
            if g.id in game_ids_seen:
                # Already in list, add 'pbp' to missing
                for game in games:
                    if game["id"] == str(g.id):
                        game["missing"].append("pbp")
                        break
            else:
                games.append({
                    "id": str(g.id),
                    "external_ids": g.external_ids,
                    "game_date": g.game_date.isoformat() if g.game_date else None,
                    "missing": ["pbp"],
                })
                game_ids_seen.add(g.id)

    return {
        "count": len(games),
        "source": source,
        "games": games[:limit],
    }


@router.post(
    "/resync/players",
    response_model=SyncLogResponse,
    summary="Resync Incomplete Players",
    description="Resync players with missing bio data from the source.",
)
async def resync_incomplete_players(
    source: str = Query(
        ...,
        description="Data source to resync from (e.g., 'winner', 'euroleague')",
    ),
    season_id: str = Query(
        ...,
        description="Season identifier for roster lookup (e.g., '2024-25')",
    ),
    db: Session = Depends(get_db),
) -> SyncLogResponse:
    """
    Resync players with missing bio data.

    Fetches fresh player data from the source for players missing
    height, birth_date, or positions. Uses roster data to match
    players and update their bio information.

    Args:
        source: Data source name.
        season_id: Season identifier for roster lookup.
        db: Database session (injected).

    Returns:
        SyncLogResponse with resync operation results.

    Raises:
        HTTPException: If source is not found or season doesn't exist.

    Example:
        >>> response = client.post(
        ...     "/api/v1/sync/resync/players",
        ...     params={"source": "winner", "season_id": "2024-25"}
        ... )
    """
    manager = _get_sync_manager(db)

    # Find internal season by name
    stmt = select(Season).where(Season.name == season_id)
    season = db.scalars(stmt).first()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {season_id} not found")

    try:
        sync_log = await manager.sync_all_player_bios(
            source=source,
            season_id=season.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resync failed: {e}")

    return SyncLogResponse(
        id=sync_log.id,
        source=sync_log.source,
        entity_type=sync_log.entity_type,
        status=SyncStatus(sync_log.status),
        season_id=sync_log.season_id,
        season_name=sync_log.season.name if sync_log.season else None,
        game_id=sync_log.game_id,
        records_processed=sync_log.records_processed,
        records_created=sync_log.records_created,
        records_updated=sync_log.records_updated,
        records_skipped=sync_log.records_skipped,
        error_message=sync_log.error_message,
        error_details=sync_log.error_details,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
    )


@router.post(
    "/resync/games",
    summary="Resync Incomplete Games",
    description="Resync games with missing stats or play-by-play data.",
)
async def resync_incomplete_games(
    source: str = Query(
        ...,
        description="Data source to resync from",
    ),
    include_stats: bool = Query(
        default=True,
        description="Resync games missing boxscore stats",
    ),
    include_pbp: bool = Query(
        default=True,
        description="Resync games missing play-by-play data",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of games to resync",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Resync games with missing data.

    Fetches fresh game data from the source for games missing
    boxscore stats or play-by-play events.

    Args:
        source: Data source name.
        include_stats: Whether to resync missing boxscore stats.
        include_pbp: Whether to resync missing play-by-play.
        limit: Maximum number of games to resync.
        db: Database session (injected).

    Returns:
        Dict with resync operation summary.

    Example:
        >>> response = client.post(
        ...     "/api/v1/sync/resync/games",
        ...     params={"source": "winner", "include_stats": True}
        ... )
    """
    from src.sync.completeness import get_games_without_pbp, get_games_without_stats

    manager = _get_sync_manager(db)
    results = {
        "source": source,
        "games_processed": 0,
        "games_synced": 0,
        "games_failed": 0,
        "errors": [],
    }

    # Get games that need resyncing
    games_to_sync = set()

    if include_stats:
        for game in get_games_without_stats(db, source, limit):
            games_to_sync.add(game)

    if include_pbp:
        for game in get_games_without_pbp(db, source, limit):
            games_to_sync.add(game)

    # Sync each game
    for game in list(games_to_sync)[:limit]:
        results["games_processed"] += 1
        try:
            # Get external ID for this source
            external_id = game.external_ids.get(source)
            if not external_id:
                results["games_failed"] += 1
                results["errors"].append(f"Game {game.id}: no {source} external_id")
                continue

            await manager.sync_game(
                source=source,
                game_external_id=external_id,
                include_pbp=include_pbp,
            )
            results["games_synced"] += 1
        except Exception as e:
            results["games_failed"] += 1
            results["errors"].append(f"Game {game.id}: {e!s}")

    return results


@router.post(
    "/historical",
    response_model=SyncLogResponse,
    summary="Sync Historical Season",
    description="Sync all games from a historical season.",
)
async def sync_historical_season(
    source: str = Query(
        ...,
        description="Data source (e.g., 'winner', 'euroleague')",
    ),
    season: str = Query(
        ...,
        description="Season identifier (e.g., '2023-24')",
    ),
    include_boxscores: bool = Query(  # noqa: ARG001  # Reserved for future use
        default=True,
        description="Whether to sync boxscore data",
    ),
    include_pbp: bool = Query(
        default=True,
        description="Whether to sync play-by-play data",
    ),
    db: Session = Depends(get_db),
) -> SyncLogResponse:
    """
    Sync all games from a historical season.

    This endpoint syncs all final games from a specified season,
    including boxscore and optionally play-by-play data. Use this
    for initial setup or backfilling historical data.

    Args:
        source: Data source name.
        season: Season identifier.
        include_boxscores: Whether to sync boxscore data.
        include_pbp: Whether to sync play-by-play data.
        db: Database session (injected).

    Returns:
        SyncLogResponse with sync operation results.

    Example:
        >>> response = client.post(
        ...     "/api/v1/sync/historical",
        ...     params={"source": "euroleague", "season": "2023-24"}
        ... )
    """
    manager = _get_sync_manager(db)

    try:
        # Use the existing sync_season method
        sync_log = await manager.sync_season(
            source=source,
            season_external_id=season,
            include_pbp=include_pbp,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Historical sync failed: {e}")

    return SyncLogResponse(
        id=sync_log.id,
        source=sync_log.source,
        entity_type=sync_log.entity_type,
        status=SyncStatus(sync_log.status),
        season_id=sync_log.season_id,
        season_name=sync_log.season.name if sync_log.season else None,
        game_id=sync_log.game_id,
        records_processed=sync_log.records_processed,
        records_created=sync_log.records_created,
        records_updated=sync_log.records_updated,
        records_skipped=sync_log.records_skipped,
        error_message=sync_log.error_message,
        error_details=sync_log.error_details,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
    )


@router.post(
    "/recent",
    response_model=SyncLogResponse,
    summary="Sync Recent Games",
    description="Sync games from the last N days.",
)
async def sync_recent_games(
    source: str = Query(
        ...,
        description="Data source (e.g., 'winner', 'euroleague')",
    ),
    days: int = Query(
        default=7,
        ge=1,
        le=90,
        description="Number of days to look back",
    ),
    include_pbp: bool = Query(
        default=True,
        description="Whether to sync play-by-play data",
    ),
    db: Session = Depends(get_db),
) -> SyncLogResponse:
    """
    Sync games from the last N days.

    This endpoint syncs recent games that haven't been synced yet.
    Useful for daily sync jobs to keep data up-to-date.

    Args:
        source: Data source name.
        days: Number of days to look back (default 7, max 90).
        include_pbp: Whether to sync play-by-play data.
        db: Database session (injected).

    Returns:
        SyncLogResponse with sync operation results.

    Example:
        >>> response = client.post(
        ...     "/api/v1/sync/recent",
        ...     params={"source": "winner", "days": 7}
        ... )
    """
    manager = _get_sync_manager(db)

    try:
        sync_log = await manager.sync_recent(
            source=source,
            days=days,
            include_pbp=include_pbp,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recent sync failed: {e}")

    return SyncLogResponse(
        id=sync_log.id,
        source=sync_log.source,
        entity_type=sync_log.entity_type,
        status=SyncStatus(sync_log.status),
        season_id=sync_log.season_id,
        season_name=sync_log.season.name if sync_log.season else None,
        game_id=sync_log.game_id,
        records_processed=sync_log.records_processed,
        records_created=sync_log.records_created,
        records_updated=sync_log.records_updated,
        records_skipped=sync_log.records_skipped,
        error_message=sync_log.error_message,
        error_details=sync_log.error_details,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
    )


@router.get(
    "/available-seasons",
    summary="Get Available Seasons",
    description="Get list of available seasons for a data source.",
)
async def get_available_seasons(
    source: str = Query(
        ...,
        description="Data source (e.g., 'winner', 'euroleague')",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get list of available seasons for sync.

    Returns the season identifiers that can be used with
    historical sync operations.

    Args:
        source: Data source name.
        db: Database session (injected).

    Returns:
        Dict with list of available season names.

    Example:
        >>> response = client.get("/api/v1/sync/available-seasons?source=euroleague")
        >>> data = response.json()
        >>> print(data["seasons"])
        ["2024-25", "2023-24", "2022-23"]
    """
    manager = _get_sync_manager(db)

    try:
        adapter = manager._get_adapter(source)
        seasons = await adapter.get_available_seasons()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get seasons: {e}")

    return {
        "source": source,
        "seasons": seasons,
    }
