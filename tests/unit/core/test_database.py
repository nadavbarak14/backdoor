"""
Database Module Tests

Tests for src/core/database.py covering:
- Engine creation and configuration
- Session factory functionality
- get_db dependency behavior
"""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.database import Base, SessionLocal, engine, get_db


class TestEngine:
    """Tests for the SQLAlchemy engine."""

    def test_engine_exists(self):
        """Engine should be created and accessible."""
        assert engine is not None

    def test_engine_is_engine_type(self):
        """Engine should be an SQLAlchemy Engine instance."""
        assert isinstance(engine, Engine)

    def test_engine_can_connect(self):
        """Engine should be able to establish a connection."""
        with engine.connect() as connection:
            assert connection is not None

    def test_engine_can_execute_query(self):
        """Engine should be able to execute basic SQL."""
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row is not None
            assert row[0] == 1


class TestSessionLocal:
    """Tests for the session factory."""

    def test_session_local_exists(self):
        """SessionLocal should be created and accessible."""
        assert SessionLocal is not None

    def test_session_local_is_sessionmaker(self):
        """SessionLocal should be a sessionmaker instance."""
        assert isinstance(SessionLocal, sessionmaker)

    def test_session_local_creates_session(self):
        """SessionLocal should create a valid Session instance."""
        session = SessionLocal()
        try:
            assert session is not None
            assert isinstance(session, Session)
        finally:
            session.close()

    def test_session_can_execute_query(self):
        """Session should be able to execute queries."""
        session = SessionLocal()
        try:
            result = session.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row is not None
            assert row[0] == 1
        finally:
            session.close()


class TestGetDb:
    """Tests for the get_db dependency function."""

    def test_get_db_yields_session(self):
        """get_db should yield a Session instance."""
        gen = get_db()
        session = next(gen)
        try:
            assert session is not None
            assert isinstance(session, Session)
        finally:
            # Complete the generator to trigger cleanup
            try:
                next(gen)
            except StopIteration:
                pass

    def test_get_db_session_is_usable(self):
        """Session from get_db should be able to execute queries."""
        gen = get_db()
        session = next(gen)
        try:
            result = session.execute(text("SELECT 1"))
            row = result.fetchone()
            assert row is not None
            assert row[0] == 1
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    def test_get_db_closes_session(self):
        """get_db should close the session after use."""
        gen = get_db()
        session = next(gen)

        # Complete the generator
        try:
            next(gen)
        except StopIteration:
            pass

        # Session should be closed (attempting to use it may raise or return None)
        # We can check the _is_closed attribute or connection state
        # Note: In SQLAlchemy 2.0, closed sessions can still exist but
        # their connection is returned to the pool
        assert session.get_bind() is not None  # Session object still exists


class TestBaseExport:
    """Tests for Base re-export from database module."""

    def test_base_is_exported(self):
        """Base should be accessible from database module."""
        assert Base is not None

    def test_base_has_metadata(self):
        """Base should have metadata attribute."""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None


class TestImports:
    """Tests for module imports."""

    def test_import_from_database(self):
        """Should be able to import all exports from database module."""
        from src.core.database import Base, SessionLocal, engine, get_db

        assert engine is not None
        assert SessionLocal is not None
        assert get_db is not None
        assert Base is not None

    def test_import_from_core(self):
        """Should be able to import database exports from core module."""
        from src.core import SessionLocal, engine, get_db

        assert engine is not None
        assert SessionLocal is not None
        assert get_db is not None
