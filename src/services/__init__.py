"""
Services Package

Business logic layer for the Basketball Analytics Platform.
Services encapsulate all business rules, validation, and orchestration.

This package exports:
    - BaseService: Generic base class with CRUD operations
    - LeagueService: League business logic
    - SeasonService: Season business logic
    - TeamService: Team business logic
    - PlayerService: Player business logic

Usage:
    from src.services import LeagueService, PlayerService

    league_service = LeagueService(db_session)
    player_service = PlayerService(db_session)

    # Find a league by code
    nba = league_service.get_by_code("NBA")

    # Create a player
    player = player_service.create_player(player_data)

Services handle all business logic and sit between the API layer and the
data models, providing a clean separation of concerns.
"""

from src.services.base import BaseService
from src.services.league import LeagueService, SeasonService
from src.services.player import PlayerService
from src.services.team import TeamService

__all__ = [
    "BaseService",
    "LeagueService",
    "SeasonService",
    "TeamService",
    "PlayerService",
]
