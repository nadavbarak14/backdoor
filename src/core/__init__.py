"""
Core Module

Contains core application infrastructure including configuration,
database setup, and shared utilities.

Exports:
    settings: Application settings singleton
    Settings: Settings class for type hints and testing
    get_settings: Factory function for settings (useful for dependency injection)
    engine: SQLAlchemy database engine
    SessionLocal: Database session factory
    get_db: FastAPI dependency for database sessions
"""

from src.core.config import Settings, get_settings, settings
from src.core.database import SessionLocal, engine, get_db

__all__ = [
    "Settings",
    "get_settings",
    "settings",
    "engine",
    "SessionLocal",
    "get_db",
]
