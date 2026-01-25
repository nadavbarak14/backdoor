"""
Unit tests for IBasketballApiClient.

Tests REST API client with mocked HTTP responses.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.sync.ibasketball.api_client import CacheResult, IBasketballApiClient
from src.sync.ibasketball.config import IBasketballConfig
from src.sync.ibasketball.exceptions import (
    IBasketballAPIError,
    IBasketballParseError,
    IBasketballRateLimitError,
    IBasketballTimeoutError,
)


class TestCacheResult:
    """Tests for CacheResult dataclass."""

    def test_cache_result_creation(self):
        """Test creating a CacheResult."""
        result = CacheResult(
            data={"key": "value"},
            changed=True,
            fetched_at=datetime.now(UTC),
            cache_id="test-id",
            from_cache=False,
        )

        assert result.data == {"key": "value"}
        assert result.changed is True
        assert result.from_cache is False

    def test_cache_result_defaults(self):
        """Test CacheResult default values."""
        result = CacheResult(
            data=[],
            changed=False,
            fetched_at=datetime.now(UTC),
            cache_id="test-id",
        )

        assert result.from_cache is False


class TestIBasketballApiClient:
    """Tests for IBasketballApiClient class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return IBasketballConfig(
            api_requests_per_second=100.0,  # Fast for tests
            max_retries=1,
        )

    @pytest.fixture
    def client(self, mock_db, config):
        """Create client instance."""
        client = IBasketballApiClient(mock_db, config=config)
        return client

    class TestContextManager:
        """Tests for context manager functionality."""

        def test_context_manager_creates_client(self, mock_db, config):
            """Test context manager creates HTTP client."""
            with IBasketballApiClient(mock_db, config=config) as client:
                assert client._client is not None

        def test_context_manager_closes_client(self, mock_db, config):
            """Test context manager closes HTTP client."""
            api_client = IBasketballApiClient(mock_db, config=config)
            with api_client:
                pass
            assert api_client._client is None

    class TestComputeHash:
        """Tests for hash computation."""

        def test_compute_hash_dict(self, client):
            """Test computing hash of dictionary."""
            data = {"key": "value"}
            hash1 = client._compute_hash(data)
            hash2 = client._compute_hash(data)

            assert hash1 == hash2
            assert len(hash1) == 64  # SHA-256 hex

        def test_compute_hash_different_data(self, client):
            """Test different data produces different hash."""
            hash1 = client._compute_hash({"key": "value1"})
            hash2 = client._compute_hash({"key": "value2"})

            assert hash1 != hash2

    class TestFetchJson:
        """Tests for JSON fetching."""

        @patch("src.sync.ibasketball.api_client.httpx.Client")
        def test_fetch_json_success(self, mock_client_class, client):
            """Test successful JSON fetch."""
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "test"}

            mock_http_client = MagicMock()
            mock_http_client.get.return_value = mock_response
            client._client = mock_http_client

            data = client._fetch_json(
                "https://test.com/api",
                "test_resource",
                "123",
            )

            assert data == {"data": "test"}

        @patch("src.sync.ibasketball.api_client.httpx.Client")
        def test_fetch_json_rate_limit(self, mock_client_class, client):
            """Test handling rate limit response."""
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "5"}

            mock_http_client = MagicMock()
            mock_http_client.get.return_value = mock_response
            client._client = mock_http_client

            with pytest.raises(IBasketballRateLimitError) as exc_info:
                client._fetch_json("https://test.com/api", "test", "123")

            assert exc_info.value.retry_after == 5.0

        @patch("src.sync.ibasketball.api_client.httpx.Client")
        def test_fetch_json_http_error(self, mock_client_class, client):
            """Test handling HTTP error response."""
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_http_client = MagicMock()
            mock_http_client.get.return_value = mock_response
            client._client = mock_http_client

            with pytest.raises(IBasketballAPIError) as exc_info:
                client._fetch_json("https://test.com/api", "test", "123")

            assert exc_info.value.status_code == 500

        @patch("src.sync.ibasketball.api_client.httpx.Client")
        def test_fetch_json_parse_error(self, mock_client_class, client):
            """Test handling JSON parse error."""
            import json

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError(
                "Invalid JSON", "doc", 0
            )
            mock_response.text = "not json"

            mock_http_client = MagicMock()
            mock_http_client.get.return_value = mock_response
            client._client = mock_http_client

            with pytest.raises(IBasketballParseError):
                client._fetch_json("https://test.com/api", "test", "123")

        @patch("src.sync.ibasketball.api_client.httpx.Client")
        def test_fetch_json_timeout(self, mock_client_class, client):
            """Test handling request timeout."""
            mock_http_client = MagicMock()
            mock_http_client.get.side_effect = httpx.TimeoutException("Timeout")
            client._client = mock_http_client

            with pytest.raises(IBasketballTimeoutError):
                client._fetch_json("https://test.com/api", "test", "123")

    class TestFetchEvents:
        """Tests for fetching events."""

        def test_fetch_events_from_cache(self, client, mock_db):
            """Test fetching events from cache."""
            mock_cache = MagicMock()
            mock_cache.raw_data = [{"id": 1}, {"id": 2}]
            mock_cache.fetched_at = datetime.now(UTC)
            mock_cache.id = "cache-123"

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_cache
            )

            result = client.fetch_events("119474", page=1)

            assert result.from_cache is True
            assert result.data == [{"id": 1}, {"id": 2}]
            assert result.changed is False

        @patch.object(IBasketballApiClient, "_fetch_json")
        def test_fetch_events_force_refresh(self, mock_fetch, client, mock_db):
            """Test force refresh bypasses cache."""
            mock_fetch.return_value = [{"id": 3}]
            mock_db.query.return_value.filter.return_value.first.return_value = None

            # Mock cache save
            mock_cache = MagicMock()
            mock_cache.fetched_at = datetime.now(UTC)
            mock_cache.id = "cache-456"

            with patch.object(client, "_save_cache", return_value=(mock_cache, True)):
                result = client.fetch_events("119474", force=True)

            assert result.from_cache is False
            mock_fetch.assert_called_once()

    class TestFetchAllEvents:
        """Tests for fetching all events with pagination."""

        @patch.object(IBasketballApiClient, "fetch_events")
        def test_fetch_all_events_single_page(self, mock_fetch, client, mock_db):
            """Test fetching single page of events."""
            # Return less than per_page to indicate last page
            mock_result = CacheResult(
                data=[{"id": i} for i in range(50)],
                changed=True,
                fetched_at=datetime.now(UTC),
                cache_id="cache-1",
                from_cache=False,
            )
            mock_fetch.return_value = mock_result

            # Mock cache for fetch_all_events
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_cache = MagicMock()
            mock_cache.fetched_at = datetime.now(UTC)
            mock_cache.id = "cache-all"

            with patch.object(client, "_save_cache", return_value=(mock_cache, True)):
                result = client.fetch_all_events("119474")

            assert len(result.data) == 50

        @patch.object(IBasketballApiClient, "fetch_events")
        def test_fetch_all_events_multiple_pages(self, mock_fetch, client, mock_db):
            """Test fetching multiple pages of events."""
            # First page returns full per_page, second returns less
            page1_result = CacheResult(
                data=[{"id": i} for i in range(100)],
                changed=True,
                fetched_at=datetime.now(UTC),
                cache_id="cache-1",
                from_cache=False,
            )
            page2_result = CacheResult(
                data=[{"id": i} for i in range(100, 150)],
                changed=True,
                fetched_at=datetime.now(UTC),
                cache_id="cache-2",
                from_cache=False,
            )

            mock_fetch.side_effect = [page1_result, page2_result]

            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_cache = MagicMock()
            mock_cache.fetched_at = datetime.now(UTC)
            mock_cache.id = "cache-all"

            with patch.object(client, "_save_cache", return_value=(mock_cache, True)):
                result = client.fetch_all_events("119474")

            assert len(result.data) == 150
            assert mock_fetch.call_count == 2

    class TestFetchEvent:
        """Tests for fetching single event."""

        def test_fetch_event_from_cache(self, client, mock_db):
            """Test fetching event from cache."""
            mock_cache = MagicMock()
            mock_cache.raw_data = {"id": 123, "teams": [100, 101]}
            mock_cache.fetched_at = datetime.now(UTC)
            mock_cache.id = "cache-event"

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_cache
            )

            result = client.fetch_event("123")

            assert result.from_cache is True
            assert result.data["id"] == 123

    class TestFetchStandings:
        """Tests for fetching standings."""

        def test_fetch_standings_from_cache(self, client, mock_db):
            """Test fetching standings from cache."""
            mock_cache = MagicMock()
            mock_cache.raw_data = [{"team_id": 100, "points": 20}]
            mock_cache.fetched_at = datetime.now(UTC)
            mock_cache.id = "cache-standings"

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_cache
            )

            result = client.fetch_standings("119474")

            assert result.from_cache is True

    class TestFetchTeams:
        """Tests for fetching teams."""

        def test_fetch_teams_from_cache(self, client, mock_db):
            """Test fetching teams from cache."""
            mock_cache = MagicMock()
            mock_cache.raw_data = [{"id": 100, "title": {"rendered": "Team A"}}]
            mock_cache.fetched_at = datetime.now(UTC)
            mock_cache.id = "cache-teams"

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_cache
            )

            result = client.fetch_teams()

            assert result.from_cache is True

    class TestFetchMultipleEvents:
        """Tests for fetching multiple events."""

        @patch.object(IBasketballApiClient, "fetch_event")
        def test_fetch_multiple_events(self, mock_fetch, client):
            """Test fetching multiple events."""
            mock_fetch.return_value = CacheResult(
                data={"id": 1},
                changed=True,
                fetched_at=datetime.now(UTC),
                cache_id="cache-1",
            )

            results = client.fetch_multiple_events(["1", "2", "3"])

            assert len(results) == 3
            assert mock_fetch.call_count == 3
