"""
Sync Exceptions Module

Defines exception classes for sync-related errors in the Basketball Analytics
Platform. These exceptions provide specific error types for different failure
scenarios during data synchronization.

Usage:
    from src.sync.exceptions import (
        SyncError,
        AdapterError,
        GameNotFoundError,
        RateLimitError
    )

    try:
        game = adapter.get_game_boxscore("game-123")
    except GameNotFoundError as e:
        logger.warning(f"Game not found: {e.external_id}")
    except AdapterError as e:
        logger.error(f"Adapter failed: {e}")
"""


class SyncError(Exception):
    """
    Base exception for all sync-related errors.

    All sync exceptions inherit from this class, allowing callers to catch
    any sync error with a single except clause.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source (e.g., "winner", "euroleague")

    Example:
        >>> raise SyncError("Connection failed", source="winner")
    """

    def __init__(self, message: str, source: str | None = None):
        """
        Initialize SyncError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
        """
        self.message = message
        self.source = source
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with source if available."""
        if self.source:
            return f"[{self.source}] {self.message}"
        return self.message


class AdapterError(SyncError):
    """
    Exception raised when an adapter encounters an error.

    This is the general exception for adapter failures that don't fit
    into more specific categories.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source
        original_error: The underlying exception that caused this error

    Example:
        >>> raise AdapterError(
        ...     "Failed to parse response",
        ...     source="euroleague",
        ...     original_error=json.JSONDecodeError(...)
        ... )
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        original_error: Exception | None = None,
    ):
        """
        Initialize AdapterError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
            original_error: The underlying exception
        """
        self.original_error = original_error
        super().__init__(message, source)


class ConnectionError(SyncError):
    """
    Exception raised when connection to external API fails.

    This includes network errors, DNS resolution failures, and
    connection timeouts.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source
        url: The URL that failed to connect

    Example:
        >>> raise ConnectionError(
        ...     "Connection timeout",
        ...     source="winner",
        ...     url="https://api.winner.co.il/games"
        ... )
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        url: str | None = None,
    ):
        """
        Initialize ConnectionError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
            url: The URL that failed
        """
        self.url = url
        super().__init__(message, source)


class RateLimitError(SyncError):
    """
    Exception raised when rate limit is exceeded.

    Indicates that the external API has throttled requests and the
    caller should wait before retrying.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source
        retry_after: Seconds to wait before retrying

    Example:
        >>> raise RateLimitError(
        ...     "Too many requests",
        ...     source="euroleague",
        ...     retry_after=60
        ... )
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        retry_after: int | None = None,
    ):
        """
        Initialize RateLimitError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
            retry_after: Seconds to wait before retrying
        """
        self.retry_after = retry_after
        super().__init__(message, source)


class GameNotFoundError(SyncError):
    """
    Exception raised when a requested game is not found.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source
        external_id: The external game ID that was not found

    Example:
        >>> raise GameNotFoundError(
        ...     "Game not found",
        ...     source="winner",
        ...     external_id="game-123"
        ... )
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        external_id: str | None = None,
    ):
        """
        Initialize GameNotFoundError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
            external_id: The external game ID that was not found
        """
        self.external_id = external_id
        super().__init__(message, source)


class SeasonNotFoundError(SyncError):
    """
    Exception raised when a requested season is not found.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source
        external_id: The external season ID that was not found

    Example:
        >>> raise SeasonNotFoundError(
        ...     "Season not found",
        ...     source="euroleague",
        ...     external_id="2024-25"
        ... )
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        external_id: str | None = None,
    ):
        """
        Initialize SeasonNotFoundError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
            external_id: The external season ID that was not found
        """
        self.external_id = external_id
        super().__init__(message, source)


class PlayerNotFoundError(SyncError):
    """
    Exception raised when a requested player is not found.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source
        external_id: The external player ID that was not found

    Example:
        >>> raise PlayerNotFoundError(
        ...     "Player not found",
        ...     source="winner",
        ...     external_id="player-456"
        ... )
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        external_id: str | None = None,
    ):
        """
        Initialize PlayerNotFoundError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
            external_id: The external player ID that was not found
        """
        self.external_id = external_id
        super().__init__(message, source)


class DataValidationError(SyncError):
    """
    Exception raised when synced data fails validation.

    This indicates that the external API returned data that doesn't
    meet our requirements or is malformed.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source
        field: The field that failed validation
        value: The invalid value

    Example:
        >>> raise DataValidationError(
        ...     "Invalid score value",
        ...     source="euroleague",
        ...     field="home_score",
        ...     value=-5
        ... )
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        field: str | None = None,
        value: object | None = None,
    ):
        """
        Initialize DataValidationError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
            field: The field that failed validation
            value: The invalid value
        """
        self.field = field
        self.value = value
        super().__init__(message, source)


class SyncConfigError(SyncError):
    """
    Exception raised when sync configuration is invalid.

    Attributes:
        message: Human-readable error description
        source: Name of the sync source
        config_key: The configuration key that is invalid

    Example:
        >>> raise SyncConfigError(
        ...     "Missing API key",
        ...     source="winner",
        ...     config_key="WINNER_API_KEY"
        ... )
    """

    def __init__(
        self,
        message: str,
        source: str | None = None,
        config_key: str | None = None,
    ):
        """
        Initialize SyncConfigError.

        Args:
            message: Human-readable error description
            source: Name of the sync source
            config_key: The configuration key that is invalid
        """
        self.config_key = config_key
        super().__init__(message, source)
