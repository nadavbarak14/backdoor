"""
Winner League Adapter Module

Implements BaseLeagueAdapter and BasePlayerInfoAdapter for Winner League data.
Combines WinnerClient, WinnerScraper, and WinnerMapper to provide normalized
data access for the sync infrastructure.

This module exports:
    - WinnerAdapter: Unified adapter for Winner League data

Usage:
    from sqlalchemy.orm import Session
    from src.sync.winner import WinnerAdapter, WinnerClient, WinnerScraper
    from src.sync.winner.mapper import WinnerMapper

    db = SessionLocal()
    client = WinnerClient(db)
    scraper = WinnerScraper(db)
    mapper = WinnerMapper()

    adapter = WinnerAdapter(client, scraper, mapper)

    seasons = await adapter.get_seasons()
    teams = await adapter.get_teams(seasons[0].external_id)
"""

from src.sync.adapters.base import BaseLeagueAdapter, BasePlayerInfoAdapter
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawSeason,
    RawTeam,
)
from src.sync.winner.client import WinnerClient
from src.sync.winner.mapper import WinnerMapper
from src.sync.winner.scraper import WinnerScraper


class WinnerAdapter(BaseLeagueAdapter, BasePlayerInfoAdapter):
    """
    Adapter for Winner League (Israeli Basketball) data.

    Implements BaseLeagueAdapter and BasePlayerInfoAdapter to provide
    normalized access to game data, schedules, box scores, play-by-play,
    and player biographical information.

    Attributes:
        source_name: "winner" - unique identifier for this data source.
        client: WinnerClient for JSON API access.
        scraper: WinnerScraper for HTML scraping.
        mapper: WinnerMapper for data transformation.

    Example:
        >>> db = SessionLocal()
        >>> client = WinnerClient(db)
        >>> scraper = WinnerScraper(db)
        >>> mapper = WinnerMapper()
        >>> adapter = WinnerAdapter(client, scraper, mapper)
        >>>
        >>> seasons = await adapter.get_seasons()
        >>> games = await adapter.get_schedule(seasons[0].external_id)
    """

    source_name = "winner"

    def __init__(
        self,
        client: WinnerClient,
        scraper: WinnerScraper,
        mapper: WinnerMapper,
    ) -> None:
        """
        Initialize WinnerAdapter.

        Args:
            client: WinnerClient for JSON API access.
            scraper: WinnerScraper for HTML scraping.
            mapper: WinnerMapper for data transformation.

        Example:
            >>> adapter = WinnerAdapter(client, scraper, mapper)
        """
        self.client = client
        self.scraper = scraper
        self.mapper = mapper

        # Cache for games_all data to avoid repeated fetches
        self._games_cache: dict | None = None

    def _get_games_data(self, force: bool = False) -> dict:
        """
        Get games_all data, using cache if available.

        The Winner API may return the data in different formats:
        - List containing a dict: [{"games": [...]}]
        - Direct dict: {"games": [...]}

        This method normalizes both formats to a dict.

        Args:
            force: If True, bypass cache and refetch.

        Returns:
            Games data dictionary with "games" key.
        """
        if self._games_cache is None or force:
            result = self.client.fetch_games_all(force=force)
            data = result.data

            # Handle list wrapper - API sometimes returns [{"games": [...]}]
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            self._games_cache = data
        return self._games_cache

    async def get_seasons(self) -> list[RawSeason]:
        """
        Fetch all available seasons from Winner League.

        Winner League typically provides only current season data through
        the games_all endpoint. Historical seasons may be available through
        scraping.

        Returns:
            List of RawSeason objects (usually just current season).

        Raises:
            WinnerAPIError: If the request fails.
            WinnerParseError: If the response cannot be parsed.

        Example:
            >>> seasons = await adapter.get_seasons()
            >>> for season in seasons:
            ...     print(f"{season.name}: {season.external_id}")
        """
        games_data = self._get_games_data()

        # Extract season from response
        season_str = games_data.get("season", "")
        if not season_str:
            # Try to infer from game dates
            games = games_data.get("games", [])
            if games:
                first_game = games[0]
                game_date = self.mapper.parse_datetime(first_game.get("GameDate", ""))
                # Determine season based on game date
                year = game_date.year
                month = game_date.month
                if month >= 9:  # Season starts in September
                    season_str = f"{year}-{str(year + 1)[-2:]}"
                else:
                    season_str = f"{year - 1}-{str(year)[-2:]}"

        season = self.mapper.map_season(season_str, games_data)
        return [season]

    async def get_teams(self, season_id: str) -> list[RawTeam]:  # noqa: ARG002
        """
        Fetch all teams participating in a season.

        Extracts unique teams from the games_all response.

        Args:
            season_id: External season identifier (e.g., "2023-24").

        Returns:
            List of RawTeam objects for the season.

        Raises:
            WinnerAPIError: If the request fails.

        Example:
            >>> teams = await adapter.get_teams("2023-24")
            >>> for team in teams:
            ...     print(f"{team.name} ({team.external_id})")
        """
        games_data = self._get_games_data()
        return self.mapper.extract_teams_from_games(games_data)

    async def get_schedule(self, season_id: str) -> list[RawGame]:  # noqa: ARG002
        """
        Fetch the game schedule for a season.

        Returns all games from the games_all endpoint.

        Args:
            season_id: External season identifier.

        Returns:
            List of RawGame objects for the season.

        Raises:
            WinnerAPIError: If the request fails.

        Example:
            >>> games = await adapter.get_schedule("2023-24")
            >>> final_games = [g for g in games if g.status == "final"]
            >>> print(f"Completed games: {len(final_games)}")
        """
        games_data = self._get_games_data()
        games = []
        for game_data in games_data.get("games", []):
            games.append(self.mapper.map_game(game_data))
        return games

    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        """
        Fetch the box score for a completed game.

        Args:
            game_id: External game identifier.

        Returns:
            RawBoxScore containing game info and player stats.

        Raises:
            WinnerAPIError: If the game doesn't exist or request fails.
            WinnerParseError: If the response cannot be parsed.

        Example:
            >>> boxscore = await adapter.get_game_boxscore("12345")
            >>> for player in boxscore.home_players:
            ...     print(f"{player.player_name}: {player.points} pts")
        """
        result = self.client.fetch_boxscore(game_id)
        return self.mapper.map_boxscore(result.data)

    async def get_game_pbp(self, game_id: str) -> list[RawPBPEvent]:
        """
        Fetch play-by-play events for a game.

        Events are returned with inferred links between related events
        (e.g., assists linked to shots, rebounds linked to misses).

        Args:
            game_id: External game identifier.

        Returns:
            List of RawPBPEvent objects with inferred links.

        Raises:
            WinnerAPIError: If the game doesn't exist or request fails.

        Example:
            >>> events = await adapter.get_game_pbp("12345")
            >>> for event in events[:5]:
            ...     print(f"{event.clock} - {event.event_type}")
        """
        result = self.client.fetch_pbp(game_id)
        return self.mapper.map_pbp_events(result.data)

    def is_game_final(self, game: RawGame) -> bool:
        """
        Check if a game has been completed.

        Args:
            game: RawGame object to check.

        Returns:
            True if the game is complete (status == "final" and scores exist).

        Example:
            >>> game = await adapter.get_schedule("2023-24")[0]
            >>> if adapter.is_game_final(game):
            ...     boxscore = await adapter.get_game_boxscore(game.external_id)
        """
        return (
            game.status == "final"
            and game.home_score is not None
            and game.away_score is not None
        )

    async def get_player_info(self, external_id: str) -> RawPlayerInfo:
        """
        Fetch biographical information for a player.

        Uses the HTML scraper to fetch player profile data.

        Args:
            external_id: External player identifier.

        Returns:
            RawPlayerInfo with biographical data.

        Raises:
            WinnerAPIError: If the player doesn't exist or request fails.
            WinnerParseError: If the profile cannot be parsed.

        Example:
            >>> player = await adapter.get_player_info("1001")
            >>> print(f"{player.first_name} {player.last_name}")
            >>> print(f"Height: {player.height_cm}cm")
        """
        profile = self.scraper.fetch_player(external_id)
        return self.mapper.map_player_info(profile)

    async def search_player(
        self, name: str, team: str | None = None
    ) -> list[RawPlayerInfo]:
        """
        Search for players by name.

        Searches through team rosters to find matching players.

        Args:
            name: Player name to search for (partial match).
            team: Optional team external ID to filter by.

        Returns:
            List of RawPlayerInfo matching the search criteria.

        Raises:
            WinnerAPIError: If the request fails.

        Example:
            >>> results = await adapter.search_player("Smith")
            >>> for player in results:
            ...     print(f"{player.first_name} {player.last_name}")
        """
        results: list[RawPlayerInfo] = []
        name_lower = name.lower()

        # Get all teams
        games_data = self._get_games_data()
        teams = self.mapper.extract_teams_from_games(games_data)

        # Filter by team if specified
        if team:
            teams = [t for t in teams if t.external_id == team]

        # Search through team rosters
        for raw_team in teams:
            try:
                roster = self.scraper.fetch_team_roster(raw_team.external_id)
                for player in roster.players:
                    if name_lower in player.name.lower():
                        # Fetch full profile for matching players
                        try:
                            profile = self.scraper.fetch_player(player.player_id)
                            results.append(self.mapper.map_player_info(profile))
                        except Exception:
                            # If profile fetch fails, skip this player
                            continue
            except Exception:
                # If roster fetch fails, skip this team
                continue

        return results

    async def get_team_roster(
        self, team_external_id: str
    ) -> list[tuple[str, str, RawPlayerInfo | None]]:
        """
        Fetch team roster with player IDs and bio data from roster page.

        Returns list of tuples: (player_id, player_name, RawPlayerInfo or None).
        Bio data (position) is extracted from the roster page directly for
        efficiency - no individual player profile fetches are needed.

        Args:
            team_external_id: External team identifier.

        Returns:
            List of (player_id, player_name, player_info) tuples.

        Example:
            >>> roster = await adapter.get_team_roster("100")
            >>> for player_id, name, info in roster:
            ...     print(f"{name}: {info.position if info else 'N/A'}")
        """
        results: list[tuple[str, str, RawPlayerInfo | None]] = []

        try:
            roster = self.scraper.fetch_team_roster(team_external_id)
            for player in roster.players:
                # Create RawPlayerInfo from roster data (no profile fetch needed)
                player_info = self.mapper.map_roster_player_info(player)
                results.append((player.player_id, player.name, player_info))
        except Exception:
            # Roster fetch failed
            pass

        return results
