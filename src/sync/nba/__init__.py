"""
NBA Sync Module

Provides data synchronization capabilities for NBA basketball data from the
NBA Stats API (stats.nba.com) using the nba_api package.

This module exports:
    - NBAAdapter: Main adapter implementing BaseLeagueAdapter
    - NBAClient: Client for NBA API access
    - NBAMapper: Transforms NBA data to Raw types
    - NBAConfig: Configuration settings

Usage:
    from src.sync.nba import NBAAdapter, NBAClient, NBAMapper, NBAConfig

    # Create components
    config = NBAConfig()
    client = NBAClient(config)
    mapper = NBAMapper()

    # Create adapter
    adapter = NBAAdapter(client, mapper, config)

    # Fetch data
    seasons = await adapter.get_seasons()
    teams = await adapter.get_teams(seasons[0].external_id)
    games = await adapter.get_schedule(seasons[0].external_id)

    # Get detailed game data
    for game in games:
        if adapter.is_game_final(game):
            boxscore = await adapter.get_game_boxscore(game.external_id)
            pbp = await adapter.get_game_pbp(game.external_id)

Example with custom configuration:
    config = NBAConfig(
        requests_per_minute=10,
        configured_seasons=["2023-24", "2022-23"]
    )
    client = NBAClient(config)
    mapper = NBAMapper()
    adapter = NBAAdapter(client, mapper, config)
"""

from src.sync.nba.adapter import NBAAdapter
from src.sync.nba.client import NBAClient
from src.sync.nba.config import NBAConfig
from src.sync.nba.mapper import NBAMapper

__all__ = [
    "NBAAdapter",
    "NBAClient",
    "NBAConfig",
    "NBAMapper",
]
