"""
Euroleague Exceptions Module

Provides custom exception classes for Euroleague data fetching operations.
These exceptions allow for specific error handling and meaningful error messages.

This module exports:
    - EuroleagueError: Base exception for all Euroleague errors
    - EuroleagueAPIError: HTTP/API request failures
    - EuroleagueParseError: Data parsing failures
    - EuroleagueRateLimitError: Rate limit exceeded
    - EuroleagueTimeoutError: Request timeout

Usage:
    from src.sync.euroleague.exceptions import EuroleagueAPIError, EuroleagueParseError

    try:
        data = client.fetch_boxscore(2024, 1)
    except EuroleagueAPIError as e:
        print(f"API error: {e}")
    except EuroleagueParseError as e:
        print(f"Parse error: {e}")
"""


class EuroleagueError(Exception):
    """
    Base exception for Euroleague operations.

    All Euroleague specific exceptions inherit from this class,
    allowing for broad exception catching when needed.

    Attributes:
        message: Human-readable error description.

    Example:
        >>> try:
        ...     raise EuroleagueError("Something went wrong")
        ... except EuroleagueError as e:
        ...     print(f"Euroleague error: {e}")
        Euroleague error: Something went wrong
    """

    def __init__(self, message: str) -> None:
        """
        Initialize EuroleagueError.

        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(message)


class EuroleagueAPIError(EuroleagueError):
    """
    Exception raised for HTTP/API request failures.

    Raised when an HTTP request to Euroleague APIs fails,
    including network errors, HTTP error status codes, and
    invalid responses.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code if available.
        url: The URL that was requested.
        response_body: Response body if available.

    Example:
        >>> try:
        ...     raise EuroleagueAPIError(
        ...         "Server returned 500",
        ...         status_code=500,
        ...         url="https://api-live.euroleague.net/v1/teams"
        ...     )
        ... except EuroleagueAPIError as e:
        ...     print(f"API error {e.status_code}: {e.message}")
        API error 500: Server returned 500
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        url: str | None = None,
        response_body: str | None = None,
    ) -> None:
        """
        Initialize EuroleagueAPIError.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code if available.
            url: The URL that was requested.
            response_body: Response body if available.
        """
        self.status_code = status_code
        self.url = url
        self.response_body = response_body
        super().__init__(message)

    def __str__(self) -> str:
        """Format error with status code and URL if available."""
        parts = [self.message]
        if self.status_code:
            parts.append(f"(status={self.status_code})")
        if self.url:
            parts.append(f"url={self.url}")
        return " ".join(parts)


class EuroleagueParseError(EuroleagueError):
    """
    Exception raised for data parsing failures.

    Raised when parsing JSON or XML responses fails,
    including decode errors, missing required fields,
    and unexpected data structures.

    Attributes:
        message: Human-readable error description.
        resource_type: Type of resource being parsed.
        resource_id: ID of the resource being parsed.
        raw_data: Raw data that failed to parse.

    Example:
        >>> try:
        ...     raise EuroleagueParseError(
        ...         "Missing 'Stats' field",
        ...         resource_type="boxscore",
        ...         resource_id="E2024_1"
        ...     )
        ... except EuroleagueParseError as e:
        ...     print(f"Parse error for {e.resource_type}: {e.message}")
        Parse error for boxscore: Missing 'Stats' field
    """

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        raw_data: str | None = None,
    ) -> None:
        """
        Initialize EuroleagueParseError.

        Args:
            message: Human-readable error description.
            resource_type: Type of resource being parsed.
            resource_id: ID of the resource being parsed.
            raw_data: Raw data that failed to parse.
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.raw_data = raw_data
        super().__init__(message)

    def __str__(self) -> str:
        """Format error with resource context if available."""
        parts = [self.message]
        if self.resource_type:
            parts.append(f"(type={self.resource_type})")
        if self.resource_id:
            parts.append(f"id={self.resource_id}")
        return " ".join(parts)


class EuroleagueRateLimitError(EuroleagueError):
    """
    Exception raised when rate limit is exceeded.

    Raised when the rate limiter blocks a request or when
    the remote API returns a rate limit response (HTTP 429).

    Attributes:
        message: Human-readable error description.
        retry_after: Suggested wait time in seconds.

    Example:
        >>> try:
        ...     raise EuroleagueRateLimitError(
        ...         "Rate limit exceeded",
        ...         retry_after=5.0
        ...     )
        ... except EuroleagueRateLimitError as e:
        ...     print(f"Rate limited, wait {e.retry_after}s")
        Rate limited, wait 5.0s
    """

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
    ) -> None:
        """
        Initialize EuroleagueRateLimitError.

        Args:
            message: Human-readable error description.
            retry_after: Suggested wait time in seconds.
        """
        self.retry_after = retry_after
        super().__init__(message)

    def __str__(self) -> str:
        """Format error with retry time if available."""
        if self.retry_after:
            return f"{self.message} (retry after {self.retry_after:.1f}s)"
        return self.message


class EuroleagueTimeoutError(EuroleagueError):
    """
    Exception raised for request timeouts.

    Raised when an HTTP request times out after the configured
    timeout period.

    Attributes:
        message: Human-readable error description.
        timeout: The timeout value that was exceeded.
        url: The URL that timed out.

    Example:
        >>> try:
        ...     raise EuroleagueTimeoutError(
        ...         "Request timed out",
        ...         timeout=30.0,
        ...         url="https://api-live.euroleague.net/v1/teams"
        ...     )
        ... except EuroleagueTimeoutError as e:
        ...     print(f"Timeout after {e.timeout}s: {e.url}")
        Timeout after 30.0s: https://api-live.euroleague.net/v1/teams
    """

    def __init__(
        self,
        message: str,
        timeout: float | None = None,
        url: str | None = None,
    ) -> None:
        """
        Initialize EuroleagueTimeoutError.

        Args:
            message: Human-readable error description.
            timeout: The timeout value that was exceeded.
            url: The URL that timed out.
        """
        self.timeout = timeout
        self.url = url
        super().__init__(message)

    def __str__(self) -> str:
        """Format error with timeout and URL if available."""
        parts = [self.message]
        if self.timeout:
            parts.append(f"(timeout={self.timeout}s)")
        if self.url:
            parts.append(f"url={self.url}")
        return " ".join(parts)
