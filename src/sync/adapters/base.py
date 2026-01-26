"""
Base Adapter Module

Provides abstract base classes for sync adapters that fetch data from external
basketball data sources. Each data source (Winner League, Euroleague, etc.)
should implement these interfaces.

The adapters are split into two types:
- BaseLeagueAdapter: For league-specific data (games, schedules, stats)
- BasePlayerInfoAdapter: For player biographical information (may come from different sources)

Usage:
    from src.sync.adapters.base import BaseLeagueAdapter

    class WinnerAdapter(BaseLeagueAdapter):
        source_name = "winner"

        async def get_seasons(self) -> list[RawSeason]:
            # Fetch seasons from Winner API
            ...

        async def get_teams(self, season_id: str) -> list[RawTeam]:
            # Fetch teams for a season
            ...
"""

from abc import ABC, abstractmethod

from src.sync.types import (
    RawBoxScore,
    RawGame,
    RawPBPEvent,
    RawPlayerInfo,
    RawSeason,
    RawTeam,
)


class BaseLeagueAdapter(ABC):
    """
    Abstract base class for league data adapters.

    League adapters are responsible for fetching game data, schedules,
    box scores, and play-by-play data from external sources. Each
    concrete implementation handles a specific data source.

    Attributes:
        source_name: Unique identifier for this data source (e.g., "winner")

    Example:
        >>> class WinnerAdapter(BaseLeagueAdapter):
        ...     source_name = "winner"
        ...
        ...     async def get_seasons(self) -> list[RawSeason]:
        ...         # Implementation
        ...         pass
    """

    source_name: str = ""

    @abstractmethod
    async def get_seasons(self) -> list[RawSeason]:
        """
        Fetch all available seasons from the data source.

        Returns:
            List of RawSeason objects representing available seasons

        Raises:
            AdapterError: If the request fails
            ConnectionError: If connection to the source fails

        Example:
            >>> adapter = WinnerAdapter()
            >>> seasons = await adapter.get_seasons()
            >>> for season in seasons:
            ...     print(f"{season.name}: {season.external_id}")
        """
        ...

    @abstractmethod
    async def get_teams(self, season_id: str) -> list[RawTeam]:
        """
        Fetch all teams participating in a season.

        Args:
            season_id: External season identifier

        Returns:
            List of RawTeam objects for the season

        Raises:
            SeasonNotFoundError: If the season doesn't exist
            AdapterError: If the request fails

        Example:
            >>> teams = await adapter.get_teams("2024-25")
            >>> for team in teams:
            ...     print(f"{team.name} ({team.short_name})")
        """
        ...

    @abstractmethod
    async def get_schedule(self, season_id: str) -> list[RawGame]:
        """
        Fetch the game schedule for a season.

        Returns all games (past and future) for the specified season.
        Past games will have scores and status="final", future games
        will have status="scheduled".

        Args:
            season_id: External season identifier

        Returns:
            List of RawGame objects representing all games in the season

        Raises:
            SeasonNotFoundError: If the season doesn't exist
            AdapterError: If the request fails

        Example:
            >>> games = await adapter.get_schedule("2024-25")
            >>> final_games = [g for g in games if g.status == "final"]
        """
        ...

    @abstractmethod
    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        """
        Fetch the box score for a completed game.

        Returns detailed player statistics for both teams in the game.

        Args:
            game_id: External game identifier

        Returns:
            RawBoxScore containing game info and player stats

        Raises:
            GameNotFoundError: If the game doesn't exist
            AdapterError: If the game hasn't been played yet or request fails

        Example:
            >>> boxscore = await adapter.get_game_boxscore("game-123")
            >>> for player in boxscore.home_players:
            ...     print(f"{player.player_name}: {player.points} pts")
        """
        ...

    @abstractmethod
    async def get_game_pbp(self, game_id: str) -> list[RawPBPEvent]:
        """
        Fetch play-by-play events for a game.

        Returns all recorded events from the game in chronological order.

        Args:
            game_id: External game identifier

        Returns:
            List of RawPBPEvent objects in chronological order

        Raises:
            GameNotFoundError: If the game doesn't exist
            AdapterError: If PBP data is unavailable or request fails

        Example:
            >>> events = await adapter.get_game_pbp("game-123")
            >>> shots = [e for e in events if e.event_type == "shot"]
        """
        ...

    @abstractmethod
    def is_game_final(self, game: RawGame) -> bool:
        """
        Check if a game has been completed.

        Different sources may use different status values, so this method
        allows each adapter to implement its own logic for determining
        if a game is final.

        Args:
            game: RawGame object to check

        Returns:
            True if the game is complete, False otherwise

        Example:
            >>> game = await adapter.get_schedule("2024-25")[0]
            >>> if adapter.is_game_final(game):
            ...     boxscore = await adapter.get_game_boxscore(game.external_id)
        """
        ...


class BasePlayerInfoAdapter(ABC):
    """
    Abstract base class for player biographical information adapters.

    Player info adapters fetch player bio data which may come from
    different sources than game data. This includes height, birth date,
    position, and other biographical information.

    Attributes:
        source_name: Unique identifier for this data source

    Example:
        >>> class WinnerPlayerAdapter(BasePlayerInfoAdapter):
        ...     source_name = "winner"
        ...
        ...     async def get_player_info(self, external_id: str) -> RawPlayerInfo:
        ...         # Implementation
        ...         pass
    """

    source_name: str = ""

    @abstractmethod
    async def get_player_info(self, external_id: str) -> RawPlayerInfo:
        """
        Fetch biographical information for a player.

        Args:
            external_id: External player identifier

        Returns:
            RawPlayerInfo with biographical data

        Raises:
            PlayerNotFoundError: If the player doesn't exist
            AdapterError: If the request fails

        Example:
            >>> player = await adapter.get_player_info("player-123")
            >>> print(f"{player.first_name} {player.last_name}, {player.height_cm}cm")
        """
        ...

    @abstractmethod
    async def search_player(
        self, name: str, team: str | None = None
    ) -> list[RawPlayerInfo]:
        """
        Search for players by name, optionally filtering by team.

        Args:
            name: Player name to search for (partial match supported)
            team: Optional team name to filter results

        Returns:
            List of RawPlayerInfo matching the search criteria

        Raises:
            AdapterError: If the request fails

        Example:
            >>> results = await adapter.search_player("James", team="Lakers")
            >>> for player in results:
            ...     print(f"{player.first_name} {player.last_name}")
        """
        ...

    async def get_team_roster(
        self, team_external_id: str
    ) -> list[tuple[str, str, RawPlayerInfo | None]]:
        """
        Fetch team roster with player IDs and optionally bio data.

        Returns list of tuples: (player_id, player_name, RawPlayerInfo or None).
        The RawPlayerInfo may be None if fetching the profile fails.

        This is an optional method - default implementation returns empty list.

        Args:
            team_external_id: External team identifier.

        Returns:
            List of (player_id, player_name, player_info) tuples.

        Example:
            >>> roster = await adapter.get_team_roster("100")
            >>> for player_id, name, info in roster:
            ...     print(f"{name}: {info.position if info else 'N/A'}")
        """
        return []
