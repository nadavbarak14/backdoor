"""
Euroleague Sync Package

Data fetching layer for Euroleague and EuroCup basketball providing:
    - EuroleagueClient: Client wrapping euroleague-api package with caching
    - EuroleagueDirectClient: Direct HTTP client for teams and player APIs
    - EuroleagueMapper: Maps raw data to normalized Raw types
    - EuroleagueAdapter: Unified adapter implementing BaseLeagueAdapter
    - EuroleagueConfig: Configuration settings for competitions and rate limits

Usage:
    from src.sync.euroleague import (
        EuroleagueClient,
        EuroleagueDirectClient,
        EuroleagueMapper,
        EuroleagueAdapter,
    )

    # Fetch game data using euroleague-api package
    with EuroleagueClient(db) as client:
        result = client.fetch_season_games(2024)
        print(f"Fetched {len(result.data)} games")

    # Fetch teams with rosters (direct API)
    with EuroleagueDirectClient(db) as client:
        teams = client.fetch_teams(2024)
        for team in teams.data:
            print(f"{team['name']}: {len(team['players'])} players")

    # Use unified adapter
    mapper = EuroleagueMapper()
    adapter = EuroleagueAdapter(client, direct_client, mapper)
    seasons = await adapter.get_seasons()
"""

from src.sync.euroleague.adapter import EuroleagueAdapter
from src.sync.euroleague.client import CacheResult, EuroleagueClient
from src.sync.euroleague.config import EuroleagueConfig
from src.sync.euroleague.direct_client import (
    EuroleagueDirectClient,
    PlayerData,
    RosterPlayer,
    TeamData,
)
from src.sync.euroleague.exceptions import (
    EuroleagueAPIError,
    EuroleagueError,
    EuroleagueParseError,
    EuroleagueRateLimitError,
    EuroleagueTimeoutError,
)
from src.sync.euroleague.mapper import EuroleagueMapper

__all__ = [
    # Adapter
    "EuroleagueAdapter",
    # Mapper
    "EuroleagueMapper",
    # Clients
    "EuroleagueClient",
    "EuroleagueDirectClient",
    "CacheResult",
    # Data types
    "TeamData",
    "PlayerData",
    "RosterPlayer",
    # Config
    "EuroleagueConfig",
    # Exceptions
    "EuroleagueError",
    "EuroleagueAPIError",
    "EuroleagueParseError",
    "EuroleagueRateLimitError",
    "EuroleagueTimeoutError",
]
