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
    - GameService: Game business logic
    - PlayerGameStatsService: Player game statistics business logic
    - TeamGameStatsService: Team game statistics business logic
    - PlayByPlayService: Play-by-play event business logic
    - StatsCalculationService: Calculate aggregated season statistics
    - PlayerSeasonStatsService: Player season statistics business logic
    - SyncLogService: Sync operation tracking business logic

Usage:
    from src.services import LeagueService, PlayerService, GameService

    league_service = LeagueService(db_session)
    player_service = PlayerService(db_session)
    game_service = GameService(db_session)

    # Find a league by code
    nba = league_service.get_by_code("NBA")

    # Create a player
    player = player_service.create_player(player_data)

    # Get game with box score
    game = game_service.get_with_box_score(game_id)

    # Calculate season stats
    from src.services import StatsCalculationService
    calc_service = StatsCalculationService(db_session)
    stats = calc_service.calculate_player_season_stats(player_id, team_id, season_id)

    # Track sync operations
    from src.services import SyncLogService
    sync_service = SyncLogService(db_session)
    sync = sync_service.start_sync("winner", "games", season_id=season_id)

Services handle all business logic and sit between the API layer and the
data models, providing a clean separation of concerns.
"""

from src.services.base import BaseService
from src.services.game import GameService
from src.services.league import LeagueService, SeasonService
from src.services.play_by_play import PlayByPlayService
from src.services.player import PlayerService
from src.services.player_stats import PlayerSeasonStatsService
from src.services.stats import PlayerGameStatsService, TeamGameStatsService
from src.services.stats_calculation import StatsCalculationService
from src.services.sync_service import SyncLogService
from src.services.team import TeamService

__all__ = [
    "BaseService",
    "LeagueService",
    "SeasonService",
    "TeamService",
    "PlayerService",
    "GameService",
    "PlayerGameStatsService",
    "TeamGameStatsService",
    "PlayByPlayService",
    "StatsCalculationService",
    "PlayerSeasonStatsService",
    "SyncLogService",
]
