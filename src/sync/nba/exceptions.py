"""
NBA Exceptions Module

Custom exceptions for NBA data fetching operations.

This module exports:
    - NBAAPIError: Base exception for NBA API errors
    - NBAConnectionError: Connection failures
    - NBATimeoutError: Request timeout errors
    - NBARateLimitError: Rate limit exceeded
    - NBANotFoundError: Resource not found

Usage:
    from src.sync.nba.exceptions import NBAAPIError, NBARateLimitError

    try:
        data = client.get_boxscore(game_id)
    except NBARateLimitError:
        await asyncio.sleep(60)
    except NBAAPIError as e:
        logger.error(f"NBA API error: {e}")
"""


class NBAAPIError(Exception):
    """
    Base exception for NBA API errors.

    Attributes:
        message: Error message.
        status_code: HTTP status code, if applicable.
        response_text: Raw response text, if available.

    Example:
        >>> raise NBAAPIError("Failed to fetch data", status_code=500)
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        """
        Initialize NBAAPIError.

        Args:
            message: Error description.
            status_code: HTTP status code, if applicable.
            response_text: Raw response text, if available.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_text = response_text

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.status_code:
            return f"{self.message} (HTTP {self.status_code})"
        return self.message


class NBAConnectionError(NBAAPIError):
    """
    Exception raised when connection to NBA API fails.

    Example:
        >>> raise NBAConnectionError("Failed to connect to stats.nba.com")
    """

    def __init__(self, message: str = "Failed to connect to NBA API") -> None:
        """Initialize NBAConnectionError."""
        super().__init__(message)


class NBATimeoutError(NBAAPIError):
    """
    Exception raised when NBA API request times out.

    Example:
        >>> raise NBATimeoutError("Request timed out after 30 seconds")
    """

    def __init__(self, message: str = "NBA API request timed out") -> None:
        """Initialize NBATimeoutError."""
        super().__init__(message)


class NBARateLimitError(NBAAPIError):
    """
    Exception raised when rate limit is exceeded.

    Attributes:
        retry_after: Suggested wait time in seconds before retrying.

    Example:
        >>> raise NBARateLimitError(retry_after=60)
    """

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
    ) -> None:
        """
        Initialize NBARateLimitError.

        Args:
            message: Error description.
            retry_after: Suggested wait time in seconds.
        """
        super().__init__(message, status_code=429)
        self.retry_after = retry_after

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.retry_after:
            return f"{self.message} (retry after {self.retry_after}s)"
        return self.message


class NBANotFoundError(NBAAPIError):
    """
    Exception raised when a requested resource is not found.

    Attributes:
        resource_type: Type of resource (game, player, team, etc.).
        resource_id: ID of the resource that was not found.

    Example:
        >>> raise NBANotFoundError("game", "0022300001")
    """

    def __init__(
        self, resource_type: str, resource_id: str, message: str | None = None
    ) -> None:
        """
        Initialize NBANotFoundError.

        Args:
            resource_type: Type of resource.
            resource_id: ID of the resource.
            message: Optional custom message.
        """
        msg = message or f"{resource_type} not found: {resource_id}"
        super().__init__(msg, status_code=404)
        self.resource_type = resource_type
        self.resource_id = resource_id
