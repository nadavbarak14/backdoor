"""
Models Package

Database models and mixins for the Basketball Analytics Platform.

This package provides:
    - Base: SQLAlchemy declarative base for all models
    - UUIDMixin: Adds UUID primary key to models
    - TimestampMixin: Adds created_at and updated_at timestamps

All entity models (Player, Team, Game, etc.) will be exported from this package
as they are implemented.

Usage:
    from src.models import Base, UUIDMixin, TimestampMixin

    class MyModel(UUIDMixin, TimestampMixin, Base):
        __tablename__ = "my_table"
        # ... columns
"""

from src.models.base import Base, TimestampMixin, UUIDMixin

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
]
