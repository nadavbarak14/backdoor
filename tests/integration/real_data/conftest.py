"""
Fixtures for real database integration tests.

Provides fixtures that connect to the actual database for read-only testing.
"""

import os
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.database import get_db
from src.main import app

REAL_DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "basketball.db",
)
REAL_DATABASE_URL = f"sqlite:///{REAL_DATABASE_PATH}"


@pytest.fixture(scope="module")
def real_engine():
    """Create engine connected to the real database."""
    if not os.path.exists(REAL_DATABASE_PATH):
        pytest.skip(f"Real database not found at {REAL_DATABASE_PATH}")

    engine = create_engine(
        REAL_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def real_db(real_engine) -> Generator[Session, Any, None]:
    """Create a read-only session to the real database."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=real_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def real_client(real_db: Session) -> Generator[TestClient, Any, None]:
    """Create a FastAPI TestClient using the real database."""

    def override_get_db():
        try:
            yield real_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
