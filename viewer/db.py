"""
Database Session Management for Viewer

Provides database session handling optimized for Streamlit's execution model.

Streamlit reruns the entire script on each interaction, so we need a clean
session for each page render. This module provides a context manager that
ensures proper session lifecycle.

Usage:
    from viewer.db import get_session

    with get_session() as session:
        teams = session.query(Team).all()
        # session auto-closes after block

Note:
    For cached functions, convert SQLAlchemy objects to dicts before
    returning, as SQLAlchemy objects cannot be cached by Streamlit.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from src.core.database import SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager that yields a database session.

    Creates a new SQLAlchemy session and ensures it is properly closed
    after the context block, regardless of success or failure.

    Yields:
        Session: SQLAlchemy session for database operations.

    Example:
        >>> with get_session() as session:
        ...     players = session.query(Player).all()
        ...     return [{"id": str(p.id), "name": p.name} for p in players]

    Note:
        Always convert SQLAlchemy objects to dicts within the context
        block if the data needs to be used outside or cached.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


__all__ = ["get_session"]
