"""
iBasketball Adapter Module

Implements BaseLeagueAdapter and BasePlayerInfoAdapter for iBasketball data.
Combines IBasketballApiClient, IBasketballScraper, and IBasketballMapper to
provide normalized data access for the sync infrastructure.

This module exports:
    - IBasketballAdapter: Unified adapter for iBasketball data

Usage:
    from sqlalchemy.orm import Session
    from src.sync.ibasketball import (
        IBasketballAdapter,
        IBasketballApiClient,
        IBasketballScraper,
    )
    from src.sync.ibasketball.mapper import IBasketballMapper

    db = SessionLocal()
    client = IBasketballApiClient(db)
    scraper = IBasketballScraper(db)
    mapper = IBasketballMapper()

    adapter = IBasketballAdapter(client, mapper, scraper)
    adapter.set_league("liga_leumit")

    seasons = await adapter.get_seasons()
    teams = await adapter.get_teams(seasons[0].external_id)
"""

from src.schemas.enums import GameStatus
from src.sync.adapters.base import BaseLeagueAdapter, BasePlayerInfoAdapter
from src.sync.ibasketball.api_client import IBasketballApiClient
from src.sync.ibasketball.config import IBasketballConfig
from src.sync.ibasketball.exceptions import IBasketballLeagueNotFoundError
from src.sync.ibasketball.mapper import IBasketballMapper
from src.sync.ibasketball.scraper import IBasketballScraper
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawSeason,
    RawTeam,
)


