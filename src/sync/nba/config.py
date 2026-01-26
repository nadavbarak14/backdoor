"""
NBA Configuration Module

Provides configuration settings for the NBA data fetching layer,
including rate limits, timeouts, retry settings, and season configuration.

This module exports:
    - NBAConfig: Dataclass with all configuration options

Usage:
    from src.sync.nba.config import NBAConfig

    # Use defaults
    config = NBAConfig()

    # Custom rate limiting
    config = NBAConfig(requests_per_minute=30)
"""

from dataclasses import dataclass, field


@dataclass
class NBAConfig:
    """
    Configuration settings for NBA data fetching.

    Controls rate limiting, timeouts, retry behavior, and season settings
    for the nba_api wrapper.

    Attributes:
        requests_per_minute: Rate limit for API requests.
        request_timeout: HTTP request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        retry_base_delay: Base delay for exponential backoff (seconds).
        retry_max_delay: Maximum delay between retries (seconds).
        proxy: Optional proxy URL for requests.
        headers: Custom headers to include in requests.
        configured_seasons: List of season strings to make available (e.g., ["2023-24"]).

    Example:
        >>> config = NBAConfig()
        >>> config.requests_per_minute
        20
        >>> config.get_season_id("2023-24")
        '2023-24'

        >>> config = NBAConfig(requests_per_minute=10)
        >>> config.requests_per_minute
        10
    """

    # Rate Limiting
    # NBA Stats API is known to be rate-limited; conservative default
    requests_per_minute: int = field(default=20)

    # Timeouts and Retries
    request_timeout: float = field(default=30.0)
    max_retries: int = field(default=3)
    retry_base_delay: float = field(default=2.0)
    retry_max_delay: float = field(default=60.0)

    # Proxy support (NBA API sometimes blocks IPs)
    proxy: str | None = field(default=None)

    # Custom headers (nba_api handles User-Agent, but allow overrides)
    headers: dict[str, str] = field(default_factory=dict)

    # Season configuration
    # Default to current and previous season
    configured_seasons: list[str] | None = field(default=None)

    def __post_init__(self) -> None:
        """Initialize default seasons if not provided."""
        if self.configured_seasons is None:
            from datetime import datetime

            current_year = datetime.now().year
            current_month = datetime.now().month
            # NBA season starts in October
            if current_month >= 10:
                current_season_start = current_year
            else:
                current_season_start = current_year - 1

            # Format as "2023-24"
            current = f"{current_season_start}-{str(current_season_start + 1)[-2:]}"
            previous = f"{current_season_start - 1}-{str(current_season_start)[-2:]}"
            self.configured_seasons = [current, previous]

    def get_season_id(self, season: str) -> str:
        """
        Get the season ID in NBA API format.

        Args:
            season: Season string (e.g., "2023-24").

        Returns:
            str: Season ID in NBA API format.

        Example:
            >>> config = NBAConfig()
            >>> config.get_season_id("2023-24")
            '2023-24'
        """
        return season

    def get_season_year(self, season: str) -> int:
        """
        Extract the start year from a season string.

        Args:
            season: Season string (e.g., "2023-24").

        Returns:
            int: Start year of the season.

        Example:
            >>> config = NBAConfig()
            >>> config.get_season_year("2023-24")
            2023
        """
        return int(season.split("-")[0])

    @property
    def delay_between_requests(self) -> float:
        """
        Calculate delay between requests based on rate limit.

        Returns:
            float: Delay in seconds between requests.

        Example:
            >>> config = NBAConfig(requests_per_minute=30)
            >>> config.delay_between_requests
            2.0
        """
        return 60.0 / self.requests_per_minute
