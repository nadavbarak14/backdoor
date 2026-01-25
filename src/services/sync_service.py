"""
Sync Log Service Module

Provides business logic for tracking data synchronization operations
in the Basketball Analytics Platform.

This module exports:
    - SyncLogService: Track and query sync operations

Usage:
    from src.services.sync_service import SyncLogService

    service = SyncLogService(db_session)

    # Start a sync operation
    sync = service.start_sync(source="winner", entity_type="games", season_id=season_id)

    # Complete the sync
    service.complete_sync(sync.id, records_processed=100, records_created=95)

    # Or mark as failed
    service.fail_sync(sync.id, error_message="API timeout")

The service tracks ETL operations for debugging, monitoring, and
ensuring data integrity when importing from external providers.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from src.models.sync import SyncLog
from src.schemas.sync import SyncLogFilter
from src.services.base import BaseService


class SyncLogService(BaseService[SyncLog]):
    """
    Service for sync log tracking operations.

    Extends BaseService with sync-specific methods for starting,
    completing, and querying synchronization operations.

    Attributes:
        db: SQLAlchemy Session for database operations.
        model: The SyncLog model class.

    Example:
        >>> service = SyncLogService(db_session)
        >>> sync = service.start_sync("winner", "games", season_id=season_uuid)
        >>> # ... perform sync ...
        >>> service.complete_sync(sync.id, 100, 95, 5, 0)
    """

    def __init__(self, db: Session) -> None:
        """
        Initialize the sync log service.

        Args:
            db: SQLAlchemy database session.

        Example:
            >>> service = SyncLogService(db_session)
        """
        super().__init__(db, SyncLog)

    def start_sync(
        self,
        source: str,
        entity_type: str,
        season_id: UUID | None = None,
        game_id: UUID | None = None,
    ) -> SyncLog:
        """
        Create a new sync log entry with STARTED status.

        Call this at the beginning of a sync operation to track its progress.

        Args:
            source: External data source (e.g., "winner", "euroleague").
            entity_type: Type of entity being synced (e.g., "games", "players", "stats").
            season_id: Optional UUID of the season being synced.
            game_id: Optional UUID of the game being synced.

        Returns:
            The newly created SyncLog with STARTED status.

        Example:
            >>> sync = service.start_sync(
            ...     source="winner",
            ...     entity_type="games",
            ...     season_id=season_uuid
            ... )
            >>> print(f"Started sync: {sync.id}")
        """
        sync = SyncLog(
            source=source,
            entity_type=entity_type,
            status="STARTED",
            season_id=season_id,
            game_id=game_id,
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_skipped=0,
            started_at=datetime.now(UTC),
        )
        self.db.add(sync)
        self.db.commit()
        self.db.refresh(sync)
        return sync

    def complete_sync(
        self,
        sync_id: UUID,
        records_processed: int,
        records_created: int,
        records_updated: int,
        records_skipped: int = 0,
    ) -> SyncLog | None:
        """
        Mark sync as COMPLETED with metrics.

        Call this when a sync operation finishes successfully.

        Args:
            sync_id: UUID of the sync log to update.
            records_processed: Total number of records processed.
            records_created: Number of new records created.
            records_updated: Number of existing records updated.
            records_skipped: Number of records skipped (e.g., duplicates).

        Returns:
            The updated SyncLog if found, None otherwise.

        Example:
            >>> sync = service.complete_sync(
            ...     sync_id=sync.id,
            ...     records_processed=100,
            ...     records_created=95,
            ...     records_updated=5,
            ...     records_skipped=0
            ... )
            >>> print(f"Sync completed in {sync.completed_at - sync.started_at}")
        """
        sync = self.get_by_id(sync_id)
        if sync is None:
            return None

        sync.status = "COMPLETED"
        sync.records_processed = records_processed
        sync.records_created = records_created
        sync.records_updated = records_updated
        sync.records_skipped = records_skipped
        sync.completed_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(sync)
        return sync

    def partial_sync(
        self,
        sync_id: UUID,
        records_processed: int,
        records_created: int,
        records_updated: int,
        records_skipped: int,
        error_message: str | None = None,
    ) -> SyncLog | None:
        """
        Mark sync as PARTIAL (completed with some records skipped/failed).

        Call this when a sync completes but with some records unable to be processed.

        Args:
            sync_id: UUID of the sync log to update.
            records_processed: Total number of records processed.
            records_created: Number of new records created.
            records_updated: Number of existing records updated.
            records_skipped: Number of records skipped.
            error_message: Optional message about why records were skipped.

        Returns:
            The updated SyncLog if found, None otherwise.

        Example:
            >>> sync = service.partial_sync(
            ...     sync_id=sync.id,
            ...     records_processed=100,
            ...     records_created=90,
            ...     records_updated=5,
            ...     records_skipped=5,
            ...     error_message="5 records had invalid data"
            ... )
        """
        sync = self.get_by_id(sync_id)
        if sync is None:
            return None

        sync.status = "PARTIAL"
        sync.records_processed = records_processed
        sync.records_created = records_created
        sync.records_updated = records_updated
        sync.records_skipped = records_skipped
        sync.error_message = error_message
        sync.completed_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(sync)
        return sync

    def fail_sync(
        self,
        sync_id: UUID,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ) -> SyncLog | None:
        """
        Mark sync as FAILED with error info.

        Call this when a sync operation encounters an error.

        Args:
            sync_id: UUID of the sync log to update.
            error_message: Human-readable error message.
            error_details: Optional dictionary with detailed error information
                (e.g., stack trace, failed record IDs).

        Returns:
            The updated SyncLog if found, None otherwise.

        Example:
            >>> sync = service.fail_sync(
            ...     sync_id=sync.id,
            ...     error_message="API connection timeout",
            ...     error_details={"endpoint": "/api/games", "timeout": 30}
            ... )
        """
        sync = self.get_by_id(sync_id)
        if sync is None:
            return None

        sync.status = "FAILED"
        sync.error_message = error_message
        sync.error_details = error_details
        sync.completed_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(sync)
        return sync

    def get_latest_by_source(
        self,
        source: str,
        entity_type: str,
    ) -> SyncLog | None:
        """
        Get most recent sync for a source/entity combination.

        Useful for checking when the last sync occurred and its status.

        Args:
            source: External data source (e.g., "winner").
            entity_type: Type of entity (e.g., "games").

        Returns:
            Most recent SyncLog if found, None otherwise.

        Example:
            >>> latest = service.get_latest_by_source("winner", "games")
            >>> if latest:
            ...     print(f"Last sync: {latest.started_at}, status: {latest.status}")
        """
        stmt = (
            select(SyncLog)
            .options(
                joinedload(SyncLog.season),
                joinedload(SyncLog.game),
            )
            .where(
                SyncLog.source == source,
                SyncLog.entity_type == entity_type,
            )
            .order_by(desc(SyncLog.started_at))
            .limit(1)
        )
        return self.db.scalars(stmt).unique().first()

    def get_latest_successful(
        self,
        source: str,
        entity_type: str,
        season_id: UUID | None = None,
    ) -> SyncLog | None:
        """
        Get most recent successful sync for a source/entity combination.

        Useful for incremental syncing to find the last successful checkpoint.

        Args:
            source: External data source.
            entity_type: Type of entity.
            season_id: Optional season to filter by.

        Returns:
            Most recent successful SyncLog if found, None otherwise.

        Example:
            >>> last_success = service.get_latest_successful("winner", "games")
            >>> if last_success:
            ...     print(f"Last successful sync: {last_success.completed_at}")
        """
        stmt = select(SyncLog).where(
            SyncLog.source == source,
            SyncLog.entity_type == entity_type,
            SyncLog.status == "COMPLETED",
        )

        if season_id:
            stmt = stmt.where(SyncLog.season_id == season_id)

        stmt = stmt.order_by(desc(SyncLog.completed_at)).limit(1)
        return self.db.scalars(stmt).first()

    def get_filtered(
        self,
        filter_params: SyncLogFilter,
    ) -> tuple[list[SyncLog], int]:
        """
        Filter sync logs with pagination.

        Args:
            filter_params: SyncLogFilter with filter criteria and pagination.

        Returns:
            Tuple of (list of SyncLogs for current page, total count).

        Example:
            >>> filter = SyncLogFilter(source="winner", status=SyncStatus.FAILED)
            >>> logs, total = service.get_filtered(filter)
            >>> print(f"Found {total} failed syncs")
        """
        stmt = select(SyncLog).options(
            joinedload(SyncLog.season),
            joinedload(SyncLog.game),
        )

        # Apply filters
        if filter_params.source:
            stmt = stmt.where(SyncLog.source == filter_params.source)

        if filter_params.entity_type:
            stmt = stmt.where(SyncLog.entity_type == filter_params.entity_type)

        if filter_params.status:
            stmt = stmt.where(SyncLog.status == filter_params.status.value)

        if filter_params.season_id:
            stmt = stmt.where(SyncLog.season_id == filter_params.season_id)

        if filter_params.start_date:
            stmt = stmt.where(SyncLog.started_at >= filter_params.start_date)

        if filter_params.end_date:
            stmt = stmt.where(SyncLog.started_at <= filter_params.end_date)

        # Count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar() or 0

        # Order and paginate
        skip = (filter_params.page - 1) * filter_params.page_size
        stmt = stmt.order_by(desc(SyncLog.started_at))
        stmt = stmt.offset(skip).limit(filter_params.page_size)

        logs = list(self.db.scalars(stmt).unique().all())
        return logs, total

    def get_running_syncs(self, source: str | None = None) -> list[SyncLog]:
        """
        Get all currently running (STARTED) sync operations.

        Useful for checking if there are any in-progress syncs before
        starting a new one to avoid conflicts.

        Args:
            source: Optional source to filter by.

        Returns:
            List of SyncLogs with STARTED status.

        Example:
            >>> running = service.get_running_syncs("winner")
            >>> if running:
            ...     print(f"Warning: {len(running)} syncs already running")
        """
        stmt = select(SyncLog).where(SyncLog.status == "STARTED")

        if source:
            stmt = stmt.where(SyncLog.source == source)

        stmt = stmt.order_by(SyncLog.started_at)
        return list(self.db.scalars(stmt).all())
