"""
Sync Adapters Package

Provides abstract base classes for sync adapters that fetch data from external
sources. Concrete implementations should inherit from these base classes.

Available base classes:
    - BaseLeagueAdapter: For fetching league data (games, schedules, box scores)
    - BasePlayerInfoAdapter: For fetching player biographical information

Usage:
    from src.sync.adapters import BaseLeagueAdapter, BasePlayerInfoAdapter

    class WinnerAdapter(BaseLeagueAdapter):
        source_name = "winner"

        async def get_seasons(self) -> list[RawSeason]:
            # Implementation
            ...
"""

from src.sync.adapters.base import BaseLeagueAdapter, BasePlayerInfoAdapter

__all__ = [
    "BaseLeagueAdapter",
    "BasePlayerInfoAdapter",
]
