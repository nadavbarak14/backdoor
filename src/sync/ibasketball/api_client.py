"""
iBasketball API Client Module

Provides the IBasketballApiClient class for fetching data from iBasketball
SportsPress REST API. Handles events, boxscores, teams, and standings with
automatic caching and rate limiting.

This module exports:
    - IBasketballApiClient: REST API client for iBasketball data
    - CacheResult: Dataclass for fetch results with caching metadata

Usage:
    from sqlalchemy.orm import Session
    from src.sync.ibasketball.api_client import IBasketballApiClient

    db = SessionLocal()
    with IBasketballApiClient(db) as client:
        result = client.fetch_events("119474")
        print(f"Fetched {len(result.data)} events")
"""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from src.models.sync_cache import SyncCache
from src.sync.ibasketball.config import IBasketballConfig
from src.sync.ibasketball.exceptions import (
    IBasketballAPIError,
    IBasketballParseError,
    IBasketballRateLimitError,
    IBasketballTimeoutError,
)
from src.sync.winner.rate_limiter import RateLimiter, calculate_backoff


@dataclass
class CacheResult:
    """
    Result from a cached fetch operation.

    Contains the fetched data along with caching metadata to indicate
    whether the data is new or unchanged from the previous fetch.

    Attributes:
        data: The fetched JSON data (list or dictionary).
        changed: True if data differs from cached version.
        fetched_at: Timestamp when data was fetched.
        cache_id: UUID of the cache entry.
        from_cache: True if data was served from cache without HTTP request.

    Example:
        >>> result = client.fetch_event("12345")
        >>> if result.changed:
        ...     print("New data available!")
        ...     process_event(result.data)
    """

    data: dict | list
    changed: bool
    fetched_at: datetime
    cache_id: str
    from_cache: bool = False


