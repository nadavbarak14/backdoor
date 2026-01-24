"""
Winner League Client Module

Provides the WinnerClient class for fetching data from Winner League JSON APIs.
Handles game schedules, boxscores, and play-by-play data with automatic caching
and rate limiting.

This module exports:
    - WinnerClient: JSON API client for Winner League data
    - CacheResult: Dataclass for fetch results with caching metadata

Usage:
    from sqlalchemy.orm import Session
    from src.sync.winner.client import WinnerClient

    db = SessionLocal()
    with WinnerClient(db) as client:
        result = client.fetch_games_all()
        print(f"Fetched {len(result.data.get('games', []))} games")
        print(f"Changed: {result.changed}")
"""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from src.models.sync_cache import SyncCache
from src.sync.winner.config import WinnerConfig
from src.sync.winner.exceptions import (
    WinnerAPIError,
    WinnerParseError,
    WinnerRateLimitError,
    WinnerTimeoutError,
)
from src.sync.winner.rate_limiter import RateLimiter, calculate_backoff


@dataclass
class CacheResult:
    """
    Result from a cached fetch operation.

    Contains the fetched data along with caching metadata to indicate
    whether the data is new or unchanged from the previous fetch.

    Attributes:
        data: The fetched JSON data as a dictionary.
        changed: True if data differs from cached version.
        fetched_at: Timestamp when data was fetched.
        cache_id: UUID of the cache entry.
        from_cache: True if data was served from cache without HTTP request.

    Example:
        >>> result = client.fetch_boxscore("12345")
        >>> if result.changed:
        ...     print("New data available!")
        ...     process_boxscore(result.data)
    """

    data: dict
    changed: bool
    fetched_at: datetime
    cache_id: str
    from_cache: bool = False


