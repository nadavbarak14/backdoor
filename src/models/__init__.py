"""
Models Package

Database models and mixins for the Basketball Analytics Platform.

This package provides:
    - Base: SQLAlchemy declarative base for all models
    - UUIDMixin: Adds UUID primary key to models
    - TimestampMixin: Adds created_at and updated_at timestamps

Entity models:
    - League: Basketball league (e.g., NBA, EuroLeague)
    - Season: A season within a league
    - Team: Basketball team
    - TeamSeason: Team participation in a season (many-to-many)
    - Player: Basketball player
    - PlayerTeamHistory: Player team affiliations by season

Usage:
    from src.models import Base, UUIDMixin, TimestampMixin
    from src.models import League, Season, Team, Player

    class MyModel(UUIDMixin, TimestampMixin, Base):
        __tablename__ = "my_table"
        # ... columns
"""

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.models.league import League, Season
from src.models.player import Player, PlayerTeamHistory
from src.models.team import Team, TeamSeason

__all__ = [
    # Base and mixins
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    # League models
    "League",
    "Season",
    # Team models
    "Team",
    "TeamSeason",
    # Player models
    "Player",
    "PlayerTeamHistory",
]
