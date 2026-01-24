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
    - Game: Basketball game between two teams
    - PlayerGameStats: Per-player box score statistics
    - TeamGameStats: Team-level aggregated statistics
    - PlayByPlayEvent: Individual play-by-play event
    - PlayByPlayEventLink: Association linking related events
    - PlayerSeasonStats: Pre-computed aggregated player season statistics
    - SyncLog: Tracks data synchronization operations

Usage:
    from src.models import Base, UUIDMixin, TimestampMixin
    from src.models import League, Season, Team, Player, Game

    class MyModel(UUIDMixin, TimestampMixin, Base):
        __tablename__ = "my_table"
        # ... columns
"""

from src.models.base import Base, TimestampMixin, UUIDMixin
from src.models.game import Game, PlayerGameStats, TeamGameStats
from src.models.league import League, Season
from src.models.play_by_play import PlayByPlayEvent, PlayByPlayEventLink
from src.models.player import Player, PlayerTeamHistory
from src.models.stats import PlayerSeasonStats
from src.models.sync import SyncLog
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
    # Game models
    "Game",
    "PlayerGameStats",
    "TeamGameStats",
    # Play-by-play models
    "PlayByPlayEvent",
    "PlayByPlayEventLink",
    # Aggregated stats models
    "PlayerSeasonStats",
    # Sync models
    "SyncLog",
]
