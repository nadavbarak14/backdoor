"""
Alembic Environment Configuration

This module configures the Alembic migration environment for the
Basketball Analytics Platform. It connects to the database using
settings from the application configuration and uses the SQLAlchemy
Base metadata for autogenerate support.

The environment supports both offline (SQL script generation) and
online (direct database connection) migration modes.

Usage:
    # Generate a new migration
    alembic revision --autogenerate -m "Add players table"

    # Apply migrations
    alembic upgrade head

    # Rollback one migration
    alembic downgrade -1
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import application settings and Base metadata
from src.core.config import settings
from src.models.base import Base

# Import all models here so they are registered with Base.metadata
# This is necessary for autogenerate to detect model changes
from src.models.game import Game, PlayerGameStats, TeamGameStats  # noqa: F401
from src.models.league import League, Season  # noqa: F401
from src.models.play_by_play import PlayByPlayEvent, PlayByPlayEventLink  # noqa: F401
from src.models.player import Player, PlayerTeamHistory  # noqa: F401
from src.models.team import Team, TeamSeason  # noqa: F401

# Alembic Config object for access to .ini file values
config = context.config

# Set the SQLAlchemy URL from application settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure Python logging from the config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
# This allows Alembic to compare models against the database schema
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This generates SQL scripts without connecting to the database.
    Useful for reviewing changes before applying them or for
    environments where direct database access is restricted.

    The generated SQL can be executed manually or through a
    deployment pipeline.

    Example:
        >>> alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Enable comparison of server defaults for SQLite
        compare_server_default=True,
        # Enable comparison of types
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    This connects directly to the database and applies migrations.
    Used for development and automated deployment scenarios.

    The connection is configured with appropriate pool settings
    based on the database type.

    Example:
        >>> alembic upgrade head
    """
    # Get configuration for engine
    configuration = config.get_section(config.config_ini_section, {})

    # Handle SQLite-specific connection args
    connect_args = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Enable comparison of server defaults for SQLite
            compare_server_default=True,
            # Enable comparison of types
            compare_type=True,
            # Render as batch operations for SQLite compatibility
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Determine which mode to run
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
