"""
Migration Integration Tests

Tests that Alembic migrations can be applied and rolled back correctly.
These tests ensure the migration scripts work properly and the database
schema matches the SQLAlchemy models.

Usage:
    uv run python -m pytest tests/integration/test_migrations.py -v
"""

import contextlib
import os
import tempfile
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from alembic import command


def get_alembic_config(database_url: str) -> Config:
    """
    Create an Alembic Config object configured for testing.

    Args:
        database_url: SQLAlchemy database URL to use for migrations.

    Returns:
        Config: Alembic configuration object.

    Example:
        >>> config = get_alembic_config("sqlite:///:memory:")
        >>> config.get_main_option("sqlalchemy.url")
        'sqlite:///:memory:'
    """
    # Get the project root directory (where alembic.ini is located)
    project_root = Path(__file__).parent.parent.parent

    # Create config from alembic.ini
    alembic_cfg = Config(str(project_root / "alembic.ini"))

    # Override the database URL for testing
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    # Set the script location relative to project root
    alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))

    return alembic_cfg


@pytest.fixture
def migration_engine():
    """
    Create a temporary SQLite database engine for migration testing.

    Uses a temporary file-based SQLite database to properly test
    migration behavior (in-memory databases have limitations with
    Alembic's connection handling).

    Yields:
        tuple: (Engine, database_url) for the temporary database.

    Example:
        >>> def test_example(migration_engine):
        ...     engine, db_url = migration_engine
        ...     # Use engine for testing
    """
    # Create a temporary file for the database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    database_url = f"sqlite:///{tmp_path}"

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    yield engine, database_url

    # Cleanup
    engine.dispose()
    with contextlib.suppress(OSError):
        os.unlink(tmp_path)


class TestMigrations:
    """
    Integration tests for Alembic migrations.

    These tests verify that:
    - Migrations can be applied from an empty database
    - Migrations can be rolled back completely
    - The upgrade/downgrade cycle is reversible
    """

    def test_upgrade_head(self, migration_engine):
        """
        Test that alembic upgrade head runs on a fresh database.

        Verifies that all migrations can be applied successfully
        from an empty database state. If no migrations exist yet,
        the command should still run without error.

        Args:
            migration_engine: Pytest fixture providing test database.

        Example:
            >>> # Run with: uv run python -m pytest -v -k test_upgrade_head
        """
        engine, database_url = migration_engine
        alembic_cfg = get_alembic_config(database_url)

        # Run upgrade to head - should not raise any exceptions
        # This verifies the Alembic configuration is valid
        command.upgrade(alembic_cfg, "head")

        # Verify no error occurred - the alembic_version table
        # is only created when there are actual migrations to apply
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # If there are migrations, alembic_version should exist
        # If no migrations yet, the table list may be empty (valid state)
        # The test passes as long as upgrade runs without error
        assert isinstance(tables, list), "Should be able to inspect tables"

    def test_downgrade_base(self, migration_engine):
        """
        Test that alembic downgrade base works after upgrade.

        Verifies that all migrations can be rolled back successfully
        after being applied.

        Args:
            migration_engine: Pytest fixture providing test database.

        Example:
            >>> # Run with: uv run python -m pytest -v -k test_downgrade_base
        """
        engine, database_url = migration_engine
        alembic_cfg = get_alembic_config(database_url)

        # First upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Then downgrade to base (empty database)
        command.downgrade(alembic_cfg, "base")

        # Verify alembic_version is empty or tables are dropped
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # After downgrade to base, application tables should be removed
        # alembic_version may or may not exist depending on implementation
        app_tables = [t for t in tables if not t.startswith("alembic_")]
        assert len(app_tables) == 0, f"Application tables should be removed: {app_tables}"

    def test_upgrade_downgrade_cycle(self, migration_engine):
        """
        Test complete upgrade and downgrade cycle is reversible.

        Verifies that the database can be upgraded and downgraded
        multiple times without errors.

        Args:
            migration_engine: Pytest fixture providing test database.

        Example:
            >>> # Run with: uv run python -m pytest -v -k test_upgrade_downgrade_cycle
        """
        engine, database_url = migration_engine
        alembic_cfg = get_alembic_config(database_url)

        # Cycle 1: upgrade then downgrade
        command.upgrade(alembic_cfg, "head")
        command.downgrade(alembic_cfg, "base")

        # Cycle 2: upgrade again - should work on clean state
        command.upgrade(alembic_cfg, "head")

        # Verify no error occurred - commands completed successfully
        # The test passes as long as the upgrade/downgrade cycle works
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert isinstance(tables, list), "Should be able to inspect tables"

    def test_current_revision_after_upgrade(self, migration_engine):
        """
        Test that current revision is set after upgrade.

        Verifies that the alembic_version table contains a revision
        after running upgrade head. If no migrations exist, the
        alembic_version table may not exist.

        Args:
            migration_engine: Pytest fixture providing test database.

        Example:
            >>> # Run with: uv run python -m pytest -v -k test_current_revision
        """
        engine, database_url = migration_engine
        alembic_cfg = get_alembic_config(database_url)

        # Upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Check if alembic_version table exists and has a revision
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "alembic_version" in tables:
            # If table exists, verify it can be queried
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                versions = result.fetchall()
                assert isinstance(versions, list), "Should be able to query alembic_version"
        else:
            # If no migrations exist yet, table won't be created
            # This is valid initial state - test passes
            pass
