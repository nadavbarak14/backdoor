"""
Winner League Sync Package

Data fetching layer for Winner League (Israeli Basketball) providing:
    - WinnerClient: JSON API client for games, boxscores, and play-by-play
    - WinnerScraper: HTML scraper for player profiles and team rosters
    - WinnerMapper: Maps raw data to normalized Raw types
    - WinnerAdapter: Unified adapter implementing BaseLeagueAdapter
    - WinnerConfig: Configuration settings for rate limits and timeouts
    - RateLimiter: Token bucket rate limiter for request throttling

Usage:
    from src.sync.winner import WinnerClient, WinnerScraper, WinnerMapper, WinnerAdapter

    # Fetch game data
    with WinnerClient(db) as client:
        result = client.fetch_games_all()
        print(f"Fetched {len(result.data.get('games', []))} games")

    # Scrape player profile
    with WinnerScraper(db) as scraper:
        profile = scraper.fetch_player("12345")
        print(f"Player: {profile.name}")

    # Use unified adapter
    mapper = WinnerMapper()
    adapter = WinnerAdapter(client, scraper, mapper)
    seasons = await adapter.get_seasons()
"""

from src.sync.winner.adapter import WinnerAdapter
from src.sync.winner.client import CacheResult, WinnerClient
from src.sync.winner.config import WinnerConfig
from src.sync.winner.exceptions import (
    WinnerAPIError,
    WinnerError,
    WinnerParseError,
    WinnerRateLimitError,
    WinnerTimeoutError,
)
from src.sync.winner.mapper import WinnerMapper
from src.sync.winner.rate_limiter import RateLimiter
from src.sync.winner.scraper import (
    HistoricalResults,
    PlayerProfile,
    TeamRoster,
    WinnerScraper,
)

__all__ = [
    # Adapter
    "WinnerAdapter",
    # Mapper
    "WinnerMapper",
    # Client
    "WinnerClient",
    "CacheResult",
    # Scraper
    "WinnerScraper",
    "PlayerProfile",
    "TeamRoster",
    "HistoricalResults",
    # Config
    "WinnerConfig",
    # Rate limiter
    "RateLimiter",
    # Exceptions
    "WinnerError",
    "WinnerAPIError",
    "WinnerParseError",
    "WinnerRateLimitError",
    "WinnerTimeoutError",
]
