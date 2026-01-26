"""
Unit tests for NBA Configuration.

Tests the NBAConfig class for configuration settings.
"""


from src.sync.nba.config import NBAConfig


class TestNBAConfigDefaults:
    """Tests for default configuration values."""

    def test_default_requests_per_minute(self):
        """Test default rate limit."""
        config = NBAConfig()
        assert config.requests_per_minute == 20

    def test_default_request_timeout(self):
        """Test default timeout."""
        config = NBAConfig()
        assert config.request_timeout == 30.0

    def test_default_max_retries(self):
        """Test default max retries."""
        config = NBAConfig()
        assert config.max_retries == 3

    def test_default_retry_base_delay(self):
        """Test default retry base delay."""
        config = NBAConfig()
        assert config.retry_base_delay == 2.0

    def test_default_retry_max_delay(self):
        """Test default retry max delay."""
        config = NBAConfig()
        assert config.retry_max_delay == 60.0

    def test_default_proxy_is_none(self):
        """Test default proxy is None."""
        config = NBAConfig()
        assert config.proxy is None

    def test_default_headers_empty(self):
        """Test default headers is empty dict."""
        config = NBAConfig()
        assert config.headers == {}

    def test_default_configured_seasons(self):
        """Test default configured seasons are auto-generated."""
        config = NBAConfig()
        assert config.configured_seasons is not None
        assert len(config.configured_seasons) == 2
        # Should be in YYYY-YY format
        assert "-" in config.configured_seasons[0]


class TestNBAConfigCustomValues:
    """Tests for custom configuration values."""

    def test_custom_requests_per_minute(self):
        """Test custom rate limit."""
        config = NBAConfig(requests_per_minute=10)
        assert config.requests_per_minute == 10

    def test_custom_timeout(self):
        """Test custom timeout."""
        config = NBAConfig(request_timeout=60.0)
        assert config.request_timeout == 60.0

    def test_custom_proxy(self):
        """Test custom proxy."""
        config = NBAConfig(proxy="http://proxy.example.com:8080")
        assert config.proxy == "http://proxy.example.com:8080"

    def test_custom_headers(self):
        """Test custom headers."""
        headers = {"X-Custom-Header": "value"}
        config = NBAConfig(headers=headers)
        assert config.headers == headers

    def test_custom_configured_seasons(self):
        """Test custom configured seasons."""
        seasons = ["2023-24", "2022-23", "2021-22"]
        config = NBAConfig(configured_seasons=seasons)
        assert config.configured_seasons == seasons


class TestNBAConfigMethods:
    """Tests for configuration helper methods."""

    def test_get_season_id(self):
        """Test get_season_id method."""
        config = NBAConfig()
        assert config.get_season_id("2023-24") == "2023-24"

    def test_get_season_year(self):
        """Test get_season_year method."""
        config = NBAConfig()
        assert config.get_season_year("2023-24") == 2023

    def test_delay_between_requests_default(self):
        """Test delay calculation with default rate."""
        config = NBAConfig()  # 20 requests/minute
        assert config.delay_between_requests == 3.0

    def test_delay_between_requests_custom(self):
        """Test delay calculation with custom rate."""
        config = NBAConfig(requests_per_minute=30)
        assert config.delay_between_requests == 2.0

    def test_delay_between_requests_low_rate(self):
        """Test delay calculation with low rate."""
        config = NBAConfig(requests_per_minute=10)
        assert config.delay_between_requests == 6.0


class TestNBAConfigSeasonFormat:
    """Tests for season format validation."""

    def test_season_format_current(self):
        """Test current season format."""
        config = NBAConfig(configured_seasons=["2023-24"])
        assert config.get_season_year("2023-24") == 2023

    def test_season_format_past(self):
        """Test past season format."""
        config = NBAConfig(configured_seasons=["2019-20"])
        assert config.get_season_year("2019-20") == 2019
