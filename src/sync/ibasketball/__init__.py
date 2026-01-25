"""
iBasketball Sync Package

Data fetching layer for iBasketball.co.il (Israeli Basketball) providing:
    - IBasketballAdapter: Unified adapter implementing BaseLeagueAdapter
    - IBasketballApiClient: REST API client for events, boxscores, and standings
    - IBasketballScraper: HTML scraper for PBP and player profiles
    - IBasketballMapper: Maps raw data to normalized Raw types
    - IBasketballConfig: Configuration settings for leagues and rate limits

Supported leagues:
    - Liga Leumit (ID: 119474)
    - Liga Alef (ID: 119473)

The adapter uses the SportsPress WordPress plugin REST API at
/wp-json/sportspress/v2/ for structured data, and HTML scraping
for play-by-play and detailed player information.

Usage:
    from src.sync.ibasketball import (
        IBasketballAdapter,
        IBasketballApiClient,
        IBasketballScraper,
        IBasketballMapper,
    )

    # Fetch game data
    with IBasketballApiClient(db) as client:
        result = client.fetch_all_events("119474")  # Liga Leumit
        print(f"Fetched {len(result.data)} events")

    # Scrape player profile
    with IBasketballScraper(db) as scraper:
        profile = scraper.fetch_player("john-smith")
        print(f"Player: {profile.name}")

    # Use unified adapter
    mapper = IBasketballMapper()
    adapter = IBasketballAdapter(client, mapper, scraper)
    adapter.set_league("liga_leumit")
    seasons = await adapter.get_seasons()
"""

from src.sync.ibasketball.adapter import IBasketballAdapter
from src.sync.ibasketball.api_client import CacheResult, IBasketballApiClient
from src.sync.ibasketball.config import IBasketballConfig, LeagueConfig
from src.sync.ibasketball.exceptions import (
    IBasketballAPIError,
    IBasketballError,
    IBasketballLeagueNotFoundError,
    IBasketballParseError,
    IBasketballRateLimitError,
    IBasketballTimeoutError,
)
from src.sync.ibasketball.mapper import IBasketballMapper
from src.sync.ibasketball.scraper import (
    GamePBP,
    IBasketballScraper,
    PBPEvent,
    PlayerProfile,
)

__all__ = [
    # Adapter
    "IBasketballAdapter",
    # Mapper
    "IBasketballMapper",
    # Client
    "IBasketballApiClient",
    "CacheResult",
    # Scraper
    "IBasketballScraper",
    "PlayerProfile",
    "GamePBP",
    "PBPEvent",
    # Config
    "IBasketballConfig",
    "LeagueConfig",
    # Exceptions
    "IBasketballError",
    "IBasketballAPIError",
    "IBasketballParseError",
    "IBasketballRateLimitError",
    "IBasketballTimeoutError",
    "IBasketballLeagueNotFoundError",
]
