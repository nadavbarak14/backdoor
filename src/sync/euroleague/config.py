"""
Euroleague Configuration Module

Provides configuration settings for the Euroleague data fetching layer,
including API endpoints, rate limits, timeouts, and retry settings.

This module exports:
    - EuroleagueConfig: Dataclass with all configuration options

Usage:
    from src.sync.euroleague.config import EuroleagueConfig

    # Use defaults (Euroleague)
    config = EuroleagueConfig()

    # EuroCup configuration
    config = EuroleagueConfig(competition="U")

    # Custom rate limiting
    config = EuroleagueConfig(requests_per_second=1.0)
"""

from dataclasses import dataclass, field


@dataclass
class EuroleagueConfig:
    """
    Configuration settings for Euroleague data fetching.

    Controls competition selection, API endpoints, rate limiting, timeouts,
    and retry behavior for both the euroleague-api package and direct API calls.

    Attributes:
        competition: Competition code ('E' for Euroleague, 'U' for EuroCup).
        teams_api_url: Base URL for teams API (XML).
        players_api_url: Base URL for player details API (XML).
        schedule_api_url: Base URL for schedule API (XML).
        live_api_url: Base URL for live game data API (JSON).
        requests_per_second: Rate limit for API requests.
        burst_size: Maximum burst size for rate limiter.
        request_timeout: HTTP request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        retry_base_delay: Base delay for exponential backoff (seconds).
        retry_max_delay: Maximum delay between retries (seconds).
        user_agent: User-Agent header for HTTP requests.

    Example:
        >>> config = EuroleagueConfig()
        >>> config.competition
        'E'
        >>> config.get_season_code(2024)
        'E2024'

        >>> eurocup = EuroleagueConfig(competition='U')
        >>> eurocup.get_season_code(2024)
        'U2024'
    """

    # Competition Selection
    competition: str = field(default="E")  # 'E' = Euroleague, 'U' = EuroCup

    # Direct API Endpoints (XML)
    teams_api_url: str = field(
        default="https://api-live.euroleague.net/v1/teams",
    )
    players_api_url: str = field(
        default="https://api-live.euroleague.net/v1/players",
    )
    schedule_api_url: str = field(
        default="https://api-live.euroleague.net/v1/schedules",
    )

    # Live Game API Endpoints (JSON)
    live_api_url: str = field(
        default="https://live.euroleague.net/api",
    )

    # Rate Limiting
    requests_per_second: float = field(default=2.0)
    burst_size: int = field(default=5)

    # Timeouts and Retries
    request_timeout: float = field(default=30.0)
    max_retries: int = field(default=3)
    retry_base_delay: float = field(default=1.0)
    retry_max_delay: float = field(default=30.0)

    # HTTP Headers
    user_agent: str = field(
        default="BasketballAnalytics/1.0 (https://github.com/nadavbarak14/backdoor)",
    )

    def get_season_code(self, season: int) -> str:
        """
        Get the season code for API requests.

        Args:
            season: The season year (e.g., 2024).

        Returns:
            str: Season code (e.g., 'E2024' or 'U2024').

        Example:
            >>> config = EuroleagueConfig()
            >>> config.get_season_code(2024)
            'E2024'
        """
        return f"{self.competition}{season}"

    def get_teams_url(self, season: int) -> str:
        """
        Get the teams API URL for a specific season.

        Args:
            season: The season year.

        Returns:
            str: Full URL for the teams endpoint.

        Example:
            >>> config = EuroleagueConfig()
            >>> config.get_teams_url(2024)
            'https://api-live.euroleague.net/v1/teams?seasonCode=E2024'
        """
        return f"{self.teams_api_url}?seasonCode={self.get_season_code(season)}"

    def get_player_url(self, player_code: str, season: int) -> str:
        """
        Get the player details API URL.

        Args:
            player_code: The player code (e.g., '011987').
            season: The season year.

        Returns:
            str: Full URL for the player endpoint.

        Example:
            >>> config = EuroleagueConfig()
            >>> config.get_player_url('011987', 2024)
            'https://api-live.euroleague.net/v1/players?playerCode=011987&seasonCode=E2024'
        """
        return (
            f"{self.players_api_url}"
            f"?playerCode={player_code}&seasonCode={self.get_season_code(season)}"
        )

    def get_schedule_url(self, season: int) -> str:
        """
        Get the schedule API URL for a specific season.

        Args:
            season: The season year.

        Returns:
            str: Full URL for the schedule endpoint.

        Example:
            >>> config = EuroleagueConfig()
            >>> config.get_schedule_url(2024)
            'https://api-live.euroleague.net/v1/schedules?seasonCode=E2024'
        """
        return f"{self.schedule_api_url}?seasonCode={self.get_season_code(season)}"

    def get_live_url(self, endpoint: str, gamecode: int, season: int) -> str:
        """
        Get the live game API URL for a specific endpoint.

        Args:
            endpoint: API endpoint (Header, Boxscore, PlaybyPlay, Points, etc.).
            gamecode: The game code.
            season: The season year.

        Returns:
            str: Full URL for the live game endpoint.

        Example:
            >>> config = EuroleagueConfig()
            >>> config.get_live_url('Boxscore', 1, 2024)
            'https://live.euroleague.net/api/Boxscore?gamecode=1&seasoncode=E2024'
        """
        return (
            f"{self.live_api_url}/{endpoint}"
            f"?gamecode={gamecode}&seasoncode={self.get_season_code(season)}"
        )
