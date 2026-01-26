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


class SyncTriggerRequest(BaseModel):
    """
    Schema for triggering a sync operation.

    Attributes:
        include_pbp: Whether to sync play-by-play data.

    Example:
        >>> request = SyncTriggerRequest(include_pbp=True)
    """

    include_pbp: bool = Field(default=True, description="Include play-by-play data")


class SyncSourceStatus(BaseModel):
    """
    Schema for sync status of a single source.

    Attributes:
        name: Source name (e.g., "winner", "euroleague").
        enabled: Whether the source is enabled.
        auto_sync_enabled: Whether auto-sync is enabled.
        sync_interval_minutes: Interval for auto-sync in minutes.
        running_syncs: Number of currently running syncs.
        latest_season_sync: Info about the latest season sync.
        latest_game_sync: Info about the latest game sync.

    Example:
        >>> status = SyncSourceStatus(
        ...     name="winner",
        ...     enabled=True,
        ...     auto_sync_enabled=False,
        ...     sync_interval_minutes=60,
        ...     running_syncs=0
        ... )
    """

    name: str
    enabled: bool
    auto_sync_enabled: bool = False
    sync_interval_minutes: int = 60
    running_syncs: int = 0
    latest_season_sync: dict[str, Any] | None = None
    latest_game_sync: dict[str, Any] | None = None


class SyncStatusResponse(BaseModel):
    """
    Schema for overall sync status response.

    Attributes:
        sources: List of source status objects.
        total_running_syncs: Total number of running syncs across all sources.

    Example:
        >>> response = SyncStatusResponse(
        ...     sources=[SyncSourceStatus(name="winner", enabled=True)],
        ...     total_running_syncs=0
        ... )
    """

    sources: list[SyncSourceStatus]
    total_running_syncs: int = 0


class SyncProgressEvent(BaseModel):
    """
    Schema for a sync progress event in SSE streaming.

    Used for real-time progress reporting during season syncs.

    Attributes:
        event: Type of event (start, progress, synced, error, complete).
        phase: Current sync phase (teams, games).
        current: Current game index (1-indexed).
        total: Total number of games to sync.
        game_id: External ID of the current game.
        status: Status of the current operation (syncing, synced, error).
        error: Error message if status is error.
        sync_log: Final sync log summary (only for complete event).

    Example:
        >>> event = SyncProgressEvent(
        ...     event="progress",
        ...     phase="games",
        ...     current=5,
        ...     total=120,
        ...     game_id="12345",
        ...     status="syncing"
        ... )
    """

    event: str = Field(
        description="Event type: start, progress, synced, error, complete"
    )
    phase: str | None = Field(default=None, description="Current phase: teams, games")
    current: int | None = Field(
        default=None, description="Current game index (1-indexed)"
    )
    total: int | None = Field(default=None, description="Total games to sync")
    game_id: str | None = Field(default=None, description="External game ID")
    status: str | None = Field(default=None, description="Operation status")
    error: str | None = Field(default=None, description="Error message if failed")
    sync_log: dict[str, Any] | None = Field(
        default=None, description="Final sync log summary"
    )
