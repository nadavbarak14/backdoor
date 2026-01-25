"""
Rate Limiter Module

Provides a thread-safe token bucket rate limiter for controlling
request rates to external APIs. Supports configurable rates, burst
allowance, and exponential backoff for retries.

This module exports:
    - RateLimiter: Token bucket rate limiter class

Usage:
    from src.sync.winner.rate_limiter import RateLimiter

    limiter = RateLimiter(requests_per_second=2.0, burst_size=5)

    # Wait for permission before making request
    limiter.acquire()
    response = httpx.get("https://api.example.com")

    # Or use as context manager
    with limiter:
        response = httpx.get("https://api.example.com")
"""

import threading
import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """
    Thread-safe token bucket rate limiter.

    Implements the token bucket algorithm to control request rates.
    Tokens are added at a fixed rate (requests_per_second), and each
    request consumes one token. Burst allowance permits short bursts
    of requests up to the bucket size.

    Attributes:
        requests_per_second: Rate at which tokens are added.
        burst_size: Maximum number of tokens (bucket capacity).
        _tokens: Current number of available tokens.
        _last_update: Timestamp of last token update.
        _lock: Thread lock for synchronization.

    Example:
        >>> limiter = RateLimiter(requests_per_second=2.0, burst_size=5)
        >>> for _ in range(10):
        ...     limiter.acquire()
        ...     print("Request made")

        >>> # Or with context manager
        >>> with limiter:
        ...     response = make_request()
    """

    requests_per_second: float = 2.0
    burst_size: int = 5
    _tokens: float = field(init=False, repr=False)
    _last_update: float = field(init=False, repr=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize token bucket with full capacity."""
        self._tokens = float(self.burst_size)
        self._last_update = time.monotonic()

    def _refill(self) -> None:
        """
        Refill tokens based on elapsed time.

        Called internally before checking token availability.
        Adds tokens proportional to time elapsed since last update,
        capped at burst_size.
        """
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(
            self.burst_size,
            self._tokens + elapsed * self.requests_per_second,
        )
        self._last_update = now

    def acquire(self, timeout: float | None = None) -> bool:
        """
        Acquire a token, blocking if necessary.

        Waits until a token is available or timeout expires.
        If no timeout is specified, waits indefinitely.

        Args:
            timeout: Maximum time to wait in seconds. None for no limit.

        Returns:
            bool: True if token acquired, False if timeout expired.

        Raises:
            ValueError: If timeout is negative.

        Example:
            >>> limiter = RateLimiter(requests_per_second=1.0)
            >>> if limiter.acquire(timeout=5.0):
            ...     print("Got token")
            ... else:
            ...     print("Timeout")
        """
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")

        start_time = time.monotonic()

        while True:
            with self._lock:
                self._refill()

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True

                # Calculate wait time for next token
                wait_time = (1.0 - self._tokens) / self.requests_per_second

            # Check timeout
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                remaining = timeout - elapsed
                if remaining <= 0:
                    return False
                wait_time = min(wait_time, remaining)

            # Wait for tokens to accumulate
            time.sleep(wait_time)

    def try_acquire(self) -> bool:
        """
        Try to acquire a token without blocking.

        Returns immediately whether a token was available or not.

        Returns:
            bool: True if token acquired, False if no tokens available.

        Example:
            >>> limiter = RateLimiter(requests_per_second=1.0)
            >>> if limiter.try_acquire():
            ...     print("Got token immediately")
            ... else:
            ...     print("No tokens available")
        """
        with self._lock:
            self._refill()

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True

            return False

    def wait_time(self) -> float:
        """
        Get estimated wait time for next available token.

        Returns:
            float: Estimated seconds until a token is available.
                   Returns 0 if a token is immediately available.

        Example:
            >>> limiter = RateLimiter(requests_per_second=1.0)
            >>> limiter.acquire()  # Use up tokens
            >>> wait = limiter.wait_time()
            >>> print(f"Wait {wait:.2f}s for next token")
        """
        with self._lock:
            self._refill()

            if self._tokens >= 1.0:
                return 0.0

            return (1.0 - self._tokens) / self.requests_per_second

    def reset(self) -> None:
        """
        Reset the rate limiter to full capacity.

        Useful for testing or after long idle periods.

        Example:
            >>> limiter = RateLimiter()
            >>> limiter.reset()  # Start fresh with full tokens
        """
        with self._lock:
            self._tokens = float(self.burst_size)
            self._last_update = time.monotonic()

    @property
    def available_tokens(self) -> float:
        """
        Get current number of available tokens.

        Returns:
            float: Number of tokens currently available (may be fractional).

        Example:
            >>> limiter = RateLimiter(burst_size=5)
            >>> print(f"Available: {limiter.available_tokens:.1f}")
            Available: 5.0
        """
        with self._lock:
            self._refill()
            return self._tokens

    def __enter__(self) -> "RateLimiter":
        """
        Context manager entry - acquire a token.

        Blocks until a token is available.

        Returns:
            RateLimiter: Self for method chaining.

        Example:
            >>> with RateLimiter() as limiter:
            ...     # Token acquired, make request
            ...     pass
        """
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit - no cleanup needed.

        Args:
            exc_type: Exception type if raised.
            exc_val: Exception value if raised.
            exc_tb: Exception traceback if raised.
        """
        pass


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Uses exponential backoff formula: delay = base_delay * 2^attempt,
    capped at max_delay. Optional jitter adds randomness to prevent
    thundering herd problems.

    Args:
        attempt: Zero-based attempt number (0 for first retry).
        base_delay: Base delay in seconds.
        max_delay: Maximum delay cap in seconds.
        jitter: Whether to add random jitter (0-50% of delay).

    Returns:
        float: Delay in seconds before next retry.

    Example:
        >>> calculate_backoff(0)  # ~1.0s
        >>> calculate_backoff(1)  # ~2.0s
        >>> calculate_backoff(2)  # ~4.0s
        >>> calculate_backoff(5)  # ~30.0s (capped)
    """
    import random

    delay = min(base_delay * (2**attempt), max_delay)

    if jitter:
        # Add 0-50% jitter
        delay = delay * (1 + random.random() * 0.5)

    return min(delay, max_delay)
