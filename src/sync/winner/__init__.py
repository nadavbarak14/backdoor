"""
Winner League Sync Package

Data fetching layer for Winner League (Israeli Basketball) providing:
    - WinnerClient: JSON API client for games, boxscores, and play-by-play
    - WinnerScraper: HTML scraper for player profiles and team rosters
    - WinnerConfig: Configuration settings for rate limits and timeouts
    - RateLimiter: Token bucket rate limiter for request throttling

Usage:
    from src.sync.winner import WinnerClient, WinnerScraper

    # Fetch game data
    with WinnerClient(db) as client:
        result = client.fetch_games_all()
        print(f"Fetched {len(result.data.get('games', []))} games")

    # Scrape player profile
    with WinnerScraper(db) as scraper:
        profile = scraper.fetch_player("12345")
        print(f"Player: {profile.name}")
"""

from src.sync.winner.client import CacheResult, WinnerClient
from src.sync.winner.config import WinnerConfig
from src.sync.winner.exceptions import (
    WinnerAPIError,
    WinnerError,
    WinnerParseError,
    WinnerRateLimitError,
    WinnerTimeoutError,
)
from src.sync.winner.rate_limiter import RateLimiter
from src.sync.winner.scraper import (
    HistoricalResults,
    PlayerProfile,
    TeamRoster,
    WinnerScraper,
)

__all__ = [
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
