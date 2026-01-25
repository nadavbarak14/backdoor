"""
Euroleague Sync Package

Data fetching layer for Euroleague and EuroCup basketball providing:
    - EuroleagueClient: Client wrapping euroleague-api package with caching
    - EuroleagueDirectClient: Direct HTTP client for teams and player APIs
    - EuroleagueConfig: Configuration settings for competitions and rate limits

Usage:
    from src.sync.euroleague import EuroleagueClient, EuroleagueDirectClient

    # Fetch game data using euroleague-api package
    with EuroleagueClient(db) as client:
        result = client.fetch_season_games(2024)
        print(f"Fetched {len(result.data)} games")

    # Fetch teams with rosters (direct API)
    with EuroleagueDirectClient(db) as client:
        teams = client.fetch_teams(2024)
        for team in teams.data:
            print(f"{team['name']}: {len(team['players'])} players")

    # EuroCup configuration
    from src.sync.euroleague import EuroleagueConfig
    config = EuroleagueConfig(competition='U')
    with EuroleagueClient(db, config=config) as client:
        result = client.fetch_season_games(2024)
"""

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

__all__ = [
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
