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
        if self.completed_at is None or self.started_at is None:
            return None
        # Handle timezone-naive vs timezone-aware datetime comparison
        completed = self.completed_at
        started = self.started_at
        # Remove timezone info for comparison if one is naive
        if completed.tzinfo is not None and started.tzinfo is None:
            completed = completed.replace(tzinfo=None)
        elif completed.tzinfo is None and started.tzinfo is not None:
            started = started.replace(tzinfo=None)
        delta = completed - started
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


class SeasonSyncCoverage(BaseModel):
    """
    Schema for sync coverage statistics of a single season.

    Shows what percentage of data has been synced for a season,
    enabling identification of missing data for incremental syncs.

    Attributes:
        season_id: UUID of the season.
        season_name: Name of the season (e.g., "2024-25").
        league_name: Name of the league.
        games_total: Total number of FINAL games.
        games_with_boxscore: Games that have box score data.
        games_with_pbp: Games that have play-by-play data.
        players_total: Total unique players in the season.
        players_with_bio: Players with position or height data.
        boxscore_pct: Percentage of games with box score.
        pbp_pct: Percentage of games with play-by-play.
        bio_pct: Percentage of players with bio data.

    Example:
        >>> coverage = SeasonSyncCoverage(
        ...     season_id=uuid4(),
        ...     season_name="2024-25",
        ...     league_name="Winner League",
        ...     games_total=104,
        ...     games_with_boxscore=104,
        ...     games_with_pbp=100,
        ...     players_total=232,
        ...     players_with_bio=200,
        ...     boxscore_pct=100.0,
        ...     pbp_pct=96.2,
        ...     bio_pct=86.2,
        ... )
    """

    season_id: uuid.UUID = Field(description="UUID of the season")
    season_name: str = Field(description="Season name (e.g., '2024-25')")
    league_name: str = Field(description="League name")
    games_total: int = Field(description="Total FINAL games in season")
    games_with_boxscore: int = Field(description="Games with PlayerGameStats")
    games_with_pbp: int = Field(description="Games with PlayByPlayEvent")
    players_total: int = Field(description="Unique players in season")
    players_with_bio: int = Field(description="Players with position or height")
    boxscore_pct: float = Field(description="Percentage of games with boxscore")
    pbp_pct: float = Field(description="Percentage of games with PBP")
    bio_pct: float = Field(description="Percentage of players with bio")


class SyncCoverageResponse(BaseModel):
    """
    Schema for sync coverage response across all seasons.

    Provides a comprehensive view of sync coverage to identify
    what data needs to be synced.

    Attributes:
        seasons: List of per-season sync coverage statistics.
        total_games: Total games across all seasons.
        total_games_with_boxscore: Total games with box score data.
        total_games_with_pbp: Total games with play-by-play data.

    Example:
        >>> response = SyncCoverageResponse(
        ...     seasons=[coverage1, coverage2],
        ...     total_games=500,
        ...     total_games_with_boxscore=495,
        ...     total_games_with_pbp=400,
        ... )
    """

    seasons: list[SeasonSyncCoverage] = Field(
        description="Per-season sync coverage statistics"
    )
    total_games: int = Field(description="Total games across all seasons")
    total_games_with_boxscore: int = Field(description="Total games with boxscore")
    total_games_with_pbp: int = Field(description="Total games with PBP")
