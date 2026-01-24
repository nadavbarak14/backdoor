"""
Sync Log Model Module

Provides the SQLAlchemy ORM model for tracking data synchronization
operations in the Basketball Analytics Platform.

This module exports:
    - SyncLog: Tracks data sync operations from external sources

Usage:
    from src.models.sync import SyncLog

    sync_log = SyncLog(
        source="winner",
        entity_type="games",
        status="STARTED",
        season_id=season.id,
    )

The SyncLog model is essential for tracking ETL operations, debugging
sync issues, and ensuring data integrity when importing from external
data providers.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin


class SyncLog(UUIDMixin, Base):
    """
    Tracks data synchronization operations from external sources.

    Records the details and status of each sync operation, including
    which source and entity type was synced, how many records were
    processed, and any errors encountered.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        source: External data source (e.g., "winner", "euroleague")
        entity_type: Type of entity being synced (e.g., "games", "players", "stats", "pbp")
        status: Sync status (STARTED, COMPLETED, FAILED, PARTIAL)
        season_id: Optional UUID foreign key to Season being synced
        game_id: Optional UUID foreign key to Game being synced
        records_processed: Total number of records processed
        records_created: Number of new records created
        records_updated: Number of existing records updated
        records_skipped: Number of records skipped (e.g., duplicates)
        error_message: Human-readable error message if sync failed
        error_details: JSON object with detailed error information
        started_at: Timestamp when sync operation started
        completed_at: Timestamp when sync operation completed (or failed)

    Relationships:
        season: Optional Season that was synced
        game: Optional Game that was synced

    Example:
        >>> # Start a sync operation
        >>> sync_log = SyncLog(
        ...     source="winner",
        ...     entity_type="games",
        ...     status="STARTED",
        ...     season_id=season.id,
        ... )
        >>> session.add(sync_log)
        >>> session.commit()
        >>>
        >>> # Update when complete
        >>> sync_log.status = "COMPLETED"
        >>> sync_log.records_processed = 100
        >>> sync_log.records_created = 95
        >>> sync_log.records_updated = 5
        >>> sync_log.completed_at = datetime.now(UTC)
        >>> session.commit()
    """

    __tablename__ = "sync_logs"

    # Source and type identification
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="STARTED")

    # Optional context foreign keys
    season_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL"),
        nullable=True,
    )
    game_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Record counts
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    season: Mapped["Season | None"] = relationship("Season", back_populates="sync_logs")
    game: Mapped["Game | None"] = relationship("Game", back_populates="sync_logs")

    __table_args__ = (
        Index("ix_sync_logs_source_entity_started", "source", "entity_type", "started_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of SyncLog."""
        return (
            f"<SyncLog(id='{self.id}', source='{self.source}', "
            f"entity_type='{self.entity_type}', status='{self.status}')>"
        )


if TYPE_CHECKING:
    from src.models.game import Game
    from src.models.league import Season
