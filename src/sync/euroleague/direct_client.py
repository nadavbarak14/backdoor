"""
Euroleague Direct Client Module

Provides the EuroleagueDirectClient class for fetching data directly from
Euroleague APIs not covered by the euroleague-api package. Handles XML parsing
for teams and player profile endpoints.

This module exports:
    - EuroleagueDirectClient: Direct HTTP client for Euroleague APIs
    - TeamData: Dataclass for team information
    - PlayerData: Dataclass for player profile information
    - RosterPlayer: Dataclass for player in team roster

Usage:
    from sqlalchemy.orm import Session
    from src.sync.euroleague.direct_client import EuroleagueDirectClient

    db = SessionLocal()
    with EuroleagueDirectClient(db) as client:
        teams = client.fetch_teams(2024)
        print(f"Fetched {len(teams.data)} teams")
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
import xmltodict
from sqlalchemy.orm import Session

from src.models.sync_cache import SyncCache
from src.sync.euroleague.config import EuroleagueConfig
from src.sync.euroleague.exceptions import (
    EuroleagueAPIError,
    EuroleagueParseError,
    EuroleagueRateLimitError,
    EuroleagueTimeoutError,
)
from src.sync.winner.rate_limiter import RateLimiter, calculate_backoff


@dataclass
class RosterPlayer:
    """
    Player information from team roster.

    Attributes:
        code: Player code (e.g., '011987').
        name: Player full name.
        dorsal: Jersey number.
        position: Playing position.
        country_code: Country code (e.g., 'USA').
        country_name: Full country name.

    Example:
        >>> player = RosterPlayer(
        ...     code='011987',
        ...     name='EDWARDS, CARSEN',
        ...     dorsal='3',
        ...     position='Guard',
        ...     country_code='USA',
        ...     country_name='United States of America'
        ... )
    """

    code: str
    name: str
    dorsal: str | None = None
    position: str | None = None
    country_code: str | None = None
    country_name: str | None = None


@dataclass
class TeamData:
    """
    Team information from teams API.

    Attributes:
        code: Team code (e.g., 'BER').
        tv_code: TV broadcast code.
        name: Team full name.
        country_code: Country code.
        country_name: Full country name.
        arena_name: Home arena name.
        players: List of roster players.

    Example:
        >>> team = TeamData(
        ...     code='BER',
        ...     tv_code='BER',
        ...     name='ALBA Berlin',
        ...     country_code='GER',
        ...     country_name='Germany',
        ...     arena_name='UBER ARENA',
        ...     players=[RosterPlayer(...)]
        ... )
    """

    code: str
    tv_code: str | None = None
    name: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    arena_name: str | None = None
    website: str | None = None
    players: list[RosterPlayer] = field(default_factory=list)


@dataclass
class PlayerData:
    """
    Player profile information from players API.

    Attributes:
        name: Player full name.
        height: Height in meters.
        birthdate: Birth date string.
        country: Country name.
        club_code: Current team code.
        club_name: Current team name.
        dorsal: Jersey number.
        position: Playing position.
        stats: Dictionary of season stats.

    Example:
        >>> player = PlayerData(
        ...     name='EDWARDS, CARSEN',
        ...     height='1.8',
        ...     birthdate='12 March, 1998',
        ...     country='United States of America',
        ...     club_code='MUN',
        ...     club_name='FC Bayern Munich',
        ...     position='Guard'
        ... )
    """

    name: str
    height: str | None = None
    birthdate: str | None = None
    country: str | None = None
    club_code: str | None = None
    club_name: str | None = None
    dorsal: str | None = None
    position: str | None = None
    stats: dict = field(default_factory=dict)


@dataclass
class CacheResult:
    """
    Result from a cached fetch operation.

    Contains the fetched data along with caching metadata to indicate
    whether the data is new or unchanged from the previous fetch.

    Attributes:
        data: The fetched data.
        changed: True if data differs from cached version.
        fetched_at: Timestamp when data was fetched.
        cache_id: UUID of the cache entry.
        from_cache: True if data was served from cache without HTTP request.
    """

    data: dict | list
    changed: bool
    fetched_at: datetime
    cache_id: str
    from_cache: bool = False


class EuroleagueDirectClient:
    """
    Direct HTTP client for Euroleague APIs not covered by euroleague-api.

    Handles XML parsing for teams and player profile endpoints.
    All responses are cached in the database with checksum-based change detection.

    Attributes:
        db: SQLAlchemy database session.
        config: Configuration settings.
        rate_limiter: Token bucket rate limiter.
        _client: httpx HTTP client instance.

    Example:
        >>> db = SessionLocal()
        >>> with EuroleagueDirectClient(db) as client:
        ...     # Fetch teams with rosters
        ...     teams = client.fetch_teams(2024)
        ...     for team in teams.data:
        ...         print(f"{team['name']}: {len(team['players'])} players")
        ...
        ...     # Fetch player profile
        ...     player = client.fetch_player('011987', 2024)
        ...     print(f"Height: {player.data['height']}")
    """

    SOURCE = "euroleague"

    def __init__(
        self,
        db: Session,
        config: EuroleagueConfig | None = None,
    ) -> None:
        """
        Initialize EuroleagueDirectClient.

        Args:
            db: SQLAlchemy database session for caching.
            config: Optional configuration. Uses defaults if not provided.

        Example:
            >>> db = SessionLocal()
            >>> client = EuroleagueDirectClient(db)
        """
        self.db = db
        self.config = config or EuroleagueConfig()
        self.rate_limiter = RateLimiter(
            requests_per_second=self.config.requests_per_second,
            burst_size=self.config.burst_size,
        )
        self._client: httpx.Client | None = None

    def __enter__(self) -> "EuroleagueDirectClient":
        """
        Context manager entry - create HTTP client.

        Returns:
            EuroleagueDirectClient: Self for method chaining.
        """
        self._client = httpx.Client(
            timeout=self.config.request_timeout,
            headers={"User-Agent": self.config.user_agent},
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit - close HTTP client.

        Args:
            exc_type: Exception type if raised.
            exc_val: Exception value if raised.
            exc_tb: Exception traceback if raised.
        """
        if self._client:
            self._client.close()
            self._client = None

    @property
    def client(self) -> httpx.Client:
        """
        Get the HTTP client, creating one if needed.

        Returns:
            httpx.Client: The HTTP client instance.
        """
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.config.request_timeout,
                headers={"User-Agent": self.config.user_agent},
            )
        return self._client

    def close(self) -> None:
        """
        Close the HTTP client.

        Call this when not using the context manager to clean up resources.
        """
        if self._client:
            self._client.close()
            self._client = None

    def _compute_hash(self, data: dict | list) -> str:
        """
        Compute SHA-256 hash of data for change detection.

        Args:
            data: Dictionary or list to hash.

        Returns:
            str: Hex-encoded SHA-256 hash.
        """
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _get_cache(
        self,
        resource_type: str,
        resource_id: str,
    ) -> SyncCache | None:
        """
        Get cached entry from database.

        Args:
            resource_type: Type of resource.
            resource_id: Resource identifier.

        Returns:
            SyncCache if found, None otherwise.
        """
        return (
            self.db.query(SyncCache)
            .filter(
                SyncCache.source == self.SOURCE,
                SyncCache.resource_type == resource_type,
                SyncCache.resource_id == resource_id,
            )
            .first()
        )

    def _save_cache(
        self,
        resource_type: str,
        resource_id: str,
        data: dict | list,
        http_status: int | None = None,
    ) -> tuple[SyncCache, bool]:
        """
        Save or update cache entry.

        Args:
            resource_type: Type of resource.
            resource_id: Resource identifier.
            data: Data to cache.
            http_status: HTTP status code.

        Returns:
            Tuple of (cache entry, changed flag).
        """
        content_hash = self._compute_hash(data)
        now = datetime.now(UTC)

        cache = self._get_cache(resource_type, resource_id)

        if cache:
            changed = cache.content_hash != content_hash

            if changed:
                cache.raw_data = data
                cache.content_hash = content_hash
                cache.fetched_at = now
                cache.http_status = http_status
                self.db.commit()
            else:
                cache.fetched_at = now
                self.db.commit()

            return cache, changed
        else:
            cache = SyncCache(
                source=self.SOURCE,
                resource_type=resource_type,
                resource_id=resource_id,
                raw_data=data,
                content_hash=content_hash,
                fetched_at=now,
                http_status=http_status,
            )
            self.db.add(cache)
            self.db.commit()
            self.db.refresh(cache)

            return cache, True

    def _fetch_xml(
        self,
        url: str,
        resource_type: str,
        resource_id: str,
    ) -> dict:
        """
        Fetch XML from URL with rate limiting and retries.

        Args:
            url: URL to fetch.
            resource_type: Type of resource (for error messages).
            resource_id: Resource identifier (for error messages).

        Returns:
            dict: Parsed XML as dictionary.

        Raises:
            EuroleagueAPIError: On HTTP errors.
            EuroleagueParseError: On XML parse errors.
            EuroleagueTimeoutError: On request timeout.
            EuroleagueRateLimitError: On rate limit (HTTP 429).
        """
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                self.rate_limiter.acquire()
                response = self.client.get(url)

                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get(
                            "Retry-After", self.config.retry_base_delay
                        )
                    )
                    raise EuroleagueRateLimitError(
                        f"Rate limited by server for {resource_type}",
                        retry_after=retry_after,
                    )

                if response.status_code >= 400:
                    raise EuroleagueAPIError(
                        f"HTTP {response.status_code} fetching {resource_type}",
                        status_code=response.status_code,
                        url=url,
                        response_body=response.text[:500] if response.text else None,
                    )

                try:
                    return xmltodict.parse(response.text)
                except Exception as e:
                    raise EuroleagueParseError(
                        f"Invalid XML response: {e}",
                        resource_type=resource_type,
                        resource_id=resource_id,
                        raw_data=response.text[:500] if response.text else None,
                    ) from e

            except httpx.TimeoutException as e:
                last_error = EuroleagueTimeoutError(
                    f"Request timed out for {resource_type}",
                    timeout=self.config.request_timeout,
                    url=url,
                )
                if attempt < self.config.max_retries:
                    delay = calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise last_error from e

            except EuroleagueRateLimitError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = e.retry_after or calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise

            except httpx.RequestError as e:
                last_error = EuroleagueAPIError(
                    f"Request failed for {resource_type}: {e}",
                    url=url,
                )
                if attempt < self.config.max_retries:
                    delay = calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise last_error from e

        if last_error:
            raise last_error
        raise EuroleagueAPIError(
            f"Failed to fetch {resource_type} after retries", url=url
        )

    def _fetch_json(
        self,
        url: str,
        resource_type: str,
        resource_id: str,
    ) -> dict:
        """
        Fetch JSON from URL with rate limiting and retries.

        Args:
            url: URL to fetch.
            resource_type: Type of resource (for error messages).
            resource_id: Resource identifier (for error messages).

        Returns:
            dict: Parsed JSON response.

        Raises:
            EuroleagueAPIError: On HTTP errors.
            EuroleagueParseError: On JSON parse errors.
            EuroleagueTimeoutError: On request timeout.
            EuroleagueRateLimitError: On rate limit (HTTP 429).
        """
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                self.rate_limiter.acquire()
                response = self.client.get(url)

                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get(
                            "Retry-After", self.config.retry_base_delay
                        )
                    )
                    raise EuroleagueRateLimitError(
                        f"Rate limited by server for {resource_type}",
                        retry_after=retry_after,
                    )

                if response.status_code >= 400:
                    raise EuroleagueAPIError(
                        f"HTTP {response.status_code} fetching {resource_type}",
                        status_code=response.status_code,
                        url=url,
                        response_body=response.text[:500] if response.text else None,
                    )

                try:
                    return response.json()
                except Exception as e:
                    raise EuroleagueParseError(
                        f"Invalid JSON response: {e}",
                        resource_type=resource_type,
                        resource_id=resource_id,
                        raw_data=response.text[:500] if response.text else None,
                    ) from e

            except httpx.TimeoutException as e:
                last_error = EuroleagueTimeoutError(
                    f"Request timed out for {resource_type}",
                    timeout=self.config.request_timeout,
                    url=url,
                )
                if attempt < self.config.max_retries:
                    delay = calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise last_error from e

            except EuroleagueRateLimitError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = e.retry_after or calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise

            except httpx.RequestError as e:
                last_error = EuroleagueAPIError(
                    f"Request failed for {resource_type}: {e}",
                    url=url,
                )
                if attempt < self.config.max_retries:
                    delay = calculate_backoff(
                        attempt,
                        self.config.retry_base_delay,
                        self.config.retry_max_delay,
                    )
                    time.sleep(delay)
                    continue
                raise last_error from e

        if last_error:
            raise last_error
        raise EuroleagueAPIError(
            f"Failed to fetch {resource_type} after retries", url=url
        )

    def _parse_teams(self, xml_data: dict) -> list[dict]:
        """
        Parse teams XML into list of team dictionaries.

        Args:
            xml_data: Parsed XML data from xmltodict.

        Returns:
            list[dict]: List of team dictionaries with players.
        """
        teams = []
        clubs = xml_data.get("clubs", {}).get("club", [])

        # Handle single club (not a list)
        if isinstance(clubs, dict):
            clubs = [clubs]

        for club in clubs:
            team = {
                "code": club.get("@code"),
                "tv_code": club.get("@tvcode"),
                "name": club.get("name"),
                "country_code": club.get("countrycode"),
                "country_name": club.get("countryname"),
                "website": club.get("website"),
                "players": [],
            }

            # Parse arena
            arena = club.get("arena", {})
            if isinstance(arena, dict):
                team["arena_name"] = arena.get("@name")

            # Parse players
            players = club.get("player", [])
            if isinstance(players, dict):
                players = [players]

            for player in players:
                if isinstance(player, dict):
                    team["players"].append(
                        {
                            "code": player.get("@code"),
                            "name": player.get("@name"),
                            "dorsal": player.get("@dorsal"),
                            "position": player.get("@position"),
                            "country_code": player.get("@countrycode"),
                            "country_name": player.get("@countryname"),
                        }
                    )

            teams.append(team)

        return teams

    def _parse_player(self, xml_data: dict) -> dict:
        """
        Parse player XML into dictionary.

        Args:
            xml_data: Parsed XML data from xmltodict.

        Returns:
            dict: Player profile dictionary.
        """
        player = xml_data.get("player", {})

        result = {
            "name": player.get("name"),
            "height": player.get("height"),
            "birthdate": player.get("birthdate"),
            "country": player.get("country"),
            "club_code": player.get("clubcode"),
            "club_name": player.get("clubname"),
            "dorsal": player.get("dorsal"),
            "position": player.get("position"),
        }

        # Parse stats
        stats = player.get("stats", {})
        if stats:
            result["stats"] = stats

        return result

    def fetch_teams(self, season: int, force: bool = False) -> CacheResult:
        """
        Fetch all teams with rosters for a season.

        Retrieves team information including player rosters from the
        Euroleague teams API (XML).

        Args:
            season: The season year.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: List of team dictionaries with players.

        Example:
            >>> result = client.fetch_teams(2024)
            >>> for team in result.data:
            ...     print(f"{team['name']}: {len(team['players'])} players")
        """
        resource_type = "teams"
        resource_id = self.config.get_season_code(season)

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        url = self.config.get_teams_url(season)
        xml_data = self._fetch_xml(url, resource_type, resource_id)
        data = self._parse_teams(xml_data)

        cache, changed = self._save_cache(
            resource_type, resource_id, data, http_status=200
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_player(
        self, player_code: str, season: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch player profile with stats.

        Retrieves detailed player information including height, birthdate,
        nationality, and season statistics.

        Args:
            player_code: The player code (e.g., '011987').
            season: The season year.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Player profile dictionary.

        Example:
            >>> result = client.fetch_player('011987', 2024)
            >>> print(f"Name: {result.data['name']}")
            >>> print(f"Height: {result.data['height']}m")
        """
        resource_type = "player"
        resource_id = f"{player_code}_{self.config.get_season_code(season)}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        url = self.config.get_player_url(player_code, season)
        xml_data = self._fetch_xml(url, resource_type, resource_id)
        data = self._parse_player(xml_data)

        cache, changed = self._save_cache(
            resource_type, resource_id, data, http_status=200
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_live_boxscore(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch live boxscore from the live API.

        Uses the live.euroleague.net API for boxscore data.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Boxscore dictionary.

        Example:
            >>> result = client.fetch_live_boxscore(2024, 1)
            >>> print(f"Attendance: {result.data['Attendance']}")
        """
        resource_type = "live_boxscore"
        resource_id = f"{self.config.get_season_code(season)}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        url = self.config.get_live_url("Boxscore", gamecode, season)
        data = self._fetch_json(url, resource_type, resource_id)

        cache, changed = self._save_cache(
            resource_type, resource_id, data, http_status=200
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_live_header(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch game header from the live API.

        Uses the live.euroleague.net API for game header data.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Game header dictionary.

        Example:
            >>> result = client.fetch_live_header(2024, 1)
            >>> print(f"Stadium: {result.data['Stadium']}")
        """
        resource_type = "live_header"
        resource_id = f"{self.config.get_season_code(season)}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        url = self.config.get_live_url("Header", gamecode, season)
        data = self._fetch_json(url, resource_type, resource_id)

        cache, changed = self._save_cache(
            resource_type, resource_id, data, http_status=200
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_live_pbp(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch play-by-play from the live API.

        Uses the live.euroleague.net API for play-by-play data.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Play-by-play dictionary with quarters.

        Example:
            >>> result = client.fetch_live_pbp(2024, 1)
            >>> print(f"Q1 events: {len(result.data['FirstQuarter'])}")
        """
        resource_type = "live_pbp"
        resource_id = f"{self.config.get_season_code(season)}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        url = self.config.get_live_url("PlaybyPlay", gamecode, season)
        data = self._fetch_json(url, resource_type, resource_id)

        cache, changed = self._save_cache(
            resource_type, resource_id, data, http_status=200
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_live_points(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch shot data from the live API.

        Uses the live.euroleague.net API for shot location data.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Shot data dictionary with coordinates.

        Example:
            >>> result = client.fetch_live_points(2024, 1)
            >>> print(f"Shots: {len(result.data['Rows'])}")
        """
        resource_type = "live_points"
        resource_id = f"{self.config.get_season_code(season)}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        url = self.config.get_live_url("Points", gamecode, season)
        data = self._fetch_json(url, resource_type, resource_id)

        cache, changed = self._save_cache(
            resource_type, resource_id, data, http_status=200
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_live_comparison(
        self, season: int, gamecode: int, force: bool = False
    ) -> CacheResult:
        """
        Fetch team comparison from the live API.

        Uses the live.euroleague.net API for team comparison stats.

        Args:
            season: The season year.
            gamecode: The game code.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Team comparison dictionary.

        Example:
            >>> result = client.fetch_live_comparison(2024, 1)
            >>> print(f"Max lead A: {result.data['maxLeadA']}")
        """
        resource_type = "live_comparison"
        resource_id = f"{self.config.get_season_code(season)}_{gamecode}"

        if not force:
            cache = self._get_cache(resource_type, resource_id)
            if cache:
                return CacheResult(
                    data=cache.raw_data,
                    changed=False,
                    fetched_at=cache.fetched_at,
                    cache_id=str(cache.id),
                    from_cache=True,
                )

        url = self.config.get_live_url("Comparison", gamecode, season)
        data = self._fetch_json(url, resource_type, resource_id)

        cache, changed = self._save_cache(
            resource_type, resource_id, data, http_status=200
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )
