"""
Database Connection Module

Provides SQLAlchemy engine, session management, and FastAPI dependency injection
for the Basketball Analytics Platform.

This module exports:
    - engine: SQLAlchemy engine configured from settings
    - SessionLocal: Session factory for creating database sessions
    - get_db: FastAPI dependency that yields database sessions
    - Base: Re-exported from models for convenient imports

Usage:
    from src.core.database import engine, SessionLocal, get_db, Base

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Use with FastAPI
    @app.get("/items")
    def get_items(db: Session = Depends(get_db)):
        return db.query(Item).all()

The module uses the DATABASE_URL from settings and configures the engine
appropriately for SQLite (with check_same_thread=False for multi-threading).
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings
from src.models.base import Base

# Determine connect_args based on database type
# SQLite requires check_same_thread=False for FastAPI's multi-threaded environment
connect_args: dict[str, Any] = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)
"""
SQLAlchemy engine instance.

Configured from settings.DATABASE_URL with appropriate connection arguments
for the database type. For SQLite, includes check_same_thread=False to
support FastAPI's multi-threaded request handling.
"""

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
"""
Session factory for creating database sessions.

Creates sessions bound to the engine with autocommit and autoflush disabled.
Use this to create sessions manually or through the get_db dependency.

Example:
    >>> session = SessionLocal()
    >>> try:
    ...     # do work
    ...     session.commit()
    ... finally:
    ...     session.close()
"""


def get_db() -> Generator[Session, Any, None]:
    """
    FastAPI dependency that yields a database session.

    Creates a new SQLAlchemy session for each request and ensures it is
    properly closed after the request completes, regardless of success
    or failure.

    Yields:
        Session: SQLAlchemy session for database operations.

    Example:
        >>> from fastapi import Depends
        >>> from sqlalchemy.orm import Session
        >>>
        >>> @app.get("/players")
        >>> def get_players(db: Session = Depends(get_db)):
        ...     return db.query(Player).all()

    Note:
        The session is automatically closed in the finally block,
        ensuring proper resource cleanup even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Re-export Base for convenient imports from database module
__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "Base",
]