class IBasketballAdapter(BaseLeagueAdapter, BasePlayerInfoAdapter):
    """
    Adapter for iBasketball (Israeli Basketball) data.

    Implements BaseLeagueAdapter and BasePlayerInfoAdapter to provide
    normalized access to game data, schedules, box scores, play-by-play,
    and player biographical information from iBasketball.co.il.

    Supports multiple leagues (Liga Al, Liga Leumit) via the set_league method.

    Attributes:
        source_name: "ibasketball" - unique identifier for this data source.
        client: IBasketballApiClient for REST API access.
        mapper: IBasketballMapper for data transformation.
        scraper: IBasketballScraper for HTML scraping (optional).
        config: IBasketballConfig with league configurations.
        _active_league_key: Currently active league key.

    Example:
        >>> db = SessionLocal()
        >>> client = IBasketballApiClient(db)
        >>> scraper = IBasketballScraper(db)
        >>> mapper = IBasketballMapper()
        >>> adapter = IBasketballAdapter(client, mapper, scraper)
        >>>
        >>> # Set active league
        >>> adapter.set_league("liga_leumit")
        >>>
        >>> seasons = await adapter.get_seasons()
        >>> games = await adapter.get_schedule(seasons[0].external_id)
    """

    source_name = "ibasketball"

    def __init__(
        self,
        client: IBasketballApiClient,
        mapper: IBasketballMapper,
        scraper: IBasketballScraper | None = None,
        config: IBasketballConfig | None = None,
    ) -> None:
        """
        Initialize IBasketballAdapter.

        Args:
            client: IBasketballApiClient for REST API access.
            mapper: IBasketballMapper for data transformation.
            scraper: IBasketballScraper for HTML scraping (optional).
            config: Optional configuration. Uses defaults if not provided.

        Example:
            >>> adapter = IBasketballAdapter(client, mapper, scraper)
        """
        self.client = client
        self.mapper = mapper
        self.scraper = scraper
        self.config = config or IBasketballConfig()

        # Active league tracking
        self._active_league_key: str = self.config.default_league

        # Cache for events data
        self._events_cache: dict[str, list[dict]] = {}

    def set_league(self, league_key: str) -> None:
        """
        Set the active league for subsequent operations.

        Args:
            league_key: League identifier key (e.g., "liga_leumit", "liga_al").

        Raises:
            IBasketballLeagueNotFoundError: If the league key is not configured.

        Example:
            >>> adapter.set_league("liga_leumit")
            >>> # Now all operations use Liga Leumit
            >>> seasons = await adapter.get_seasons()
        """
        if league_key not in self.config.leagues:
            raise IBasketballLeagueNotFoundError(
                f"League '{league_key}' not found",
                league_key=league_key,
                available_leagues=list(self.config.leagues.keys()),
            )
        self._active_league_key = league_key
        # Clear cache when switching leagues
        self._events_cache.clear()

    def get_available_leagues(self) -> list[str]:
        """
        Get list of available league keys.

        Returns:
            List of league keys that can be used with set_league().

        Example:
            >>> adapter.get_available_leagues()
            ['liga_al', 'liga_leumit']
        """
        return self.config.get_available_leagues()

    def _get_league_id(self) -> str:
        """Get the SportsPress league ID for the active league."""
        league_config = self.config.get_league_config(self._active_league_key)
        return league_config.league_id

    def _get_league_name(self) -> str:
        """Get the display name for the active league."""
        league_config = self.config.get_league_config(self._active_league_key)
        return league_config.name

    def _get_events_data(self, force: bool = False) -> list[dict]:
        """
        Get events data for current league, using cache if available.

        Args:
            force: If True, bypass cache and refetch.

        Returns:
            List of event dictionaries from API.
        """
        league_id = self._get_league_id()

        if league_id not in self._events_cache or force:
            result = self.client.fetch_all_events(league_id, force=force)
            if isinstance(result.data, list):
                self._events_cache[league_id] = result.data
            else:
                self._events_cache[league_id] = []

        return self._events_cache.get(league_id, [])

    async def get_seasons(self) -> list[RawSeason]:
        """
        Fetch all available seasons from iBasketball.

        iBasketball doesn't expose explicit season data, so we infer
        the current season from event dates for the active league.

        Returns:
            List of RawSeason objects (typically just current season).

        Raises:
            IBasketballAPIError: If the request fails.
            IBasketballParseError: If the response cannot be parsed.

        Example:
            >>> adapter.set_league("liga_leumit")
            >>> seasons = await adapter.get_seasons()
            >>> for season in seasons:
            ...     print(f"{season.name}: {season.external_id}")
        """
        events_data = self._get_events_data()

        season = self.mapper.map_season(
            league_key=self._active_league_key,
            league_name=self._get_league_name(),
            events_data=events_data,
        )

        return [season]

    async def get_teams(self, season_id: str) -> list[RawTeam]:  # noqa: ARG002
        """
        Fetch all teams participating in the current league.

        Extracts unique teams from the events response.

        Args:
            season_id: External season identifier (not used, included for interface).

        Returns:
            List of RawTeam objects for the league.

        Raises:
            IBasketballAPIError: If the request fails.

        Example:
            >>> adapter.set_league("liga_leumit")
            >>> teams = await adapter.get_teams("2024-25")
            >>> for team in teams:
            ...     print(f"{team.name} ({team.external_id})")
        """
        events_data = self._get_events_data()
        return self.mapper.extract_teams_from_events(events_data)

    async def get_schedule(self, season_id: str) -> list[RawGame]:  # noqa: ARG002
        """
        Fetch the game schedule for the current league.

        Returns all events from the SportsPress API for the active league.

        Args:
            season_id: External season identifier (not used, included for interface).

        Returns:
            List of RawGame objects for the league.

        Raises:
            IBasketballAPIError: If the request fails.

        Example:
            >>> adapter.set_league("liga_leumit")
            >>> games = await adapter.get_schedule("2024-25")
            >>> final_games = [g for g in games if g.status == "final"]
            >>> print(f"Completed games: {len(final_games)}")
        """
        events_data = self._get_events_data()
        games = []
        for event_data in events_data:
            games.append(self.mapper.map_game(event_data))
        return games

    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        """
        Fetch the box score for a completed game.

        Args:
            game_id: External game/event identifier.

        Returns:
            RawBoxScore containing game info and player stats.

        Raises:
            IBasketballAPIError: If the game doesn't exist or request fails.
            IBasketballParseError: If the response cannot be parsed.

        Example:
            >>> boxscore = await adapter.get_game_boxscore("123456")
            >>> for player in boxscore.home_players:
            ...     print(f"{player.player_name}: {player.points} pts")
        """
        result = self.client.fetch_event(game_id)

        if not isinstance(result.data, dict):
            raise ValueError(f"Unexpected data type for event {game_id}")

        return self.mapper.map_boxscore(result.data)

    async def get_game_pbp(
        self, game_id: str
    ) -> tuple[list[RawPBPEvent], dict[str, int]]:
        """
        Fetch play-by-play events for a game.

        PBP data is scraped from the HTML game page since it's not
        available via the REST API.

        Args:
            game_id: External game/event identifier.

        Returns:
            Tuple of (events, player_id_to_jersey). Jersey mapping is empty
            for iBasketball since external IDs match database.

        Raises:
            IBasketballAPIError: If the game doesn't exist or request fails.
            IBasketballParseError: If the page cannot be parsed.

        Example:
            >>> events, _ = await adapter.get_game_pbp("123456")
            >>> for event in events[:5]:
            ...     print(f"{event.clock} - {event.event_type}")
        """
        if not self.scraper:
            return [], {}

        # First get event data to get the slug
        result = self.client.fetch_event(game_id)
        if not isinstance(result.data, dict):
            return [], {}

        # Get event slug from data
        event_slug = result.data.get("slug", "")
        if not event_slug:
            # Try to construct from link
            link = result.data.get("link", "")
            if "/event/" in link:
                event_slug = link.split("/event/")[-1].strip("/")

        if not event_slug:
            return [], {}

        # Fetch and parse PBP
        pbp = self.scraper.fetch_game_pbp(event_slug)

        # Convert to list of dicts for mapper
        events_data = []
        for event in pbp.events:
            events_data.append(
                {
                    "period": event.period,
                    "clock": event.clock,
                    "type": event.type,
                    "player": event.player,
                    "team_id": event.team_id,
                    "team_name": event.team_name,
                    "success": event.success,
                }
            )

        return self.mapper.map_pbp_events(events_data), {}

    def is_game_final(self, game: RawGame) -> bool:
        """
        Check if a game has been completed.

        Args:
            game: RawGame object to check.

        Returns:
            True if the game is complete (status == "final" and scores exist).

        Example:
            >>> games = await adapter.get_schedule("2024-25")
            >>> game = games[0]
            >>> if adapter.is_game_final(game):
            ...     boxscore = await adapter.get_game_boxscore(game.external_id)
        """
        return (
            game.status == GameStatus.FINAL
            and game.home_score is not None
            and game.away_score is not None
        )

    async def get_player_info(self, external_id: str) -> RawPlayerInfo:
        """
        Fetch biographical information for a player.

        Uses the HTML scraper to fetch player profile data if available.

        Args:
            external_id: External player identifier (slug).

        Returns:
            RawPlayerInfo with biographical data.

        Raises:
            IBasketballAPIError: If the player doesn't exist or request fails.
            IBasketballParseError: If the profile cannot be parsed.

        Example:
            >>> player = await adapter.get_player_info("john-smith")
            >>> print(f"{player.first_name} {player.last_name}")
            >>> print(f"Height: {player.height_cm}cm")
        """
        if not self.scraper:
            # Return minimal info if scraper not available
            return RawPlayerInfo(
                external_id=external_id,
                first_name="",
                last_name=external_id.replace("-", " ").title(),
            )

        profile = self.scraper.fetch_player(external_id)

        return self.mapper.map_player_info(
            player_id=external_id,
            data={
                "name": profile.name,
                "team_name": profile.team_name,
                "position": profile.position,
                "height_cm": profile.height_cm,
                "birth_date": profile.birth_date,
                "nationality": profile.nationality,
            },
        )

    async def search_player(
        self, name: str, team: str | None = None  # noqa: ARG002
    ) -> list[RawPlayerInfo]:
        """
        Search for players by name.

        Note: iBasketball doesn't provide a player search API, so this
        method returns an empty list. Use get_player_info with a known
        player slug instead.

        Args:
            name: Player name to search for (not implemented).
            team: Optional team external ID to filter by (not implemented).

        Returns:
            Empty list (search not supported).

        Example:
            >>> results = await adapter.search_player("Smith")
            >>> # Returns [] - use get_player_info instead
        """
        # Player search not available via iBasketball
        # Would need to scrape player lists from team pages
        return []
