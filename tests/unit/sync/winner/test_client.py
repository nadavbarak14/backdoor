"""
Winner Client Tests

Tests for src/sync/winner/client.py covering:
- JSON API fetching
- Caching behavior
- Change detection
- Error handling
- Retry logic
"""

import json
from datetime import UTC
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.models.sync_cache import SyncCache
from src.sync.winner.client import CacheResult, WinnerClient
from src.sync.winner.config import WinnerConfig
from src.sync.winner.exceptions import (
    WinnerAPIError,
    WinnerParseError,
    WinnerRateLimitError,
    WinnerTimeoutError,
)

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "winner"


@pytest.fixture
def games_all_fixture():
    """Load games_all.json fixture."""
    with open(FIXTURES_DIR / "games_all.json") as f:
        return json.load(f)


@pytest.fixture
def boxscore_fixture():
    """Load boxscore.json fixture."""
    with open(FIXTURES_DIR / "boxscore.json") as f:
        return json.load(f)


@pytest.fixture
def pbp_fixture():
    """Load pbp_events.json fixture."""
    with open(FIXTURES_DIR / "pbp_events.json") as f:
        return json.load(f)


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""

    def _create(json_data=None, status_code=200, text=""):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.text = text or json.dumps(json_data) if json_data else ""
        response.headers = {}
        response.json.return_value = json_data
        return response

    return _create


class TestCacheResult:
    """Tests for CacheResult dataclass."""

    def test_creation(self):
        """CacheResult should hold fetch result data."""
        from datetime import datetime

        result = CacheResult(
            data={"test": "data"},
            changed=True,
            fetched_at=datetime.now(UTC),
            cache_id="abc-123",
            from_cache=False,
        )

        assert result.data == {"test": "data"}
        assert result.changed is True
        assert result.from_cache is False

    def test_from_cache_default(self):
        """from_cache should default to False."""
        from datetime import datetime

        result = CacheResult(
            data={},
            changed=False,
            fetched_at=datetime.now(UTC),
            cache_id="abc-123",
        )

        assert result.from_cache is False


class TestWinnerClientInit:
    """Tests for WinnerClient initialization."""

    def test_default_config(self, test_db):
        """Client should use default config if not provided."""
        client = WinnerClient(test_db)

        assert client.config is not None
        assert client.config.api_requests_per_second == 2.0

    def test_custom_config(self, test_db):
        """Client should use provided config."""
        config = WinnerConfig(api_requests_per_second=1.0)
        client = WinnerClient(test_db, config=config)

        assert client.config.api_requests_per_second == 1.0

    def test_context_manager(self, test_db):
        """Client should work as context manager."""
        with WinnerClient(test_db) as client:
            assert client._client is not None

        assert client._client is None


class TestWinnerClientFetchGamesAll:
    """Tests for fetch_games_all method."""

    def test_fetch_success(self, test_db, games_all_fixture, mock_response):
        """Should fetch and cache games data."""
        response = mock_response(json_data=games_all_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db) as client:
                result = client.fetch_games_all()

        assert result.data == games_all_fixture
        assert result.changed is True
        assert result.from_cache is False
        assert result.cache_id is not None

    def test_returns_cached_data(self, test_db, games_all_fixture, mock_response):
        """Should return cached data without HTTP request."""
        response = mock_response(json_data=games_all_fixture)

        with patch.object(httpx.Client, "get", return_value=response) as mock_get:
            with WinnerClient(test_db) as client:
                # First fetch
                client.fetch_games_all()

                # Second fetch should use cache
                result = client.fetch_games_all()

        # Should only have made one HTTP request
        assert mock_get.call_count == 1
        assert result.from_cache is True
        assert result.changed is False

    def test_force_refresh(self, test_db, games_all_fixture, mock_response):
        """force=True should bypass cache."""
        response = mock_response(json_data=games_all_fixture)

        with patch.object(httpx.Client, "get", return_value=response) as mock_get:
            with WinnerClient(test_db) as client:
                # First fetch
                client.fetch_games_all()

                # Force refresh
                result = client.fetch_games_all(force=True)

        # Should have made two HTTP requests
        assert mock_get.call_count == 2
        assert result.from_cache is False

    def test_detects_change(self, test_db, games_all_fixture, mock_response):
        """Should detect when data changes."""
        original_data = games_all_fixture.copy()
        modified_data = games_all_fixture.copy()
        modified_data["lastUpdated"] = "2024-01-18T10:30:00Z"

        with patch.object(httpx.Client, "get") as mock_get:
            mock_get.return_value = mock_response(json_data=original_data)

            with WinnerClient(test_db) as client:
                # First fetch
                result1 = client.fetch_games_all()
                assert result1.changed is True

                # Simulate data change
                mock_get.return_value = mock_response(json_data=modified_data)

                # Force refresh to get new data
                result2 = client.fetch_games_all(force=True)
                assert result2.changed is True


