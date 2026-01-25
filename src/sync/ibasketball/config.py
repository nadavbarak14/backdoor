"""
iBasketball Configuration Module

Provides configuration settings for the iBasketball data fetching layer,
including API endpoints, league configurations, rate limits, and timeout settings.

iBasketball.co.il uses the SportsPress WordPress plugin which exposes data
via the WP REST API at /wp-json/sportspress/v2/.

This module exports:
    - IBasketballConfig: Dataclass with all configuration options
    - LeagueConfig: Configuration for a specific league

Usage:
    from src.sync.ibasketball.config import IBasketballConfig

    # Use defaults
    config = IBasketballConfig()

    # Custom configuration
    config = IBasketballConfig(
        api_requests_per_second=1.0,
        request_timeout=60.0
    )
"""

from dataclasses import dataclass, field


@dataclass
class LeagueConfig:
    """
    Configuration for a specific league in iBasketball.

    Attributes:
        league_id: SportsPress league/competition ID.
        name: Display name of the league.
        short_name: Abbreviated league name.

    Example:
        >>> liga_al = LeagueConfig(
        ...     league_id="119473",
        ...     name="Liga Alef",
        ...     short_name="Liga Al"
        ... )
    """

    league_id: str
    name: str
    short_name: str


@dataclass
class IBasketballConfig:
    """
    Configuration settings for iBasketball data fetching.

    Controls API endpoints, rate limiting, timeouts, and retry behavior
    for both REST API requests and HTML scraping.

    Attributes:
        base_url: Base URL for iBasketball website.
        api_base_url: Base URL for SportsPress REST API.
        events_endpoint: API endpoint for fetching events/games.
        event_endpoint_template: URL template for single event with boxscore.
        standings_endpoint_template: URL template for standings.
        teams_endpoint: API endpoint for fetching teams.
        players_endpoint: API endpoint for fetching players.
        game_page_template: URL template for game HTML page (PBP).
        player_page_template: URL template for player profile page.
        leagues: Dictionary of league configurations keyed by short name.
        default_league: Default league key to use.
        api_requests_per_second: Rate limit for REST API requests.
        scrape_requests_per_second: Rate limit for HTML scraping.
        api_burst_size: Maximum burst size for API rate limiter.
        scrape_burst_size: Maximum burst size for scrape rate limiter.
        request_timeout: HTTP request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        retry_base_delay: Base delay for exponential backoff (seconds).
        retry_max_delay: Maximum delay between retries (seconds).
        user_agent: User-Agent header for HTTP requests.
        per_page: Number of items per page for paginated API requests.

    Example:
        >>> config = IBasketballConfig()
        >>> config.api_requests_per_second
        2.0
        >>> config.get_events_url("119474")
        'https://ibasketball.co.il/wp-json/sportspress/v2/events?leagues=119474&per_page=100'
    """

    # Base URLs
    base_url: str = field(default="https://ibasketball.co.il")
    api_base_url: str = field(default="https://ibasketball.co.il/wp-json/sportspress/v2")

    # API Endpoints
    events_endpoint: str = field(default="/events")
    event_endpoint_template: str = field(default="/events/{event_id}")
    standings_endpoint_template: str = field(default="/tables?leagues={league_id}")
    teams_endpoint: str = field(default="/teams")
    players_endpoint: str = field(default="/players")

    # HTML Scraping Endpoints
    game_page_template: str = field(default="/event/{event_slug}/")
    player_page_template: str = field(default="/player/{player_slug}/")

    # League Configurations
    leagues: dict[str, LeagueConfig] = field(default_factory=lambda: {
        "liga_al": LeagueConfig(
            league_id="119473",
            name="Liga Alef",
            short_name="Liga Al",
        ),
        "liga_leumit": LeagueConfig(
            league_id="119474",
            name="Liga Leumit",
            short_name="Liga Leumit",
        ),
    })
    default_league: str = field(default="liga_leumit")

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

    # Pagination
    per_page: int = field(default=100)

    def get_league_config(self, league_key: str) -> LeagueConfig:
        """
        Get configuration for a specific league.

        Args:
            league_key: League identifier key (e.g., "liga_leumit").

        Returns:
            LeagueConfig for the specified league.

        Raises:
            KeyError: If the league key is not found.

        Example:
            >>> config = IBasketballConfig()
            >>> league = config.get_league_config("liga_leumit")
            >>> league.league_id
            '119474'
        """
        return self.leagues[league_key]

    def get_events_url(self, league_id: str, page: int = 1) -> str:
        """
        Get the events list URL for a specific league.

        Args:
            league_id: SportsPress league ID.
            page: Page number for pagination.

        Returns:
            str: Full URL for the events endpoint.

        Example:
            >>> config = IBasketballConfig()
            >>> config.get_events_url("119474")
            'https://ibasketball.co.il/wp-json/sportspress/v2/events?leagues=119474&per_page=100&page=1'
        """
        return (
            f"{self.api_base_url}{self.events_endpoint}"
            f"?leagues={league_id}&per_page={self.per_page}&page={page}"
        )

    def get_event_url(self, event_id: str) -> str:
        """
        Get the single event URL for fetching boxscore data.

        Args:
            event_id: SportsPress event ID.

        Returns:
            str: Full URL for the event endpoint.

        Example:
            >>> config = IBasketballConfig()
            >>> config.get_event_url("123456")
            'https://ibasketball.co.il/wp-json/sportspress/v2/events/123456'
        """
        return f"{self.api_base_url}{self.event_endpoint_template.format(event_id=event_id)}"

    def get_standings_url(self, league_id: str) -> str:
        """
        Get the standings URL for a specific league.

        Args:
            league_id: SportsPress league ID.

        Returns:
            str: Full URL for the standings endpoint.

        Example:
            >>> config = IBasketballConfig()
            >>> config.get_standings_url("119474")
            'https://ibasketball.co.il/wp-json/sportspress/v2/tables?leagues=119474'
        """
        return f"{self.api_base_url}{self.standings_endpoint_template.format(league_id=league_id)}"

    def get_teams_url(self, league_id: str | None = None) -> str:
        """
        Get the teams list URL.

        Args:
            league_id: Optional league ID to filter teams.

        Returns:
            str: Full URL for the teams endpoint.

        Example:
            >>> config = IBasketballConfig()
            >>> config.get_teams_url("119474")
            'https://ibasketball.co.il/wp-json/sportspress/v2/teams?leagues=119474&per_page=100'
        """
        url = f"{self.api_base_url}{self.teams_endpoint}?per_page={self.per_page}"
        if league_id:
            url += f"&leagues={league_id}"
        return url

    def get_game_page_url(self, event_slug: str) -> str:
        """
        Get the HTML game page URL for PBP scraping.

        Args:
            event_slug: Event slug from the API.

        Returns:
            str: Full URL for the game HTML page.

        Example:
            >>> config = IBasketballConfig()
            >>> config.get_game_page_url("team-a-vs-team-b")
            'https://ibasketball.co.il/event/team-a-vs-team-b/'
        """
        return f"{self.base_url}{self.game_page_template.format(event_slug=event_slug)}"

    def get_player_page_url(self, player_slug: str) -> str:
        """
        Get the HTML player profile page URL.

        Args:
            player_slug: Player slug from the API.

        Returns:
            str: Full URL for the player profile page.

        Example:
            >>> config = IBasketballConfig()
            >>> config.get_player_page_url("john-smith")
            'https://ibasketball.co.il/player/john-smith/'
        """
        return f"{self.base_url}{self.player_page_template.format(player_slug=player_slug)}"

    def get_available_leagues(self) -> list[str]:
        """
        Get list of available league keys.

        Returns:
            List of league keys.

        Example:
            >>> config = IBasketballConfig()
            >>> config.get_available_leagues()
            ['liga_al', 'liga_leumit']
        """
        return list(self.leagues.keys())
