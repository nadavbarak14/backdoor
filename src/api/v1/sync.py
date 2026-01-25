"""
Sync Router Module

FastAPI router for data synchronization tracking endpoints.
Provides endpoints for viewing sync operation history and status.

Endpoints:
    GET /sync/logs - Get sync operation history with filters

Usage:
    from src.api.v1.sync import router

    app.include_router(router, prefix="/api/v1")
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core import get_db
from src.schemas import (
    SyncLogFilter,
    SyncLogListResponse,
    SyncLogResponse,
    SyncStatus,
)
from src.services import SyncLogService

router = APIRouter(prefix="/sync", tags=["Sync"])


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
