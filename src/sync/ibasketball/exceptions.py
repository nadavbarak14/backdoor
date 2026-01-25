"""
iBasketball Exceptions Module

Provides custom exception classes for iBasketball data fetching operations.
These exceptions allow for specific error handling and meaningful error messages.

This module exports:
    - IBasketballError: Base exception for all iBasketball errors
    - IBasketballAPIError: HTTP/API request failures
    - IBasketballParseError: Data parsing failures
    - IBasketballRateLimitError: Rate limit exceeded
    - IBasketballTimeoutError: Request timeout
    - IBasketballLeagueNotFoundError: League not found in configuration

Usage:
    from src.sync.ibasketball.exceptions import IBasketballAPIError, IBasketballParseError

    try:
        data = client.fetch_event("12345")
    except IBasketballAPIError as e:
        print(f"API error: {e}")
    except IBasketballParseError as e:
        print(f"Parse error: {e}")
"""


class IBasketballError(Exception):
    """
    Base exception for iBasketball operations.

    All iBasketball specific exceptions inherit from this class,
    allowing for broad exception catching when needed.

    Attributes:
        message: Human-readable error description.

    Example:
        >>> try:
        ...     raise IBasketballError("Something went wrong")
        ... except IBasketballError as e:
        ...     print(f"iBasketball error: {e}")
        iBasketball error: Something went wrong
    """

    def __init__(self, message: str) -> None:
        """
        Initialize IBasketballError.

        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(message)


class IBasketballAPIError(IBasketballError):
    """
    Exception raised for HTTP/API request failures.

    Raised when an HTTP request to iBasketball APIs fails,
    including network errors, HTTP error status codes, and
    invalid responses.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code if available.
        url: The URL that was requested.
        response_body: Response body if available.

    Example:
        >>> try:
        ...     raise IBasketballAPIError(
        ...         "Server returned 500",
        ...         status_code=500,
        ...         url="https://ibasketball.co.il/wp-json/sportspress/v2/events"
        ...     )
        ... except IBasketballAPIError as e:
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
        Initialize IBasketballAPIError.

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


class IBasketballParseError(IBasketballError):
    """
    Exception raised for data parsing failures.

    Raised when parsing JSON responses or HTML pages fails,
    including JSON decode errors, missing required fields,
    and unexpected data structures.

    Attributes:
        message: Human-readable error description.
        resource_type: Type of resource being parsed.
        resource_id: ID of the resource being parsed.
        raw_data: Raw data that failed to parse.

    Example:
        >>> try:
        ...     raise IBasketballParseError(
        ...         "Missing 'teams' field",
        ...         resource_type="event",
        ...         resource_id="12345"
        ...     )
        ... except IBasketballParseError as e:
        ...     print(f"Parse error for {e.resource_type}: {e.message}")
        Parse error for event: Missing 'teams' field
    """

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        raw_data: str | None = None,
    ) -> None:
        """
        Initialize IBasketballParseError.

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


class IBasketballRateLimitError(IBasketballError):
    """
    Exception raised when rate limit is exceeded.

    Raised when the rate limiter blocks a request or when
    the remote API returns a rate limit response (HTTP 429).

    Attributes:
        message: Human-readable error description.
        retry_after: Suggested wait time in seconds.

    Example:
        >>> try:
        ...     raise IBasketballRateLimitError(
        ...         "Rate limit exceeded",
        ...         retry_after=5.0
        ...     )
        ... except IBasketballRateLimitError as e:
        ...     print(f"Rate limited, wait {e.retry_after}s")
        Rate limited, wait 5.0s
    """

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
    ) -> None:
        """
        Initialize IBasketballRateLimitError.

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


class IBasketballTimeoutError(IBasketballError):
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
        ...     raise IBasketballTimeoutError(
        ...         "Request timed out",
        ...         timeout=30.0,
        ...         url="https://ibasketball.co.il/wp-json/sportspress/v2/events"
        ...     )
        ... except IBasketballTimeoutError as e:
        ...     print(f"Timeout after {e.timeout}s: {e.url}")
        Timeout after 30.0s: https://ibasketball.co.il/wp-json/sportspress/v2/events
    """

    def __init__(
        self,
        message: str,
        timeout: float | None = None,
        url: str | None = None,
    ) -> None:
        """
        Initialize IBasketballTimeoutError.

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


class IBasketballLeagueNotFoundError(IBasketballError):
    """
    Exception raised when a league is not found in configuration.

    Raised when attempting to use a league key that is not
    configured in IBasketballConfig.

    Attributes:
        message: Human-readable error description.
        league_key: The league key that was not found.
        available_leagues: List of available league keys.

    Example:
        >>> try:
        ...     raise IBasketballLeagueNotFoundError(
        ...         "League not found",
        ...         league_key="invalid_league",
        ...         available_leagues=["liga_al", "liga_leumit"]
        ...     )
        ... except IBasketballLeagueNotFoundError as e:
        ...     print(f"Unknown league: {e.league_key}")
        Unknown league: invalid_league
    """

    def __init__(
        self,
        message: str,
        league_key: str | None = None,
        available_leagues: list[str] | None = None,
    ) -> None:
        """
        Initialize IBasketballLeagueNotFoundError.

        Args:
            message: Human-readable error description.
            league_key: The league key that was not found.
            available_leagues: List of available league keys.
        """
        self.league_key = league_key
        self.available_leagues = available_leagues or []
        super().__init__(message)

    def __str__(self) -> str:
        """Format error with league key and available leagues."""
        parts = [self.message]
        if self.league_key:
            parts.append(f"(league={self.league_key})")
        if self.available_leagues:
            parts.append(f"available={self.available_leagues}")
        return " ".join(parts)
