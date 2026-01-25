"""
Sync Package

External data synchronization for the Basketball Analytics Platform.
Handles importing data from external APIs into the local database.

Usage:
    # Winner League
    from src.sync.winner import WinnerClient, WinnerScraper

    # Euroleague
    from src.sync.euroleague import EuroleagueClient, EuroleagueDirectClient
"""

from src.sync.euroleague import (
    EuroleagueClient,
    EuroleagueConfig,
    EuroleagueDirectClient,
    EuroleagueError,
    PlayerData,
    RosterPlayer,
    TeamData,
)
from src.sync.winner import (
    CacheResult,
    HistoricalResults,
    PlayerProfile,
    RateLimiter,
    TeamRoster,
    WinnerClient,
    WinnerConfig,
    WinnerError,
    WinnerScraper,
)

__all__ = [
    # Winner League
    "WinnerClient",
    "WinnerScraper",
    "WinnerConfig",
    "WinnerError",
    "CacheResult",
    "PlayerProfile",
    "TeamRoster",
    "HistoricalResults",
    "RateLimiter",
    # Euroleague
    "EuroleagueClient",
    "EuroleagueDirectClient",
    "EuroleagueConfig",
    "EuroleagueError",
    "TeamData",
    "PlayerData",
    "RosterPlayer",
]
