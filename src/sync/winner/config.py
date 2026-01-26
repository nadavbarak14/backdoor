"""
Winner League Configuration Module

Provides configuration settings for the Winner League data fetching layer,
including API endpoints, rate limits, timeouts, and retry settings.

This module exports:
    - WinnerConfig: Dataclass with all configuration options

Usage:
    from src.sync.winner.config import WinnerConfig

    # Use defaults
    config = WinnerConfig()

    # Custom configuration
    config = WinnerConfig(
        api_requests_per_second=1.0,
        request_timeout=60.0
    )
"""

from dataclasses import dataclass, field


@dataclass
class WinnerConfig:
    """
    Configuration settings for Winner League data fetching.

    Controls API endpoints, rate limiting, timeouts, and retry behavior
    for both JSON API requests and HTML scraping.

    Attributes:
        games_all_url: URL for fetching all current season games.
        boxscore_url_template: URL template for fetching game boxscores.
        pbp_url_template: URL template for fetching play-by-play data.
        player_url_template: URL template for player profile pages.
        team_url_template: URL template for team roster pages.
        results_url_template: URL template for historical results.
        api_requests_per_second: Rate limit for JSON API requests.
        scrape_requests_per_second: Rate limit for HTML scraping.
        api_burst_size: Maximum burst size for API rate limiter.
        scrape_burst_size: Maximum burst size for scrape rate limiter.
        request_timeout: HTTP request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        retry_base_delay: Base delay for exponential backoff (seconds).
        retry_max_delay: Maximum delay between retries (seconds).
        user_agent: User-Agent header for HTTP requests.

    Example:
        >>> config = WinnerConfig()
        >>> config.api_requests_per_second
        2.0
        >>> config.request_timeout
        30.0

        >>> custom = WinnerConfig(
        ...     api_requests_per_second=1.0,
        ...     request_timeout=60.0
        ... )
    """

    # API Endpoints
    games_all_url: str = field(
        default="https://basket.co.il/pbp/json/games_all.json",
    )
    boxscore_url_template: str = field(
        default="https://stats.segevstats.com/realtimestat_heb/get_team_score.php?game_id={game_id}",
    )
    pbp_url_template: str = field(
        default="https://stats.segevstats.com/realtimestat_heb/get_team_action.php?game_id={game_id}",
    )

    # Scraping Endpoints
    player_url_template: str = field(
        default="https://basket.co.il/player.asp?PlayerId={player_id}",
    )
    team_url_template: str = field(
        default="https://basket.co.il/team.asp?TeamId={team_id}",
    )
    results_url_template: str = field(
        default="https://basket.co.il/results.asp?cYear={year}",
    )

    # Rate Limiting
    api_requests_per_second: float = field(default=2.0)
    scrape_requests_per_second: float = field(default=0.5)
    api_burst_size: int = field(default=5)
    scrape_burst_size: int = field(default=2)

    # Timeouts and Retries
    request_timeout: float = field(default=30.0)
    max_retries: int = field(default=3)
    retry_base_delay: float = field(default=1.0)
    retry_max_delay: float = field(default=30.0)

    # HTTP Headers
    user_agent: str = field(
        default="BasketballAnalytics/1.0 (https://github.com/nadavbarak14/backdoor)",
    )

    def get_boxscore_url(self, game_id: str) -> str:
        """
        Get the boxscore URL for a specific game.

        Args:
            game_id: The game identifier.

        Returns:
            str: Full URL for the boxscore endpoint.

        Example:
            >>> config = WinnerConfig()
            >>> config.get_boxscore_url("12345")
            'https://segevstats.com/get_team_score.php?game_id=12345'
        """
        return self.boxscore_url_template.format(game_id=game_id)

    def get_pbp_url(self, game_id: str) -> str:
        """
        Get the play-by-play URL for a specific game.

        Args:
            game_id: The game identifier.

        Returns:
            str: Full URL for the play-by-play endpoint.

        Example:
            >>> config = WinnerConfig()
            >>> config.get_pbp_url("12345")
            'https://segevstats.com/get_team_action.php?game_id=12345'
        """
        return self.pbp_url_template.format(game_id=game_id)

    def get_player_url(self, player_id: str) -> str:
        """
        Get the player profile URL.

        Args:
            player_id: The player identifier.

        Returns:
            str: Full URL for the player profile page.

        Example:
            >>> config = WinnerConfig()
            >>> config.get_player_url("54321")
            'https://basket.co.il/player.asp?PlayerId=54321'
        """
        return self.player_url_template.format(player_id=player_id)

    def get_team_url(self, team_id: str) -> str:
        """
        Get the team roster URL.

        Args:
            team_id: The team identifier.

        Returns:
            str: Full URL for the team roster page.

        Example:
            >>> config = WinnerConfig()
            >>> config.get_team_url("100")
            'https://basket.co.il/team.asp?TeamId=100'
        """
        return self.team_url_template.format(team_id=team_id)

    def get_results_url(self, year: int) -> str:
        """
        Get the historical results URL for a specific year.

        Args:
            year: The season year.

        Returns:
            str: Full URL for the historical results page.

        Example:
            >>> config = WinnerConfig()
            >>> config.get_results_url(2024)
            'https://basket.co.il/results.asp?cYear=2024'
        """
        return self.results_url_template.format(year=year)
