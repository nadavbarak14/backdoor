"""
Base Model Module

Provides the SQLAlchemy declarative base and reusable mixins for all database
models in the Basketball Analytics Platform.

This module exports:
    - Base: The SQLAlchemy DeclarativeBase all models inherit from
    - UUIDMixin: Adds UUID primary key to models
    - TimestampMixin: Adds created_at and updated_at timestamps

Usage:
    from src.models.base import Base, UUIDMixin, TimestampMixin

    class Player(UUIDMixin, TimestampMixin, Base):
        __tablename__ = "players"
        name: Mapped[str] = mapped_column(String(100))

All models should inherit from Base and include both mixins for consistent
primary keys and audit timestamps across the database.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for all models.

    All database models in the application should inherit from this base class.
    It provides the foundation for SQLAlchemy's ORM functionality including
    table mapping and metadata management.

    Attributes:
        metadata: SQLAlchemy MetaData object containing table definitions.
        registry: SQLAlchemy registry for type annotation mappings.

    Example:
        >>> class Player(Base):
        ...     __tablename__ = "players"
        ...     id: Mapped[int] = mapped_column(primary_key=True)
        ...     name: Mapped[str] = mapped_column(String(100))
    """

    pass


class UUIDMixin:
    """
    Mixin that adds a UUID primary key column.

    Provides a universally unique identifier as the primary key for models.
    UUIDs are generated automatically on insert using Python's uuid4.

    Attributes:
        id: UUID primary key, auto-generated on insert.

    Example:
        >>> class Player(UUIDMixin, Base):
        ...     __tablename__ = "players"
        ...     name: Mapped[str]
        ...
        >>> player = Player(name="LeBron James")
        >>> # player.id will be auto-generated as UUID
    """

    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        """
        UUID primary key column.

        Returns:
            Mapped[uuid.UUID]: UUID column configured as primary key with
                auto-generation default.
        """
        return mapped_column(
            primary_key=True,
            default=uuid.uuid4,
            nullable=False,
        )


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp columns.

    Provides automatic audit timestamps for tracking when records are created
    and last modified. Uses server-side defaults where supported.

    Attributes:
        created_at: Timestamp of record creation, set automatically on insert.
        updated_at: Timestamp of last update, updated automatically on change.

    Example:
        >>> class Player(TimestampMixin, Base):
        ...     __tablename__ = "players"
        ...     name: Mapped[str]
        ...
        >>> player = Player(name="Stephen Curry")
        >>> session.add(player)
        >>> session.commit()
        >>> print(player.created_at)  # Automatically set
        >>> player.name = "Stephen Wardell Curry"
        >>> session.commit()
        >>> print(player.updated_at)  # Automatically updated
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """
        Timestamp of record creation.

        Returns:
            Mapped[datetime]: DateTime column with server default to current time.
        """
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """
        Timestamp of last record update.

        Returns:
            Mapped[datetime]: DateTime column with server default and auto-update
                on modification.
        """
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