class IBasketballApiClient:
    """
    Client for fetching data from iBasketball SportsPress REST API.

    Provides methods for fetching events, boxscores, teams, and standings.
    All responses are cached in the database with checksum-based change
    detection. Rate limiting prevents overloading the remote servers.

    Attributes:
        db: SQLAlchemy database session.
        config: Configuration settings.
        rate_limiter: Token bucket rate limiter.
        _client: httpx HTTP client instance.

    Example:
        >>> db = SessionLocal()
        >>> with IBasketballApiClient(db) as client:
        ...     # Fetch all events for Liga Leumit
        ...     events = client.fetch_all_events("119474")
        ...     print(f"Events: {len(events.data)}")
        ...
        ...     # Fetch specific event with boxscore
        ...     event = client.fetch_event("123456")
        ...     print(f"Home score: {event.data.get('results', {})}")
    """

    SOURCE = "ibasketball"

    def __init__(
        self,
        db: Session,
        config: IBasketballConfig | None = None,
    ) -> None:
        """
        Initialize IBasketballApiClient.

        Args:
            db: SQLAlchemy database session for caching.
            config: Optional configuration. Uses defaults if not provided.

        Example:
            >>> db = SessionLocal()
            >>> client = IBasketballApiClient(db)
            >>> # Or with custom config
            >>> config = IBasketballConfig(api_requests_per_second=1.0)
            >>> client = IBasketballApiClient(db, config=config)
        """
        self.db = db
        self.config = config or IBasketballConfig()
        self.rate_limiter = RateLimiter(
            requests_per_second=self.config.api_requests_per_second,
            burst_size=self.config.api_burst_size,
        )
        self._client: httpx.Client | None = None

    def __enter__(self) -> "IBasketballApiClient":
        """
        Context manager entry - create HTTP client.

        Returns:
            IBasketballApiClient: Self for method chaining.
        """
        self._client = httpx.Client(
            timeout=self.config.request_timeout,
            headers={
                "User-Agent": self.config.user_agent,
                "Accept": "application/json",
            },
            follow_redirects=True,
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
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self._client

    def close(self) -> None:
        """
        Close the HTTP client.

        Call this when not using the context manager to clean up resources.

        Example:
            >>> client = IBasketballApiClient(db)
            >>> try:
            ...     result = client.fetch_events("119474")
            ... finally:
            ...     client.close()
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
            resource_type: Type of resource (e.g., "events", "event").
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
    ) -> dict | list:
        """
        Fetch JSON from URL with rate limiting and retries.

        Args:
            url: URL to fetch.
            resource_type: Type of resource (for error messages).
            resource_id: Resource identifier (for error messages).

        Returns:
            Parsed JSON response (dict or list).

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballParseError: On JSON parse errors.
            IBasketballTimeoutError: On request timeout.
            IBasketballRateLimitError: On rate limit (HTTP 429).
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
                    raise IBasketballRateLimitError(
                        f"Rate limited by server for {resource_type}",
                        retry_after=retry_after,
                    )

                # Handle errors
                if response.status_code >= 400:
                    raise IBasketballAPIError(
                        f"HTTP {response.status_code} fetching {resource_type}",
                        status_code=response.status_code,
                        url=url,
                        response_body=response.text[:500] if response.text else None,
                    )

                # Parse JSON
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    raise IBasketballParseError(
                        f"Invalid JSON response: {e}",
                        resource_type=resource_type,
                        resource_id=resource_id,
                        raw_data=response.text[:500] if response.text else None,
                    ) from e

            except httpx.TimeoutException as e:
                last_error = IBasketballTimeoutError(
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

            except IBasketballRateLimitError as e:
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
                last_error = IBasketballAPIError(
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
        raise IBasketballAPIError(
            f"Failed to fetch {resource_type} after retries", url=url
        )

    def fetch_events(
        self,
        league_id: str,
        page: int = 1,
        force: bool = False,
    ) -> CacheResult:
        """
        Fetch events (games) for a specific league and page.

        Args:
            league_id: SportsPress league ID.
            page: Page number for pagination.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Fetched data with caching metadata.

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballParseError: On JSON parse errors.
            IBasketballTimeoutError: On request timeout.

        Example:
            >>> result = client.fetch_events("119474", page=1)
            >>> events = result.data
            >>> print(f"Found {len(events)} events")
        """
        resource_type = "events"
        resource_id = f"{league_id}_page_{page}"

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
        url = self.config.get_events_url(league_id, page)
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

    def fetch_all_events(
        self,
        league_id: str,
        force: bool = False,
    ) -> CacheResult:
        """
        Fetch all events for a league, handling pagination.

        Args:
            league_id: SportsPress league ID.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Combined data from all pages.

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballParseError: On JSON parse errors.
            IBasketballTimeoutError: On request timeout.

        Example:
            >>> result = client.fetch_all_events("119474")
            >>> all_events = result.data
            >>> print(f"Found {len(all_events)} total events")
        """
        resource_type = "events_all"
        resource_id = league_id

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

        # Fetch all pages
        all_events: list[dict] = []
        page = 1
        max_pages = 50  # Safety limit

        while page <= max_pages:
            result = self.fetch_events(league_id, page=page, force=True)

            if not isinstance(result.data, list):
                break

            if not result.data:
                break

            all_events.extend(result.data)

            # Check if more pages exist (less than per_page means last page)
            if len(result.data) < self.config.per_page:
                break

            page += 1

        # Save combined result to cache
        cache, changed = self._save_cache(
            resource_type,
            resource_id,
            all_events,
            http_status=200,
        )

        return CacheResult(
            data=all_events,
            changed=changed,
            fetched_at=cache.fetched_at,
            cache_id=str(cache.id),
            from_cache=False,
        )

    def fetch_event(
        self,
        event_id: str,
        force: bool = False,
    ) -> CacheResult:
        """
        Fetch a single event with full details including boxscore data.

        Args:
            event_id: SportsPress event ID.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Event data with performance/boxscore.

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballParseError: On JSON parse errors.
            IBasketballTimeoutError: On request timeout.

        Example:
            >>> result = client.fetch_event("123456")
            >>> event = result.data
            >>> print(f"Teams: {event.get('teams')}")
        """
        resource_type = "event"
        resource_id = event_id

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
        url = self.config.get_event_url(event_id)
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

    def fetch_standings(
        self,
        league_id: str,
        force: bool = False,
    ) -> CacheResult:
        """
        Fetch standings/tables for a specific league.

        Args:
            league_id: SportsPress league ID.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Standings data.

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballParseError: On JSON parse errors.
            IBasketballTimeoutError: On request timeout.

        Example:
            >>> result = client.fetch_standings("119474")
            >>> standings = result.data
            >>> print(f"Found {len(standings)} tables")
        """
        resource_type = "standings"
        resource_id = league_id

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

        url = self.config.get_standings_url(league_id)
        data = self._fetch_json(url, resource_type, resource_id)

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

    def fetch_teams(
        self,
        league_id: str | None = None,
        force: bool = False,
    ) -> CacheResult:
        """
        Fetch teams, optionally filtered by league.

        Args:
            league_id: Optional SportsPress league ID to filter by.
            force: If True, bypass cache and fetch from API.

        Returns:
            CacheResult: Teams data.

        Raises:
            IBasketballAPIError: On HTTP errors.
            IBasketballParseError: On JSON parse errors.
            IBasketballTimeoutError: On request timeout.

        Example:
            >>> result = client.fetch_teams("119474")
            >>> teams = result.data
            >>> print(f"Found {len(teams)} teams")
        """
        resource_type = "teams"
        resource_id = league_id or "all"

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

        url = self.config.get_teams_url(league_id)
        data = self._fetch_json(url, resource_type, resource_id)

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

    def fetch_multiple_events(
        self,
        event_ids: list[str],
        force: bool = False,
    ) -> dict[str, CacheResult]:
        """
        Fetch multiple events with boxscore data.

        Convenience method for fetching multiple events sequentially
        with proper rate limiting.

        Args:
            event_ids: List of event identifiers.
            force: If True, bypass cache and fetch from API.

        Returns:
            Dict mapping event_id to CacheResult.

        Example:
            >>> results = client.fetch_multiple_events(["123", "456", "789"])
            >>> for event_id, result in results.items():
            ...     print(f"Event {event_id}: changed={result.changed}")
        """
        results = {}
        for event_id in event_ids:
            results[event_id] = self.fetch_event(event_id, force=force)
        return results
