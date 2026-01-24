"""
Pytest configuration and shared fixtures.

This module provides test fixtures for the Basketball Analytics Platform:
- Database fixtures for in-memory SQLite testing
- FastAPI TestClient fixture for API testing

All fixtures use function scope by default to ensure test isolation.

Usage:
    def test_something(test_db, client):
        # test_db is an SQLAlchemy session with auto-rollback
        # client is a FastAPI TestClient
        response = client.get("/health")
        assert response.status_code == 200
"""

from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Database imports
from src.core.database import Base, get_db

# Placeholder app - will be replaced with actual import
try:
    from src.main import app
except ImportError:
    from fastapi import FastAPI

    app = FastAPI(title="Basketball Analytics Platform - Test")


# Test database URL - in-memory SQLite
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    """
    Create a test database engine.

    Uses in-memory SQLite with a static connection pool to ensure
    the same connection is reused across the session.

    Returns:
        Engine: SQLAlchemy engine configured for testing.

    Example:
        >>> def test_engine_works(test_engine):
        ...     assert test_engine is not None
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, Any, None]:
    """
    Create a test database session with automatic rollback.

    Provides an isolated database session for each test. All changes
    made during the test are rolled back after the test completes,
    ensuring test isolation.

    Args:
        test_engine: The test database engine fixture.

    Yields:
        Session: SQLAlchemy session for database operations.

    Example:
        >>> def test_create_player(test_db):
        ...     player = Player(name="Test Player")
        ...     test_db.add(player)
        ...     test_db.commit()
        ...     assert test_db.query(Player).count() == 1
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
    )
    session = TestingSessionLocal()

    # Begin a nested transaction (savepoint)
    nested = connection.begin_nested()

    # Restart the nested transaction on commit
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.begin_nested()

    yield session

    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[Any, Any, None]:
    """
    Create a FastAPI TestClient with test database dependency override.

    Provides a test client configured to use the test database session.
    All API requests will use the isolated test database.

    Args:
        test_db: The test database session fixture.

    Yields:
        TestClient: FastAPI test client for making HTTP requests.

    Example:
        >>> def test_health_endpoint(client):
        ...     response = client.get("/health")
        ...     assert response.status_code == 200
    """
    from fastapi.testclient import TestClient

    def override_get_db():
        """Override the database dependency with test session."""
        try:
            yield test_db
        finally:
            pass

    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def anyio_backend():
    """
    Configure anyio backend for async tests.

    Returns:
        str: The async backend to use (asyncio).
    """
    return "asyncio"
