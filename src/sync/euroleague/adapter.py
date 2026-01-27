"""
Euroleague Adapter Module

Implements BaseLeagueAdapter and BasePlayerInfoAdapter for Euroleague data.
Combines EuroleagueClient, EuroleagueDirectClient, and EuroleagueMapper to
provide normalized data access for the sync infrastructure.

This module exports:
    - EuroleagueAdapter: Unified adapter for Euroleague data

Usage:
    from sqlalchemy.orm import Session
    from src.sync.euroleague import (
        EuroleagueAdapter,
        EuroleagueClient,
        EuroleagueDirectClient,
    )
    from src.sync.euroleague.mapper import EuroleagueMapper

    db = SessionLocal()
    client = EuroleagueClient(db)
    direct_client = EuroleagueDirectClient(db)
    mapper = EuroleagueMapper()

    adapter = EuroleagueAdapter(client, direct_client, mapper)
    seasons = await adapter.get_seasons()
"""

from src.sync.adapters.base import BaseLeagueAdapter, BasePlayerInfoAdapter
from src.sync.euroleague.client import EuroleagueClient
from src.sync.euroleague.direct_client import EuroleagueDirectClient
from src.sync.euroleague.mapper import EuroleagueMapper
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawSeason,
    RawTeam,
)


class EuroleagueAdapter(BaseLeagueAdapter, BasePlayerInfoAdapter):
    """
    Adapter for Euroleague and EuroCup basketball data.

    Implements BaseLeagueAdapter and BasePlayerInfoAdapter to provide
    normalized access to game data, schedules, box scores, play-by-play,
    and player biographical information.

    Uses both the euroleague-api package (for boxscores, PBP, standings)
    and direct XML/JSON APIs (for teams, player profiles).

    Attributes:
        source_name: "euroleague" - unique identifier for this data source.
        client: EuroleagueClient for euroleague-api package access.
        direct_client: EuroleagueDirectClient for XML/JSON APIs.
        mapper: EuroleagueMapper for data transformation.
        competition: Competition code ("E" for Euroleague, "U" for EuroCup).
        configured_seasons: List of seasons to make available.

    Example:
        >>> db = SessionLocal()
        >>> client = EuroleagueClient(db)
        >>> direct_client = EuroleagueDirectClient(db)
        >>> mapper = EuroleagueMapper()
        >>> adapter = EuroleagueAdapter(client, direct_client, mapper)
        >>>
        >>> seasons = await adapter.get_seasons()
        >>> games = await adapter.get_schedule(seasons[0].external_id)
    """

    source_name = "euroleague"

    def __init__(
        self,
        client: EuroleagueClient,
        direct_client: EuroleagueDirectClient,
        mapper: EuroleagueMapper,
        competition: str = "E",
        configured_seasons: list[int] | None = None,
    ) -> None:
        """
        Initialize EuroleagueAdapter.

        Args:
            client: EuroleagueClient for euroleague-api package access.
            direct_client: EuroleagueDirectClient for XML/JSON APIs.
            mapper: EuroleagueMapper for data transformation.
            competition: Competition code ("E" for Euroleague, "U" for EuroCup).
            configured_seasons: List of seasons to make available. Defaults to
                current and previous season.

        Example:
            >>> adapter = EuroleagueAdapter(client, direct_client, mapper)
            >>> # Or for EuroCup
            >>> adapter = EuroleagueAdapter(client, direct_client, mapper, "U")
        """
        self.client = client
        self.direct_client = direct_client
        self.mapper = mapper
        self.competition = competition

        # Default to current and previous season
        if configured_seasons is None:
            from datetime import datetime

            current_year = datetime.now().year
            current_month = datetime.now().month
            # Season starts in October
            current_season = current_year if current_month >= 10 else current_year - 1
            configured_seasons = [current_season, current_season - 1]

        self.configured_seasons = configured_seasons

        # Cache for teams data
        self._teams_cache: dict[str, list[dict]] = {}

    def _parse_season_id(self, season_id: str) -> tuple[str, int]:
        """
        Parse season ID to extract competition and year.

        Args:
            season_id: Season ID like "E2024" or "U2024".

        Returns:
            Tuple of (competition, year).

        Raises:
            ValueError: If season_id format is invalid.
        """
        if len(season_id) < 2:
            raise ValueError(f"Invalid season_id format: {season_id}")

        competition = season_id[0]
        try:
            year = int(season_id[1:])
        except ValueError as e:
            raise ValueError(f"Invalid season_id format: {season_id}") from e

        return competition, year

    def _parse_game_id(self, game_id: str) -> tuple[str, int, int]:
        """
        Parse game ID to extract competition, season, and gamecode.

        Args:
            game_id: Game ID like "E2024_1".

        Returns:
            Tuple of (competition, season, gamecode).

        Raises:
            ValueError: If game_id format is invalid.
        """
        if "_" not in game_id or len(game_id) < 3:
            raise ValueError(f"Invalid game_id format: {game_id}")

        parts = game_id.split("_")
        competition = parts[0][0]

        try:
            season = int(parts[0][1:])
            gamecode = int(parts[1])
        except ValueError as e:
            raise ValueError(f"Invalid game_id format: {game_id}") from e

        return competition, season, gamecode

    async def get_seasons(self) -> list[RawSeason]:
        """
        Fetch available seasons.

        Euroleague doesn't provide a dynamic season list, so this returns
        the configured seasons.

        Returns:
            List of RawSeason objects for configured seasons.

        Example:
            >>> seasons = await adapter.get_seasons()
            >>> for season in seasons:
            ...     print(f"{season.name}: {season.external_id}")
        """
        seasons = []
        for year in self.configured_seasons:
            season = self.mapper.map_season(year, self.competition)
            # Mark the most recent season as current
            if year == max(self.configured_seasons):
                season.is_current = True
            seasons.append(season)

        return seasons

    async def get_teams(self, season_id: str) -> list[RawTeam]:
        """
        Fetch all teams participating in a season.

        Args:
            season_id: External season identifier (e.g., "E2024").

        Returns:
            List of RawTeam objects for the season.

        Raises:
            EuroleagueAPIError: If the request fails.

        Example:
            >>> teams = await adapter.get_teams("E2024")
            >>> for team in teams:
            ...     print(f"{team.name} ({team.external_id})")
        """
        _, year = self._parse_season_id(season_id)

        # Check cache
        if season_id in self._teams_cache:
            teams_data = self._teams_cache[season_id]
        else:
            result = self.direct_client.fetch_teams(year)
            teams_data = result.data
            self._teams_cache[season_id] = teams_data

        return [self.mapper.map_team(t) for t in teams_data]

    async def get_schedule(self, season_id: str) -> list[RawGame]:
        """
        Fetch the game schedule for a season.

        Args:
            season_id: External season identifier (e.g., "E2024").

        Returns:
            List of RawGame objects for the season.

        Raises:
            EuroleagueAPIError: If the request fails.

        Example:
            >>> games = await adapter.get_schedule("E2024")
            >>> final_games = [g for g in games if g.status == "final"]
            >>> print(f"Completed games: {len(final_games)}")
        """
        competition, year = self._parse_season_id(season_id)

        result = self.client.fetch_season_games(year)

        games = []
        for game_data in result.data:
            games.append(self.mapper.map_game(game_data, year, competition))

        return games

    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        """
        Fetch the box score for a completed game.

        Uses the live boxscore API for more complete data, then looks up
        the actual game date from the schedule.

        Args:
            game_id: External game identifier (e.g., "E2024_1").

        Returns:
            RawBoxScore containing game info and player stats.

        Raises:
            EuroleagueAPIError: If the game doesn't exist or request fails.

        Example:
            >>> boxscore = await adapter.get_game_boxscore("E2024_1")
            >>> for player in boxscore.home_players:
            ...     print(f"{player.player_name}: {player.points} pts")
        """
        competition, season, gamecode = self._parse_game_id(game_id)

        # Use live boxscore for more complete data
        result = self.direct_client.fetch_live_boxscore(season, gamecode)

        boxscore = self.mapper.map_boxscore_from_live(
            result.data, gamecode, season, competition
        )

        # Look up actual game date from schedule (live API doesn't include date)
        schedule = await self.get_schedule(game_id.split("_")[0])
        for game in schedule:
            if game.external_id == game_id:
                boxscore.game.game_date = game.game_date
                break

        return boxscore

    async def get_game_pbp(self, game_id: str) -> list[RawPBPEvent]:
        """
        Fetch play-by-play events for a game.

        Args:
            game_id: External game identifier (e.g., "E2024_1").

        Returns:
            List of RawPBPEvent objects.

        Raises:
            EuroleagueAPIError: If the game doesn't exist or request fails.

        Example:
            >>> events = await adapter.get_game_pbp("E2024_1")
            >>> for event in events[:5]:
            ...     print(f"{event.clock} - {event.event_type}")
        """
        _, season, gamecode = self._parse_game_id(game_id)

        # Use live PBP API
        result = self.direct_client.fetch_live_pbp(season, gamecode)

        return self.mapper.map_pbp_from_live(result.data)

    def is_game_final(self, game: RawGame) -> bool:
        """
        Check if a game has been completed.

        Args:
            game: RawGame object to check.

        Returns:
            True if the game is complete (status == "final" and scores exist).

        Example:
            >>> game = await adapter.get_schedule("E2024")[0]
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

        Uses the player XML API for detailed player data.

        Args:
            external_id: External player identifier (e.g., "P011987").

        Returns:
            RawPlayerInfo with biographical data.

        Raises:
            EuroleagueAPIError: If the player doesn't exist or request fails.

        Example:
            >>> player = await adapter.get_player_info("P011987")
            >>> print(f"{player.first_name} {player.last_name}")
            >>> print(f"Height: {player.height_cm}cm")
        """
        # Get current season for the API call
        current_season = max(self.configured_seasons)

        # The API expects player codes without the P prefix
        player_code = external_id.lstrip("P")

        result = self.direct_client.fetch_player(player_code, current_season)

        # Add the external_id (with P prefix) to the data
        data = result.data
        data["code"] = external_id

        return self.mapper.map_player_info(data)

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
            EuroleagueAPIError: If the request fails.

        Example:
            >>> results = await adapter.search_player("Edwards")
            >>> for player in results:
            ...     print(f"{player.first_name} {player.last_name}")
        """
        results: list[RawPlayerInfo] = []
        name_lower = name.lower()

        # Get current season
        current_season = max(self.configured_seasons)
        season_id = f"{self.competition}{current_season}"

        # Get teams
        teams = await self.get_teams(season_id)

        # Filter by team if specified
        if team:
            teams = [t for t in teams if t.external_id == team]

        # Get cached teams data with rosters
        if season_id not in self._teams_cache:
            result = self.direct_client.fetch_teams(current_season)
            self._teams_cache[season_id] = result.data

        teams_data = self._teams_cache[season_id]

        # Search through rosters
        for team_data in teams_data:
            team_code = team_data.get("code", "")

            # Skip if filtering by team and doesn't match
            if team and team_code != team:
                continue

            players = team_data.get("players", [])
            for player_data in players:
                player_name = player_data.get("name", "")
                if name_lower in player_name.lower():
                    # Try to get full player info
                    player_code = player_data.get("code", "")
                    if player_code:
                        try:
                            player_info = await self.get_player_info(player_code)
                            results.append(player_info)
                        except Exception:
                            # Fall back to roster data
                            results.append(
                                self.mapper.map_player_from_roster(
                                    player_data, team_code
                                )
                            )
                    else:
                        results.append(
                            self.mapper.map_player_from_roster(player_data, team_code)
                        )

        return results
