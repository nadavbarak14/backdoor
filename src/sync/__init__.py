"""
Sync Package

External data synchronization for the Basketball Analytics Platform.
Handles importing data from external APIs into the local database.

Usage:
    # Base infrastructure
    from src.sync.adapters import BaseLeagueAdapter, BasePlayerInfoAdapter
    from src.sync.types import RawSeason, RawTeam, RawGame, RawBoxScore
    from src.sync.config import SyncConfig, SyncSourceConfig
    from src.sync.tracking import SyncTracker

    # Player Info Service
    from src.sync.player_info import PlayerInfoService, MergedPlayerInfo

    # Winner League
    from src.sync.winner import WinnerClient, WinnerScraper

    # Euroleague
    from src.sync.euroleague import EuroleagueClient, EuroleagueDirectClient
"""

# Base infrastructure
from src.sync.adapters import BaseLeagueAdapter, BasePlayerInfoAdapter
from src.sync.config import SyncConfig, SyncSourceConfig

# Player Info Service
from src.sync.player_info import MergedPlayerInfo, PlayerInfoService, merge_player_info

# Euroleague
from src.sync.euroleague import (
    EuroleagueClient,
    EuroleagueConfig,
    EuroleagueDirectClient,
    EuroleagueError,
    PlayerData,
    RosterPlayer,
    TeamData,
)
from src.sync.exceptions import (
    AdapterError,
    ConnectionError,
    DataValidationError,
    GameNotFoundError,
    PlayerNotFoundError,
    RateLimitError,
    SeasonNotFoundError,
    SyncConfigError,
    SyncError,
)
from src.sync.tracking import SyncTracker
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawPlayerStats,
    RawSeason,
    RawTeam,
)

# Winner League
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
    # Base infrastructure - Adapters
    "BaseLeagueAdapter",
    "BasePlayerInfoAdapter",
    # Base infrastructure - Config
    "SyncConfig",
    "SyncSourceConfig",
    # Base infrastructure - Tracking
    "SyncTracker",
    # Player Info Service
    "PlayerInfoService",
    "MergedPlayerInfo",
    "merge_player_info",
    # Base infrastructure - Types
    "RawSeason",
    "RawTeam",
    "RawGame",
    "RawPlayerStats",
    "RawBoxScore",
    "RawPBPEvent",
    "RawPlayerInfo",
    # Base infrastructure - Exceptions
    "SyncError",
    "AdapterError",
    "ConnectionError",
    "RateLimitError",
    "GameNotFoundError",
    "SeasonNotFoundError",
    "PlayerNotFoundError",
    "DataValidationError",
    "SyncConfigError",
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