class TestWinnerClientFetchBoxscore:
    """Tests for fetch_boxscore method."""

    def test_fetch_success(self, test_db, boxscore_fixture, mock_response):
        """Should fetch boxscore data."""
        response = mock_response(json_data=boxscore_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db) as client:
                result = client.fetch_boxscore("12345")

        assert result.data == boxscore_fixture
        assert result.changed is True

    def test_uses_correct_url(self, test_db, boxscore_fixture, mock_response):
        """Should construct correct boxscore URL."""
        response = mock_response(json_data=boxscore_fixture)

        with patch.object(httpx.Client, "get", return_value=response) as mock_get:
            with WinnerClient(test_db) as client:
                client.fetch_boxscore("12345")

        called_url = mock_get.call_args[0][0]
        assert "game_id=12345" in called_url


class TestWinnerClientFetchPbp:
    """Tests for fetch_pbp method."""

    def test_fetch_success(self, test_db, pbp_fixture, mock_response):
        """Should fetch play-by-play data."""
        response = mock_response(json_data=pbp_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db) as client:
                result = client.fetch_pbp("12345")

        assert result.data == pbp_fixture
        assert "Events" in result.data


class TestWinnerClientErrorHandling:
    """Tests for error handling."""

    def test_http_error(self, test_db, mock_response):
        """Should raise WinnerAPIError on HTTP errors."""
        response = mock_response(status_code=500, text="Internal Server Error")

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db) as client:
                with pytest.raises(WinnerAPIError) as exc_info:
                    client.fetch_games_all()

        assert exc_info.value.status_code == 500

    def test_rate_limit_error(self, test_db, mock_response):
        """Should raise WinnerRateLimitError on 429."""
        response = mock_response(status_code=429)
        response.headers = {"Retry-After": "5"}

        config = WinnerConfig(max_retries=0)  # Disable retries for test

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db, config=config) as client:
                with pytest.raises(WinnerRateLimitError) as exc_info:
                    client.fetch_games_all()

        assert exc_info.value.retry_after == 5.0

    def test_json_parse_error(self, test_db):
        """Should raise WinnerParseError on invalid JSON."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.text = "not valid json"
        response.json.side_effect = json.JSONDecodeError("test", "", 0)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db) as client:
                with pytest.raises(WinnerParseError):
                    client.fetch_games_all()

    def test_timeout_error(self, test_db):
        """Should raise WinnerTimeoutError on timeout."""
        config = WinnerConfig(max_retries=0)

        with (
            patch.object(
                httpx.Client, "get", side_effect=httpx.TimeoutException("timeout")
            ),
            WinnerClient(test_db, config=config) as client,
        ):
            with pytest.raises(WinnerTimeoutError):
                client.fetch_games_all()

    def test_retry_on_error(self, test_db, games_all_fixture, mock_response):
        """Should retry on transient errors."""
        config = WinnerConfig(
            max_retries=2,
            retry_base_delay=0.01,  # Fast retries for test
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Raise a network error that should trigger retry
                raise httpx.RequestError("Connection failed")
            return mock_response(json_data=games_all_fixture)

        with patch.object(httpx.Client, "get", side_effect=side_effect):
            with WinnerClient(test_db, config=config) as client:
                result = client.fetch_games_all()

        assert result.data == games_all_fixture
        assert call_count == 2


class TestWinnerClientCaching:
    """Tests for caching behavior."""

    def test_cache_entry_created(self, test_db, games_all_fixture, mock_response):
        """Should create cache entry in database."""
        response = mock_response(json_data=games_all_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db) as client:
                client.fetch_games_all()

        cache = (
            test_db.query(SyncCache)
            .filter(
                SyncCache.source == "winner",
                SyncCache.resource_type == "games_all",
            )
            .first()
        )

        assert cache is not None
        assert cache.raw_data == games_all_fixture
        assert cache.content_hash is not None
        assert cache.http_status == 200

    def test_hash_computed_correctly(self, test_db, games_all_fixture, mock_response):
        """Should compute consistent hash for same data."""
        response = mock_response(json_data=games_all_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db) as client:
                hash1 = client._compute_hash(games_all_fixture)
                hash2 = client._compute_hash(games_all_fixture)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length


class TestWinnerClientMultipleFetch:
    """Tests for fetch_multiple_boxscores."""

    def test_fetch_multiple(self, test_db, boxscore_fixture, mock_response):
        """Should fetch multiple boxscores."""
        response = mock_response(json_data=boxscore_fixture)

        with patch.object(httpx.Client, "get", return_value=response):
            with WinnerClient(test_db) as client:
                results = client.fetch_multiple_boxscores(["123", "456", "789"])

        assert len(results) == 3
        assert "123" in results
        assert "456" in results
        assert "789" in results
