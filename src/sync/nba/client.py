"""
NBA API Client Module

Wraps the nba_api package to provide a unified interface for fetching NBA data.
Handles rate limiting, retries, and error conversion.

This module exports:
    - NBAClient: Main client class for NBA API access

Usage:
    from src.sync.nba.client import NBAClient
    from src.sync.nba.config import NBAConfig

    config = NBAConfig()
    client = NBAClient(config)

    # Get teams
    teams = client.get_teams(season="2023-24")

    # Get schedule
    games = client.get_schedule(season="2023-24")

    # Get boxscore
    boxscore = client.get_boxscore(game_id="0022300001")
"""

import time
from dataclasses import dataclass, field
from typing import Any

from nba_api.stats.endpoints import (
    BoxScoreTraditionalV3,
    CommonTeamRoster,
    LeagueGameFinder,
    PlayByPlayV3,
)
from nba_api.stats.static import teams as static_teams

from src.sync.nba.config import NBAConfig
from src.sync.nba.exceptions import (
    NBAAPIError,
    NBAConnectionError,
    NBANotFoundError,
    NBARateLimitError,
    NBATimeoutError,
)


@dataclass
class NBAClient:
    """
    Client for NBA Stats API using nba_api package.

    Provides methods for fetching NBA data with built-in rate limiting,
    retries, and error handling.

    Attributes:
        config: NBAConfig with rate limits and settings.
        _last_request_time: Timestamp of last request for rate limiting.

    Example:
        >>> config = NBAConfig()
        >>> client = NBAClient(config)
        >>> teams = client.get_teams("2023-24")
        >>> for team in teams:
        ...     print(team["full_name"])
    """

    config: NBAConfig = field(default_factory=NBAConfig)
    _last_request_time: float = field(default=0.0, init=False)

    def _rate_limit(self) -> None:
        """
        Apply rate limiting between requests.

        Sleeps if necessary to maintain the configured request rate.
        """
        elapsed = time.time() - self._last_request_time
        delay = self.config.delay_between_requests

        if elapsed < delay:
            time.sleep(delay - elapsed)

        self._last_request_time = time.time()

    def _make_request(
        self, endpoint_class: type, retries: int = 0, **kwargs: Any
    ) -> Any:
        """
        Make a request to the NBA API with retries.

        Args:
            endpoint_class: nba_api endpoint class.
            retries: Current retry count.
            **kwargs: Arguments to pass to the endpoint.

        Returns:
            Endpoint response object.

        Raises:
            NBAAPIError: If the request fails after all retries.
            NBARateLimitError: If rate limited.
            NBATimeoutError: If request times out.
            NBAConnectionError: If connection fails.
        """
        self._rate_limit()

        try:
            # Add timeout and proxy from config
            kwargs.setdefault("timeout", int(self.config.request_timeout))
            if self.config.proxy:
                kwargs.setdefault("proxy", self.config.proxy)
            if self.config.headers:
                kwargs.setdefault("headers", self.config.headers)

            return endpoint_class(**kwargs)

        except TimeoutError as e:
            if retries < self.config.max_retries:
                delay = min(
                    self.config.retry_base_delay * (2**retries),
                    self.config.retry_max_delay,
                )
                time.sleep(delay)
                return self._make_request(endpoint_class, retries + 1, **kwargs)
            raise NBATimeoutError(str(e)) from e

        except ConnectionError as e:
            if retries < self.config.max_retries:
                delay = min(
                    self.config.retry_base_delay * (2**retries),
                    self.config.retry_max_delay,
                )
                time.sleep(delay)
                return self._make_request(endpoint_class, retries + 1, **kwargs)
            raise NBAConnectionError(str(e)) from e

        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "429" in error_msg:
                raise NBARateLimitError() from e
            if retries < self.config.max_retries:
                delay = min(
                    self.config.retry_base_delay * (2**retries),
                    self.config.retry_max_delay,
                )
                time.sleep(delay)
                return self._make_request(endpoint_class, retries + 1, **kwargs)
            raise NBAAPIError(f"NBA API request failed: {e}") from e

    def get_teams(self, _season: str | None = None) -> list[dict]:
        """
        Get all NBA teams.

        Uses static team data from nba_api, optionally filtered by season.

        Args:
            season: Optional season string (e.g., "2023-24"). Currently unused
                as team data is static.

        Returns:
            List of team dictionaries with id, full_name, abbreviation, etc.

        Example:
            >>> client = NBAClient(NBAConfig())
            >>> teams = client.get_teams("2023-24")
            >>> len(teams)
            30
            >>> teams[0]["full_name"]
            'Atlanta Hawks'
        """
        # nba_api provides static team data
        # Note: This returns all teams regardless of season
        teams = static_teams.get_teams()
        return teams

    def get_team_roster(self, team_id: int, season: str) -> list[dict]:
        """
        Get roster for a specific team and season.

        Args:
            team_id: NBA team ID.
            season: Season string (e.g., "2023-24").

        Returns:
            List of player dictionaries from the roster.

        Raises:
            NBANotFoundError: If team or season not found.
            NBAAPIError: If request fails.

        Example:
            >>> roster = client.get_team_roster(1610612737, "2023-24")
            >>> for player in roster:
            ...     print(player["PLAYER"])
        """
        try:
            endpoint = self._make_request(
                CommonTeamRoster, team_id=team_id, season=season
            )
            data = endpoint.get_normalized_dict()
            return data.get("CommonTeamRoster", [])
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise NBANotFoundError("team", str(team_id)) from e
            raise

    def get_schedule(
        self,
        season: str,
        season_type: str = "Regular Season",
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """
        Get games for a season.

        Args:
            season: Season string (e.g., "2023-24").
            season_type: Type of season ("Regular Season", "Playoffs", etc.).
            date_from: Optional start date filter (MM/DD/YYYY).
            date_to: Optional end date filter (MM/DD/YYYY).

        Returns:
            List of game dictionaries.

        Raises:
            NBAAPIError: If request fails.

        Example:
            >>> games = client.get_schedule("2023-24")
            >>> len(games) > 0
            True
            >>> games[0]["GAME_ID"]
            '0022300001'
        """
        kwargs: dict[str, Any] = {
            "season_nullable": season,
            "season_type_nullable": season_type,
            "league_id_nullable": "00",  # NBA
        }

        if date_from:
            kwargs["date_from_nullable"] = date_from
        if date_to:
            kwargs["date_to_nullable"] = date_to

        endpoint = self._make_request(LeagueGameFinder, **kwargs)
        data = endpoint.get_normalized_dict()
        return data.get("LeagueGameFinderResults", [])

    def get_boxscore(self, game_id: str) -> dict:
        """
        Get boxscore for a specific game.

        Args:
            game_id: NBA game ID (e.g., "0022300001").

        Returns:
            Dictionary with boxscore data including player stats.

        Raises:
            NBANotFoundError: If game not found.
            NBAAPIError: If request fails.

        Example:
            >>> boxscore = client.get_boxscore("0022300001")
            >>> "PlayerStats" in boxscore
            True
        """
        try:
            endpoint = self._make_request(BoxScoreTraditionalV3, game_id=game_id)
            return endpoint.get_normalized_dict()
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise NBANotFoundError("game", game_id) from e
            raise

    def get_pbp(self, game_id: str) -> list[dict]:
        """
        Get play-by-play data for a specific game.

        Args:
            game_id: NBA game ID (e.g., "0022300001").

        Returns:
            List of play-by-play event dictionaries.

        Raises:
            NBANotFoundError: If game not found.
            NBAAPIError: If request fails.

        Example:
            >>> events = client.get_pbp("0022300001")
            >>> len(events) > 0
            True
            >>> events[0]["EVENTNUM"]
            1
        """
        try:
            endpoint = self._make_request(PlayByPlayV3, game_id=game_id)
            data = endpoint.get_normalized_dict()
            return data.get("PlayByPlay", [])
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise NBANotFoundError("game", game_id) from e
            raise

    def get_game_info(self, game_id: str) -> dict | None:
        """
        Get game metadata from boxscore.

        Args:
            game_id: NBA game ID.

        Returns:
            Game info dictionary or None if not found.

        Example:
            >>> info = client.get_game_info("0022300001")
            >>> info["GAME_DATE"]
            '2023-10-24'
        """
        try:
            boxscore = self.get_boxscore(game_id)
            # Game info is typically in TeamStats or as part of the response
            team_stats = boxscore.get("TeamStats", [])
            if team_stats:
                # Extract game-level info from team stats
                return {
                    "GAME_ID": game_id,
                    "GAME_DATE_EST": team_stats[0].get("GAME_DATE_EST"),
                }
            return None
        except NBANotFoundError:
            return None
