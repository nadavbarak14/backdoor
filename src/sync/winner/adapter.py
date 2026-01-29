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

from src.schemas.enums import GameStatus
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
        self._current_season_id: str | None = None
        # Cache for historical schedule (keyed by season_id)
        self._historical_schedule_cache: dict[str, list[RawGame]] = {}
        # Cache for historical team info (keyed by segevstats team_id)
        self._historical_teams_cache: dict[str, RawTeam] = {}
        # Cache mapping segevstats external_id -> basket.co.il source_game_id
        self._game_id_mapping: dict[str, str] = {}

    def _get_current_season_id(self) -> str:
        """
        Get the current season ID from the API.

        Returns:
            Season ID string (e.g., "2025-26").
        """
        if self._current_season_id is None:
            games_data = self._get_games_data()
            games = games_data.get("games", [])
            if games:
                first_game = games[0]
                game_year = first_game.get("game_year")
                if game_year:
                    start_year = game_year - 1
                    self._current_season_id = f"{start_year}-{str(game_year)[-2:]}"
                else:
                    # Fallback to date inference
                    game_date = self.mapper.parse_datetime(
                        first_game.get("GameDate", first_game.get("game_date_txt", ""))
                    )
                    year = game_date.year
                    month = game_date.month
                    if month >= 9:
                        self._current_season_id = f"{year}-{str(year + 1)[-2:]}"
                    else:
                        self._current_season_id = f"{year - 1}-{str(year)[-2:]}"
            else:
                # Default to current year
                from datetime import date

                year = date.today().year
                self._current_season_id = f"{year}-{str(year + 1)[-2:]}"
        return self._current_season_id

    def _is_current_season(self, season_id: str) -> bool:
        """Check if the requested season is the current season."""
        current = self._get_current_season_id()
        return season_id == current

    def _parse_season_year(self, season_id: str) -> int:
        """
        Parse season ID to get the ending year.

        Args:
            season_id: Season ID like "2024-25".

        Returns:
            Ending year (e.g., 2025 for "2024-25").
        """
        try:
            parts = season_id.split("-")
            start_year = int(parts[0])
            if len(parts) > 1:
                end_suffix = int(parts[1])
                if end_suffix < 100:
                    century = (start_year // 100) * 100
                    return century + end_suffix
                return end_suffix
            return start_year + 1
        except (ValueError, IndexError):
            from datetime import date

            return date.today().year

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

    async def get_teams(self, season_id: str) -> list[RawTeam]:
        """
        Fetch all teams participating in a season.

        For current season, extracts teams from games_all response.
        For historical seasons, extracts teams from scraped results.

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
        if self._is_current_season(season_id):
            games_data = self._get_games_data()
            return self.mapper.extract_teams_from_games(games_data)
        else:
            # For historical seasons, get_schedule populates the team cache
            await self.get_schedule(season_id)

            # Return teams from cache (populated during schedule fetch)
            return list(self._historical_teams_cache.values())

    async def get_schedule(self, season_id: str) -> list[RawGame]:
        """
        Fetch the game schedule for a season.

        For current season, returns games from the games_all JSON endpoint.
        For historical seasons, scrapes game IDs from results page and
        constructs RawGame objects from boxscore data.

        Args:
            season_id: External season identifier (e.g., "2024-25").

        Returns:
            List of RawGame objects for the season.

        Raises:
            WinnerAPIError: If the request fails.

        Example:
            >>> games = await adapter.get_schedule("2024-25")
            >>> final_games = [g for g in games if g.status == "final"]
            >>> print(f"Completed games: {len(final_games)}")
        """
        if self._is_current_season(season_id):
            # Current season: use JSON API
            games_data = self._get_games_data()
            games = []
            for game_data in games_data.get("games", []):
                raw_game = self.mapper.map_game(game_data)
                games.append(raw_game)
                # Cache mapping from segevstats ID to basket.co.il ID
                if raw_game.source_game_id:
                    self._game_id_mapping[raw_game.external_id] = raw_game.source_game_id
            return games
        else:
            # Historical season: scrape results page for game IDs
            return await self._get_historical_schedule(season_id)

    async def _get_historical_schedule(self, season_id: str) -> list[RawGame]:
        """
        Fetch historical game schedule by scraping results page.

        For each game, fetches the segevstats game ID from the game-zone page
        and team IDs from the boxscore so that sync can work correctly.

        Results are cached to avoid duplicate fetches when called from
        both get_teams and get_schedule.

        Args:
            season_id: External season identifier (e.g., "2024-25").

        Returns:
            List of RawGame objects for the historical season.
        """
        # Check cache first
        if season_id in self._historical_schedule_cache:
            return self._historical_schedule_cache[season_id]

        year = self._parse_season_year(season_id)
        results = self.scraper.fetch_historical_results(year)

        games = []
        for game_result in results.games:
            if game_result.game_id:
                # Clean basket.co.il game ID (remove any trailing junk)
                basket_game_id = game_result.game_id.split("#")[0].strip()
                if not basket_game_id:
                    continue

                # Get the segevstats game ID from game-zone page
                segevstats_id = self.scraper.fetch_segevstats_game_id(basket_game_id)
                if not segevstats_id:
                    # Skip games without segevstats mapping
                    continue

                # Fetch boxscore to get team IDs and PBP to get team names
                try:
                    boxscore_result = self.client.fetch_boxscore(segevstats_id)
                    boxscore = self.mapper.map_boxscore(boxscore_result.data)
                    home_team_id = boxscore.game.home_team_external_id
                    away_team_id = boxscore.game.away_team_external_id

                    # Fetch PBP to get team names
                    pbp_result = self.client.fetch_pbp(segevstats_id)
                    pbp_data = pbp_result.data
                    game_info = pbp_data.get("result", {}).get("gameInfo", {})
                    home_team_info = game_info.get("homeTeam", {})
                    away_team_info = game_info.get("awayTeam", {})

                    # Cache team info for later use in get_teams
                    if (
                        home_team_id
                        and home_team_id not in self._historical_teams_cache
                    ):
                        self._historical_teams_cache[home_team_id] = RawTeam(
                            external_id=home_team_id,
                            name=home_team_info.get("name", f"Team {home_team_id}"),
                        )
                    if (
                        away_team_id
                        and away_team_id not in self._historical_teams_cache
                    ):
                        self._historical_teams_cache[away_team_id] = RawTeam(
                            external_id=away_team_id,
                            name=away_team_info.get("name", f"Team {away_team_id}"),
                        )
                except Exception:
                    # Skip games without valid boxscore
                    continue

                # Create RawGame with all IDs filled
                game = RawGame(
                    external_id=segevstats_id,
                    game_date=boxscore.game.game_date,
                    home_team_external_id=home_team_id,
                    away_team_external_id=away_team_id,
                    home_score=boxscore.game.home_score,
                    away_score=boxscore.game.away_score,
                    status="final" if boxscore.game.home_score else "scheduled",
                )
                games.append(game)

        # Cache the results
        self._historical_schedule_cache[season_id] = games
        return games

    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        """
        Fetch the box score for a completed game.

        Uses basket.co.il game-zone page to get boxscore with correct player IDs.
        Falls back to segevstats if game-zone scraping fails.

        Args:
            game_id: External game identifier (segevstats ID).

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
        # Try to get basket.co.il game ID from cache
        basket_game_id = self._game_id_mapping.get(game_id)

        if basket_game_id:
            try:
                # Use scraper to get boxscore with correct player IDs
                gamezone_boxscore = self.scraper.fetch_game_boxscore(basket_game_id)
                return self.mapper.map_gamezone_boxscore(gamezone_boxscore)
            except Exception:
                # Fall back to segevstats if scraping fails
                pass

        # Fallback: use segevstats (player IDs won't match)
        result = self.client.fetch_boxscore(game_id)
        return self.mapper.map_boxscore(result.data)

    async def get_game_pbp(
        self, game_id: str
    ) -> tuple[list[RawPBPEvent], dict[str, int]]:
        """
        Fetch play-by-play events for a game.

        Events are returned with inferred links between related events
        (e.g., assists linked to shots, rebounds linked to misses).

        Also returns a mapping from internal player IDs to jersey numbers
        for player matching when internal IDs don't match database.

        Args:
            game_id: External game identifier.

        Returns:
            Tuple of (events, player_id_to_jersey) where:
            - events: List of RawPBPEvent objects with inferred links
            - player_id_to_jersey: Dict mapping internal player ID to jersey number

        Raises:
            WinnerAPIError: If the game doesn't exist or request fails.

        Example:
            >>> events, player_jerseys = await adapter.get_game_pbp("12345")
            >>> for event in events[:5]:
            ...     print(f"{event.clock} - {event.event_type}")
            >>> player_jerseys["1000"]  # Player 1000 wears jersey #1
            1
        """
        result = self.client.fetch_pbp(game_id)
        events = self.mapper.map_pbp_events(result.data)
        player_id_to_jersey = self.mapper.extract_player_id_to_jersey(result.data)
        return events, player_id_to_jersey

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
            game.status == GameStatus.FINAL
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
        self, team_external_id: str, fetch_profiles: bool = True
    ) -> list[tuple[str, str, RawPlayerInfo | None]]:
        """
        Fetch team roster with player IDs and bio data.

        Returns list of tuples: (player_id, player_name, RawPlayerInfo or None).

        When fetch_profiles=True (default), fetches individual player profiles
        to get full bio data (height, birthdate). This is slower but provides
        complete player information.

        Args:
            team_external_id: External team identifier.
            fetch_profiles: If True, fetch individual player profiles for bio data.

        Returns:
            List of (player_id, player_name, player_info) tuples.

        Example:
            >>> roster = await adapter.get_team_roster("100")
            >>> for player_id, name, info in roster:
            ...     print(f"{name}: height={info.height_cm if info else 'N/A'}")
        """
        results: list[tuple[str, str, RawPlayerInfo | None]] = []

        try:
            roster = self.scraper.fetch_team_roster(team_external_id)
            for player in roster.players:
                player_info = None

                if fetch_profiles and player.player_id:
                    # Fetch individual player profile for full bio data
                    try:
                        profile = self.scraper.fetch_player(player.player_id)
                        player_info = self.mapper.map_player_info(profile)
                    except Exception:
                        # Fall back to roster data if profile fetch fails
                        player_info = self.mapper.map_roster_player_info(player)
                else:
                    # Just use roster data (position only)
                    player_info = self.mapper.map_roster_player_info(player)

                results.append((player.player_id, player.name, player_info))
        except Exception:
            # Roster fetch failed
            pass

        return results
