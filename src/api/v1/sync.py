"""
Sync Router Module

FastAPI router for data synchronization endpoints.
Provides endpoints for viewing sync history, triggering syncs,
and checking sync status.

Endpoints:
    GET /sync/logs - Get sync operation history with filters
    GET /sync/status - Get current sync status for all sources
    POST /sync/{source}/season/{season_id} - Trigger sync for a season
    POST /sync/{source}/game/{game_id} - Trigger sync for a single game
    POST /sync/{source}/teams/{season_id} - Sync team rosters for a season

Usage:
    from src.api.v1.sync import router

    app.include_router(router, prefix="/api/v1")
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core import get_db
from src.schemas import (
    SyncLogFilter,
    SyncLogListResponse,
    SyncLogResponse,
    SyncStatus,
)
from src.schemas.sync import (
    SyncSourceStatus,
    SyncStatusResponse,
)
from src.services import SyncLogService
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
    from src.sync.winner import WinnerClient, WinnerScraper
    from src.sync.winner.adapter import WinnerAdapter
    from src.sync.winner.mapper import WinnerMapper

    # Initialize Winner adapter
    client = WinnerClient(db)
    scraper = WinnerScraper(db)
    mapper = WinnerMapper()
    winner_adapter = WinnerAdapter(client, scraper, mapper)

    # Create config
    config = SyncConfig.from_settings()

    # Create manager
    return SyncManager(
        db=db,
        adapters={"winner": winner_adapter},
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
