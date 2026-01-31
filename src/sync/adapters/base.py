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
from datetime import datetime

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
    async def get_game_pbp(
        self, game_id: str
    ) -> tuple[list[RawPBPEvent], dict[str, int]]:
        """
        Fetch play-by-play events for a game.

        Returns all recorded events from the game in chronological order,
        plus a mapping from internal player IDs to jersey numbers for
        sources where internal IDs don't match database external IDs.

        Args:
            game_id: External game identifier

        Returns:
            Tuple of (events, player_id_to_jersey) where:
            - events: List of RawPBPEvent objects in chronological order
            - player_id_to_jersey: Dict mapping internal player ID to jersey number
              (empty dict if not needed for this source)

        Raises:
            GameNotFoundError: If the game doesn't exist
            AdapterError: If PBP data is unavailable or request fails

        Example:
            >>> events, player_jerseys = await adapter.get_game_pbp("game-123")
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

    async def get_games_since(
        self, since: datetime, season_id: str | None = None
    ) -> list[RawGame]:
        """
        Fetch games played since a specific date.

        Used for recent sync operations (e.g., daily sync of last 7 days).
        Default implementation filters the schedule by date.

        Args:
            since: Datetime to filter games from (inclusive).
            season_id: Optional season to filter. If None, uses current season.

        Returns:
            List of RawGame objects played on or after the specified date.

        Example:
            >>> from datetime import datetime, timedelta
            >>> since = datetime.now() - timedelta(days=7)
            >>> recent_games = await adapter.get_games_since(since)
        """
        # Default implementation: get schedule and filter by date
        # Subclasses can override for more efficient API calls
        if season_id is None:
            seasons = await self.get_seasons()
            if not seasons:
                return []
            # Get current season (first one is usually current)
            season_id = seasons[0].external_id

        games = await self.get_schedule(season_id)
        return [
            g for g in games
            if g.game_date and g.game_date >= since and self.is_game_final(g)
        ]

    async def get_available_seasons(self) -> list[str]:
        """
        Get list of available season identifiers.

        Returns normalized season names that can be used with sync operations.

        Returns:
            List of season name strings (e.g., ["2024-25", "2023-24", "2022-23"])

        Example:
            >>> seasons = await adapter.get_available_seasons()
            >>> print(f"Available: {', '.join(seasons)}")
        """
        seasons = await self.get_seasons()
        return [s.name for s in seasons]


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
        self,
        team_external_id: str,  # noqa: ARG002
        fetch_profiles: bool = True,  # noqa: ARG002
    ) -> list[tuple[str, str, RawPlayerInfo | None]]:
        """
        Fetch team roster with player IDs and optionally bio data.

        Returns list of tuples: (player_id, player_name, RawPlayerInfo or None).
        The RawPlayerInfo may be None if fetching the profile fails.

        This is an optional method - default implementation returns empty list.

        Args:
            team_external_id: External team identifier.
            fetch_profiles: If True, fetch individual player profiles for full
                bio data. If False, use roster data only (faster but may have
                less complete information). Default True.

        Returns:
            List of (player_id, player_name, player_info) tuples.

        Example:
            >>> roster = await adapter.get_team_roster("100", fetch_profiles=False)
            >>> for player_id, name, info in roster:
            ...     print(f"{name}: {info.positions if info else 'N/A'}")
        """
        return []
