"""Unit tests for Euroleague exceptions."""


from src.sync.euroleague.exceptions import (
    EuroleagueAPIError,
    EuroleagueError,
    EuroleagueParseError,
    EuroleagueRateLimitError,
    EuroleagueTimeoutError,
)


class TestEuroleagueError:
    """Tests for base EuroleagueError exception."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = EuroleagueError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"

    def test_error_inheritance(self):
        """Test that EuroleagueError inherits from Exception."""
        error = EuroleagueError("Test")

        assert isinstance(error, Exception)


class TestEuroleagueAPIError:
    """Tests for EuroleagueAPIError exception."""

    def test_basic_api_error(self):
        """Test basic API error creation."""
        error = EuroleagueAPIError("HTTP 500 error")

        assert error.message == "HTTP 500 error"
        assert error.status_code is None
        assert error.url is None

    def test_api_error_with_details(self):
        """Test API error with all details."""
        error = EuroleagueAPIError(
            "Server error",
            status_code=500,
            url="https://api.example.com",
            response_body="Internal Server Error",
        )

        assert error.status_code == 500
        assert error.url == "https://api.example.com"
        assert error.response_body == "Internal Server Error"

    def test_api_error_str_format(self):
        """Test API error string formatting."""
        error = EuroleagueAPIError(
            "Failed",
            status_code=404,
            url="https://api.example.com/teams",
        )

        error_str = str(error)
        assert "Failed" in error_str
        assert "status=404" in error_str
        assert "url=https://api.example.com/teams" in error_str

    def test_api_error_inherits_from_base(self):
        """Test that EuroleagueAPIError inherits from EuroleagueError."""
        error = EuroleagueAPIError("Test")

        assert isinstance(error, EuroleagueError)


class TestEuroleagueParseError:
    """Tests for EuroleagueParseError exception."""

    def test_basic_parse_error(self):
        """Test basic parse error creation."""
        error = EuroleagueParseError("Invalid XML")

        assert error.message == "Invalid XML"
        assert error.resource_type is None
        assert error.resource_id is None

    def test_parse_error_with_context(self):
        """Test parse error with resource context."""
        error = EuroleagueParseError(
            "Missing 'Stats' field",
            resource_type="boxscore",
            resource_id="E2024_1",
            raw_data="<invalid>...",
        )

        assert error.resource_type == "boxscore"
        assert error.resource_id == "E2024_1"
        assert error.raw_data == "<invalid>..."

    def test_parse_error_str_format(self):
        """Test parse error string formatting."""
        error = EuroleagueParseError(
            "Parse failed",
            resource_type="teams",
            resource_id="E2024",
        )

        error_str = str(error)
        assert "Parse failed" in error_str
        assert "type=teams" in error_str
        assert "id=E2024" in error_str


class TestEuroleagueRateLimitError:
    """Tests for EuroleagueRateLimitError exception."""

    def test_basic_rate_limit_error(self):
        """Test basic rate limit error creation."""
        error = EuroleagueRateLimitError("Rate limit exceeded")

        assert error.message == "Rate limit exceeded"
        assert error.retry_after is None

    def test_rate_limit_with_retry_after(self):
        """Test rate limit error with retry time."""
        error = EuroleagueRateLimitError(
            "Too many requests",
            retry_after=5.0,
        )

        assert error.retry_after == 5.0

    def test_rate_limit_str_format(self):
        """Test rate limit error string formatting."""
        error = EuroleagueRateLimitError(
            "Rate limited",
            retry_after=10.0,
        )

        assert "retry after 10.0s" in str(error)


class TestEuroleagueTimeoutError:
    """Tests for EuroleagueTimeoutError exception."""

    def test_basic_timeout_error(self):
        """Test basic timeout error creation."""
        error = EuroleagueTimeoutError("Request timed out")

        assert error.message == "Request timed out"
        assert error.timeout is None
        assert error.url is None

    def test_timeout_with_details(self):
        """Test timeout error with all details."""
        error = EuroleagueTimeoutError(
            "Timeout",
            timeout=30.0,
            url="https://api.example.com",
        )

        assert error.timeout == 30.0
        assert error.url == "https://api.example.com"

    def test_timeout_str_format(self):
        """Test timeout error string formatting."""
        error = EuroleagueTimeoutError(
            "Request failed",
            timeout=30.0,
            url="https://api.example.com/teams",
        )

        error_str = str(error)
        assert "timeout=30.0s" in error_str
        assert "url=https://api.example.com/teams" in error_str
