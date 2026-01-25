"""
Sync Schema Module

Pydantic schemas for data synchronization tracking:
- SyncStatus: Enum for sync operation status
- SyncLogResponse: Full sync log entry with computed duration
- SyncLogListResponse: Paginated list of sync logs
- SyncLogFilter: Filter for querying sync logs

Usage:
    from src.schemas.sync import (
        SyncStatus,
        SyncLogResponse,
        SyncLogListResponse,
        SyncLogFilter,
    )

    @router.get("/sync/logs")
    def list_sync_logs(filter: SyncLogFilter) -> SyncLogListResponse:
        ...
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field

from src.schemas.base import OrmBase


class SyncStatus(str, Enum):
    """
    Status of a sync operation.

    Attributes:
        STARTED: Sync operation has begun.
        COMPLETED: Sync operation finished successfully.
        FAILED: Sync operation encountered an error.
        PARTIAL: Sync operation completed with some records skipped.
    """

    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class SyncLogResponse(OrmBase):
    """
    Schema for sync log entry response.

    Contains full details of a sync operation including computed duration.

    Attributes:
        id: Unique sync log identifier.
        source: External data source (e.g., "winner", "euroleague").
        entity_type: Type of entity synced (e.g., "games", "players", "stats", "pbp").
        status: Current status of the sync operation.
        season_id: Optional UUID of the season being synced.
        season_name: Optional name of the season being synced.
        game_id: Optional UUID of the game being synced.
        records_processed: Total number of records processed.
        records_created: Number of new records created.
        records_updated: Number of existing records updated.
        records_skipped: Number of records skipped.
        error_message: Human-readable error message if failed.
        error_details: Detailed error information as JSON.
        started_at: Timestamp when sync started.
        completed_at: Timestamp when sync completed (or failed).

    Computed Fields:
        duration_seconds: Time elapsed in seconds (None if still running).

    Example:
        >>> log = SyncLogResponse(
        ...     id=uuid4(),
        ...     source="winner",
        ...     entity_type="games",
        ...     status=SyncStatus.COMPLETED,
        ...     records_processed=100,
        ...     records_created=95,
        ...     records_updated=5,
        ...     records_skipped=0,
        ...     started_at=datetime(2024, 1, 15, 10, 0, 0),
        ...     completed_at=datetime(2024, 1, 15, 10, 5, 30),
        ... )
        >>> print(log.duration_seconds)
        330.0
    """

    id: uuid.UUID
    source: str
    entity_type: str
    status: SyncStatus

    # Optional context
    season_id: uuid.UUID | None = None
    season_name: str | None = None
    game_id: uuid.UUID | None = None

    # Record counts
    records_processed: int
    records_created: int
    records_updated: int
    records_skipped: int

    # Error tracking
    error_message: str | None = None
    error_details: dict[str, Any] | None = None

    # Timestamps
    started_at: datetime
    completed_at: datetime | None = None

    @computed_field
    @property
    def duration_seconds(self) -> float | None:
        """
        Compute duration in seconds.

        Returns None if sync is still in progress (no completed_at).
        """
        if self.completed_at is None:
            return None
        delta = self.completed_at - self.started_at
        return delta.total_seconds()


class SyncLogListResponse(BaseModel):
    """
    Schema for paginated sync log list response.

    Attributes:
        items: List of sync log entries for the current page.
        total: Total number of sync logs matching the filter.

    Example:
        >>> response = SyncLogListResponse(
        ...     items=[log1, log2, log3],
        ...     total=150
        ... )
    """

    items: list[SyncLogResponse]
    total: int


class SyncLogFilter(BaseModel):
    """
    Schema for filtering sync log queries.

    All fields are optional. When provided, they filter the results.

    Attributes:
        source: Filter by external data source.
        entity_type: Filter by entity type.
        status: Filter by sync status.
        season_id: Filter by season.
        start_date: Filter logs started on or after this date.
        end_date: Filter logs started on or before this date.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Example:
        >>> filter = SyncLogFilter(
        ...     source="winner",
        ...     status=SyncStatus.FAILED,
        ...     start_date=datetime(2024, 1, 1),
        ...     page=1,
        ...     page_size=20
        ... )
    """

    source: str | None = Field(default=None, description="Filter by data source")
    entity_type: str | None = Field(default=None, description="Filter by entity type")
    status: SyncStatus | None = Field(default=None, description="Filter by status")
    season_id: uuid.UUID | None = Field(default=None, description="Filter by season")
    start_date: datetime | None = Field(
        default=None, description="Filter logs started on or after"
    )
    end_date: datetime | None = Field(
        default=None, description="Filter logs started on or before"
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
