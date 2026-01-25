"""
Sync Cache Model

Provides the SyncCache model for storing raw data fetched from external APIs
and scraped HTML pages. This enables checksum-based caching to detect changes
and avoid unnecessary processing.

This module exports:
    - SyncCache: Model for storing raw API responses and HTML content

Usage:
    from src.models.sync_cache import SyncCache

    cache_entry = SyncCache(
        source="winner",
        resource_type="boxscore",
        resource_id="12345",
        raw_data={"teams": [...]},
        content_hash="sha256...",
        fetched_at=datetime.utcnow(),
        http_status=200
    )
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDMixin


class SyncCache(UUIDMixin, TimestampMixin, Base):
    """
    Cache entry for raw data fetched from external sources.

    Stores raw API responses (JSON) and scraped HTML pages for caching
    and change detection. Uses SHA-256 content hashes to efficiently
    detect when data has changed without full comparison.

    Attributes:
        id: UUID primary key (from UUIDMixin).
        source: Data source identifier (e.g., "winner", "nba").
        resource_type: Type of resource (e.g., "games_all", "boxscore", "player_page").
        resource_id: Unique identifier within resource type (e.g., game ID, player ID).
        raw_data: Raw JSON response or {"html": "..."} for HTML content.
        content_hash: SHA-256 hash of raw_data for change detection.
        fetched_at: Timestamp when data was fetched from source.
        http_status: HTTP status code from the fetch request.
        created_at: Record creation timestamp (from TimestampMixin).
        updated_at: Record update timestamp (from TimestampMixin).

    Table:
        sync_cache: Stores cached raw data with unique constraint on
        (source, resource_type, resource_id).

    Example:
        >>> from src.models.sync_cache import SyncCache
        >>> from datetime import datetime
        >>>
        >>> cache = SyncCache(
        ...     source="winner",
        ...     resource_type="boxscore",
        ...     resource_id="12345",
        ...     raw_data={"home_team": {"score": 85}, "away_team": {"score": 78}},
        ...     content_hash="abc123...",
        ...     fetched_at=datetime.utcnow(),
        ...     http_status=200
        ... )
        >>> session.add(cache)
        >>> session.commit()
    """

    __tablename__ = "sync_cache"

    # Source and resource identification
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Data source identifier (e.g., 'winner', 'nba')",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of resource (e.g., 'games_all', 'boxscore', 'player_page')",
    )
    resource_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Unique identifier within resource type",
    )

    # Raw data storage
    raw_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        doc="Raw JSON response or {'html': '...'} for HTML content",
    )

    # Change detection
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hash of raw_data for change detection",
    )

    # Fetch metadata
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Timestamp when data was fetched from source",
    )
    http_status: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="HTTP status code from the fetch request",
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint(
            "source",
            "resource_type",
            "resource_id",
            name="uq_sync_cache_source_type_id",
        ),
        Index("ix_sync_cache_source", "source"),
        Index("ix_sync_cache_source_type", "source", "resource_type"),
        Index("ix_sync_cache_fetched_at", "fetched_at"),
    )

    def __repr__(self) -> str:
        """
        String representation of SyncCache.

        Returns:
            str: Human-readable representation showing source, type, and ID.
        """
        return (
            f"<SyncCache(source='{self.source}', "
            f"resource_type='{self.resource_type}', "
            f"resource_id='{self.resource_id}')>"
        )