class WinnerClient:
    """
    Client for fetching data from Winner League JSON APIs.

    Provides methods for fetching game schedules, boxscores, and play-by-play
    data. All responses are cached in the database with checksum-based change
    detection. Rate limiting prevents overloading the remote servers.

    Attributes:
        db: SQLAlchemy database session.
        config: Configuration settings.
        rate_limiter: Token bucket rate limiter.
        _client: httpx HTTP client instance.

    Example:
        >>> db = SessionLocal()
        >>> with WinnerClient(db) as client:
        ...     # Fetch all games
        ...     games = client.fetch_games_all()
        ...     print(f"Games: {len(games.data.get('games', []))}")
        ...
        ...     # Fetch specific game boxscore
        ...     boxscore = client.fetch_boxscore("12345")
        ...     print(f"Home: {boxscore.data.get('home_score')}")
    """

    SOURCE = "winner"

    def __init__(
        self,
        db: Session,
        config: WinnerConfig | None = None,
    ) -> None:
        """
        Initialize WinnerClient.

        Args:
            db: SQLAlchemy database session for caching.
            config: Optional configuration. Uses defaults if not provided.

        Example:
            >>> db = SessionLocal()
            >>> client = WinnerClient(db)
            >>> # Or with custom config
            >>> config = WinnerConfig(api_requests_per_second=1.0)
            >>> client = WinnerClient(db, config=config)
        """
        self.db = db
        self.config = config or WinnerConfig()
        self.rate_limiter = RateLimiter(
            requests_per_second=self.config.api_requests_per_second,
            burst_size=self.config.api_burst_size,
        )
        self._client: httpx.Client | None = None

    def __enter__(self) -> "WinnerClient":
        """
        Context manager entry - create HTTP client.

        Returns:
            WinnerClient: Self for method chaining.
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

        Raises:
            RuntimeError: If client not initialized (use context manager).
        """
        if self._client is None:
            # Create client for non-context-manager usage
            self._client = httpx.Client(
                timeout=self.config.request_timeout,
                headers={"User-Agent": self.config.user_agent},
            )
        return self._client

    def close(self) -> None:
        """
        Close the HTTP client.

        Call this when not using the context manager to clean up resources.

        Example:
            >>> client = WinnerClient(db)
            >>> try:
            ...     result = client.fetch_games_all()
            ... finally:
            ...     client.close()
        """
        if self._client:
            self._client.close()
            self._client = None

    def _compute_hash(self, data: dict) -> str:
        """
        Compute SHA-256 hash of data for change detection.

        Args:
            data: Dictionary to hash.

        Returns:
            str: Hex-encoded SHA-256 hash.
        """
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _get_cache(
        self,
        resource_type: str,
        resource_id: str,
    ) -> SyncCache | None:
        """
        Get cached entry from database.

        Args:
            resource_type: Type of resource (e.g., "games_all", "boxscore").
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
        data: dict,
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
            # Check if data changed
            changed = cache.content_hash != content_hash

            if changed:
                cache.raw_data = data
                cache.content_hash = content_hash
                cache.fetched_at = now
                cache.http_status = http_status
                self.db.commit()
            else:
                # Update fetched_at even if data unchanged
                cache.fetched_at = now
                self.db.commit()

            return cache, changed
        else:
            # Create new cache entry
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
            WinnerAPIError: On HTTP errors.
            WinnerParseError: On JSON parse errors.
            WinnerTimeoutError: On request timeout.
            WinnerRateLimitError: On rate limit (HTTP 429).
        """
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Wait for rate limiter
                self.rate_limiter.acquire()

                # Make request
                response = self.client.get(url)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get(
                            "Retry-After", self.config.retry_base_delay
                        )
                    )
                    raise WinnerRateLimitError(
                        f"Rate limited by server for {resource_type}",
                        retry_after=retry_after,
                    )

                # Handle errors
                if response.status_code >= 400:
                    raise WinnerAPIError(
                        f"HTTP {response.status_code} fetching {resource_type}",
                        status_code=response.status_code,
                        url=url,
                        response_body=response.text[:500] if response.text else None,
                    )

                # Parse JSON
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    raise WinnerParseError(
                        f"Invalid JSON response: {e}",
                        resource_type=resource_type,
                        resource_id=resource_id,
                        raw_data=response.text[:500] if response.text else None,
                    ) from e

            except httpx.TimeoutException as e:
                last_error = WinnerTimeoutError(
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

            except WinnerRateLimitError as e:
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
                last_error = WinnerAPIError(
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

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise WinnerAPIError(f"Failed to fetch {resource_type} after retries", url=url)

    def fetch_games_all(self, force: bool = False) -> CacheResult:
        """
        Fetch all current season games.

        Retrieves the complete list of games for the current season
        from basket.co.il.

        Args:
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Fetched data with caching metadata.

        Raises:
            WinnerAPIError: On HTTP errors.
            WinnerParseError: On JSON parse errors.
            WinnerTimeoutError: On request timeout.

        Example:
            >>> result = client.fetch_games_all()
            >>> games = result.data.get("games", [])
            >>> print(f"Found {len(games)} games")
            >>> if result.changed:
            ...     print("New games data!")
        """
        resource_type = "games_all"
        resource_id = "current"  # Single resource for current season

        # Check cache unless force refresh
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

        # Fetch from API
        data = self._fetch_json(
            self.config.games_all_url,
            resource_type,
            resource_id,
        )

        # Save to cache
        cache, changed = self._save_cache(
            resource_type,
            resource_id,
            data,
            http_status=200,
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_boxscore(self, game_id: str, force: bool = False) -> CacheResult:
        """
        Fetch boxscore for a specific game.

        Retrieves detailed box score data including team and player
        statistics for a single game.

        Args:
            game_id: The game identifier.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Fetched data with caching metadata.

        Raises:
            WinnerAPIError: On HTTP errors.
            WinnerParseError: On JSON parse errors.
            WinnerTimeoutError: On request timeout.

        Example:
            >>> result = client.fetch_boxscore("12345")
            >>> home = result.data.get("home_team", {})
            >>> print(f"Home score: {home.get('score')}")
        """
        resource_type = "boxscore"
        resource_id = game_id

        # Check cache unless force refresh
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

        # Fetch from API
        url = self.config.get_boxscore_url(game_id)
        data = self._fetch_json(url, resource_type, resource_id)

        # Save to cache
        cache, changed = self._save_cache(
            resource_type,
            resource_id,
            data,
            http_status=200,
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_pbp(self, game_id: str, force: bool = False) -> CacheResult:
        """
        Fetch play-by-play events for a specific game.

        Retrieves detailed play-by-play data including all game events
        and actions.

        Args:
            game_id: The game identifier.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Fetched data with caching metadata.

        Raises:
            WinnerAPIError: On HTTP errors.
            WinnerParseError: On JSON parse errors.
            WinnerTimeoutError: On request timeout.

        Example:
            >>> result = client.fetch_pbp("12345")
            >>> events = result.data.get("events", [])
            >>> print(f"Found {len(events)} play-by-play events")
        """
        resource_type = "pbp"
        resource_id = game_id

        # Check cache unless force refresh
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

        # Fetch from API
        url = self.config.get_pbp_url(game_id)
        data = self._fetch_json(url, resource_type, resource_id)

        # Save to cache
        cache, changed = self._save_cache(
            resource_type,
            resource_id,
            data,
            http_status=200,
        )

        return CacheResult(
            data=data,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_multiple_boxscores(
        self,
        game_ids: list[str],
        force: bool = False,
    ) -> dict[str, CacheResult]:
        """
        Fetch boxscores for multiple games.

        Convenience method for fetching multiple boxscores sequentially
        with proper rate limiting.

        Args:
            game_ids: List of game identifiers.
            force: If True, bypass cache and fetch from API.

        Returns:
            Dict mapping game_id to CacheResult.

        Example:
            >>> results = client.fetch_multiple_boxscores(["123", "456", "789"])
            >>> for game_id, result in results.items():
            ...     print(f"Game {game_id}: changed={result.changed}")
        """
        results = {}
        for game_id in game_ids:
            results[game_id] = self.fetch_boxscore(game_id, force=force)
        return results
