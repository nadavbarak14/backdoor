"""
NBA Adapter Module

Implements BaseLeagueAdapter for NBA data.
Combines NBAClient and NBAMapper to provide normalized data access
for the sync infrastructure.

This module exports:
    - NBAAdapter: Unified adapter for NBA data

Usage:
    from src.sync.nba import NBAAdapter
    from src.sync.nba.client import NBAClient
    from src.sync.nba.mapper import NBAMapper
    from src.sync.nba.config import NBAConfig

    config = NBAConfig()
    client = NBAClient(config)
    mapper = NBAMapper()

    adapter = NBAAdapter(client, mapper, config)
    seasons = await adapter.get_seasons()
"""

from src.sync.adapters.base import BaseLeagueAdapter
from src.sync.nba.client import NBAClient
from src.sync.nba.config import NBAConfig
from src.sync.nba.mapper import NBAMapper
from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawSeason,
    RawTeam,
)


class NBAAdapter(BaseLeagueAdapter):
    """
    Adapter for NBA basketball data.

    Implements BaseLeagueAdapter to provide normalized access to game data,
    schedules, box scores, and play-by-play information from the NBA Stats API.

    Uses the nba_api package for API access.

    Attributes:
        source_name: "nba" - unique identifier for this data source.
        client: NBAClient for API access.
        mapper: NBAMapper for data transformation.
        config: NBAConfig with settings and configured seasons.

    Example:
        >>> config = NBAConfig()
        >>> client = NBAClient(config)
        >>> mapper = NBAMapper()
        >>> adapter = NBAAdapter(client, mapper, config)
        >>>
        >>> seasons = await adapter.get_seasons()
        >>> games = await adapter.get_schedule(seasons[0].external_id)
    """

    source_name = "nba"

    def __init__(
        self,
        client: NBAClient,
        mapper: NBAMapper,
        config: NBAConfig | None = None,
    ) -> None:
        """
        Initialize NBAAdapter.

        Args:
            client: NBAClient for NBA API access.
            mapper: NBAMapper for data transformation.
            config: NBAConfig with settings. Uses client's config if not provided.

        Example:
            >>> adapter = NBAAdapter(client, mapper)
            >>> # Or with custom config
            >>> adapter = NBAAdapter(client, mapper, NBAConfig(requests_per_minute=10))
        """
        self.client = client
        self.mapper = mapper
        self.config = config or client.config

        # Cache for schedule data (game_id -> full game data)
        self._schedule_cache: dict[str, dict[str, RawGame]] = {}

    def _parse_season_id(self, season_id: str) -> str:
        """
        Parse season ID to extract the NBA season string.

        Args:
            season_id: Season ID like "NBA2023-24".

        Returns:
            Season string like "2023-24".

        Raises:
            ValueError: If season_id format is invalid.

        Example:
            >>> adapter._parse_season_id("NBA2023-24")
            '2023-24'
        """
        if season_id.startswith("NBA"):
            return season_id[3:]
        return season_id

    async def get_seasons(self) -> list[RawSeason]:
        """
        Fetch available seasons.

        Returns the configured seasons from NBAConfig.

        Returns:
            List of RawSeason objects for configured seasons.

        Example:
            >>> seasons = await adapter.get_seasons()
            >>> for season in seasons:
            ...     print(f"{season.name}: {season.external_id}")
        """
        if not self.config.configured_seasons:
            return []

        seasons = []
        for season_str in self.config.configured_seasons:
            season = self.mapper.map_season(season_str)
            # Mark the first (most recent) season as current
            if season_str == self.config.configured_seasons[0]:
                season.is_current = True
            seasons.append(season)

        return seasons

    async def get_teams(self, season_id: str) -> list[RawTeam]:
        """
        Fetch all NBA teams.

        Args:
            season_id: External season identifier (e.g., "NBA2023-24").
                Currently unused as NBA teams are static.

        Returns:
            List of RawTeam objects for all NBA teams.

        Example:
            >>> teams = await adapter.get_teams("NBA2023-24")
            >>> for team in teams:
            ...     print(f"{team.name} ({team.external_id})")
        """
        season = self._parse_season_id(season_id)
        teams_data = self.client.get_teams(season)
        return [self.mapper.map_team(t) for t in teams_data]

    async def get_schedule(self, season_id: str) -> list[RawGame]:
        """
        Fetch the game schedule for a season.

        Note: The NBA API returns one row per team per game, so we need to
        combine rows to get complete game data with both teams' info.

        Args:
            season_id: External season identifier (e.g., "NBA2023-24").

        Returns:
            List of RawGame objects for the season.

        Example:
            >>> games = await adapter.get_schedule("NBA2023-24")
            >>> final_games = [g for g in games if g.status == "final"]
            >>> print(f"Completed games: {len(final_games)}")
        """
        season = self._parse_season_id(season_id)

        # Check cache
        if season_id in self._schedule_cache:
            return list(self._schedule_cache[season_id].values())

        # Fetch schedule data
        schedule_data = self.client.get_schedule(season)

        # Combine rows by game_id
        games_map: dict[str, RawGame] = {}

        for game_data in schedule_data:
            partial_game = self.mapper.map_game_from_schedule(game_data)
            game_id = partial_game.external_id

            if game_id not in games_map:
                games_map[game_id] = partial_game
            else:
                # Merge with existing game data
                existing = games_map[game_id]

                # Fill in missing team info
                if (
                    not existing.home_team_external_id
                    and partial_game.home_team_external_id
                ):
                    existing.home_team_external_id = partial_game.home_team_external_id
                if (
                    not existing.away_team_external_id
                    and partial_game.away_team_external_id
                ):
                    existing.away_team_external_id = partial_game.away_team_external_id

                # Fill in missing scores
                if existing.home_score is None and partial_game.home_score is not None:
                    existing.home_score = partial_game.home_score
                if existing.away_score is None and partial_game.away_score is not None:
                    existing.away_score = partial_game.away_score

                # Update status if we have more info
                if partial_game.status == "final":
                    existing.status = "final"

        # Cache and return
        self._schedule_cache[season_id] = games_map
        return list(games_map.values())

    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        """
        Fetch the box score for a completed game.

        Args:
            game_id: External game identifier (e.g., "0022300001").

        Returns:
            RawBoxScore containing game info and player stats.

        Raises:
            NBANotFoundError: If the game doesn't exist.
            NBAAPIError: If the game hasn't been played yet or request fails.

        Example:
            >>> boxscore = await adapter.get_game_boxscore("0022300001")
            >>> for player in boxscore.home_players:
            ...     print(f"{player.player_name}: {player.points} pts")
        """
        boxscore_data = self.client.get_boxscore(game_id)
        return self.mapper.map_boxscore(boxscore_data, game_id)

    async def get_game_pbp(self, game_id: str) -> list[RawPBPEvent]:
        """
        Fetch play-by-play events for a game.

        Args:
            game_id: External game identifier (e.g., "0022300001").

        Returns:
            List of RawPBPEvent objects.

        Raises:
            NBANotFoundError: If the game doesn't exist.
            NBAAPIError: If PBP data is unavailable or request fails.

        Example:
            >>> events = await adapter.get_game_pbp("0022300001")
            >>> for event in events[:5]:
            ...     print(f"{event.clock} - {event.event_type}")
        """
        pbp_data = self.client.get_pbp(game_id)
        return self.mapper.map_pbp_events(pbp_data)

    def is_game_final(self, game: RawGame) -> bool:
        """
        Check if a game has been completed.

        Args:
            game: RawGame object to check.

        Returns:
            True if the game is complete (status == "final" and scores exist).

        Example:
            >>> game = await adapter.get_schedule("NBA2023-24")[0]
            >>> if adapter.is_game_final(game):
            ...     boxscore = await adapter.get_game_boxscore(game.external_id)
        """
        return (
            game.status == "final"
            and game.home_score is not None
            and game.away_score is not None
        )
