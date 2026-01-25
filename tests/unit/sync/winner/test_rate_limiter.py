"""
Rate Limiter Tests

Tests for src/sync/winner/rate_limiter.py covering:
- Token bucket algorithm behavior
- Blocking and non-blocking acquire
- Burst handling
- Thread safety
- Exponential backoff calculation
"""

import threading
import time

import pytest

from src.sync.winner.rate_limiter import RateLimiter, calculate_backoff


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_initial_tokens(self):
        """Rate limiter should start with full bucket."""
        limiter = RateLimiter(requests_per_second=2.0, burst_size=5)
        assert limiter.available_tokens == 5.0

    def test_acquire_consumes_token(self):
        """Acquire should consume one token."""
        limiter = RateLimiter(requests_per_second=2.0, burst_size=5)
        initial = limiter.available_tokens

        limiter.acquire()

        assert limiter.available_tokens < initial

    def test_try_acquire_succeeds_with_tokens(self):
        """Try acquire should succeed when tokens available."""
        limiter = RateLimiter(requests_per_second=2.0, burst_size=5)

        result = limiter.try_acquire()

        assert result is True

    def test_try_acquire_fails_without_tokens(self):
        """Try acquire should fail when no tokens available."""
        limiter = RateLimiter(requests_per_second=0.1, burst_size=1)

        # Use up the single token
        limiter.acquire()

        # Should fail immediately
        result = limiter.try_acquire()

        assert result is False

    def test_acquire_timeout(self):
        """Acquire should return False on timeout."""
        limiter = RateLimiter(requests_per_second=0.1, burst_size=1)

        # Use up the token
        limiter.acquire()

        # Should timeout
        start = time.monotonic()
        result = limiter.acquire(timeout=0.1)
        elapsed = time.monotonic() - start

        assert result is False
        assert elapsed >= 0.1
        assert elapsed < 0.5  # Should not take too long

    def test_acquire_invalid_timeout(self):
        """Acquire should raise ValueError for negative timeout."""
        limiter = RateLimiter()

        with pytest.raises(ValueError, match="timeout must be non-negative"):
            limiter.acquire(timeout=-1)

    def test_token_refill(self):
        """Tokens should refill over time."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=5)

        # Use up all tokens
        for _ in range(5):
            limiter.try_acquire()

        assert limiter.available_tokens < 1.0

        # Wait for refill
        time.sleep(0.2)

        # Should have some tokens now
        assert limiter.available_tokens >= 1.0

    def test_burst_handling(self):
        """Should allow burst of requests up to bucket size."""
        limiter = RateLimiter(requests_per_second=1.0, burst_size=5)

        # Should be able to make 5 requests immediately
        results = [limiter.try_acquire() for _ in range(5)]

        assert all(results)
        assert sum(results) == 5

        # 6th should fail
        assert limiter.try_acquire() is False

    def test_wait_time_calculation(self):
        """Wait time should be calculated correctly."""
        limiter = RateLimiter(requests_per_second=2.0, burst_size=1)

        # Use up the token
        limiter.acquire()

        wait_time = limiter.wait_time()

        # Should be approximately 0.5 seconds (1/2 rps)
        assert 0 < wait_time <= 0.6

    def test_wait_time_zero_when_available(self):
        """Wait time should be zero when tokens available."""
        limiter = RateLimiter(burst_size=5)

        wait_time = limiter.wait_time()

        assert wait_time == 0.0

    def test_reset(self):
        """Reset should restore full capacity."""
        limiter = RateLimiter(burst_size=5)

        # Use some tokens
        for _ in range(3):
            limiter.acquire()

        assert limiter.available_tokens < 5.0

        limiter.reset()

        assert limiter.available_tokens == 5.0

    def test_context_manager(self):
        """Context manager should acquire token."""
        limiter = RateLimiter(burst_size=5)
        initial = limiter.available_tokens

        with limiter:
            pass

        # Token should have been consumed
        assert limiter.available_tokens < initial

    def test_thread_safety(self):
        """Rate limiter should be thread-safe."""
        limiter = RateLimiter(requests_per_second=100.0, burst_size=10)
        acquired_count = 0
        lock = threading.Lock()

        def acquire_tokens():
            nonlocal acquired_count
            for _ in range(5):
                if limiter.try_acquire():
                    with lock:
                        acquired_count += 1

        threads = [threading.Thread(target=acquire_tokens) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have acquired exactly burst_size tokens
        assert acquired_count == 10


class TestCalculateBackoff:
    """Tests for the calculate_backoff function."""

    def test_base_delay(self):
        """First attempt should use base delay."""
        delay = calculate_backoff(0, base_delay=1.0, jitter=False)
        assert delay == 1.0

    def test_exponential_increase(self):
        """Delay should increase exponentially."""
        delays = [calculate_backoff(i, base_delay=1.0, jitter=False) for i in range(4)]

        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0
        assert delays[3] == 8.0

    def test_max_delay_cap(self):
        """Delay should be capped at max_delay."""
        delay = calculate_backoff(10, base_delay=1.0, max_delay=30.0, jitter=False)

        assert delay == 30.0

    def test_jitter_adds_variation(self):
        """Jitter should add random variation."""
        delays = [
            calculate_backoff(0, base_delay=1.0, max_delay=30.0, jitter=True)
            for _ in range(10)
        ]

        # With jitter, not all delays should be exactly the same
        unique_delays = set(delays)
        assert len(unique_delays) > 1

    def test_jitter_range(self):
        """Jitter should add 0-50% to delay."""
        for _ in range(20):
            delay = calculate_backoff(0, base_delay=1.0, max_delay=30.0, jitter=True)
            # Base is 1.0, with 0-50% jitter should be 1.0-1.5
            assert 1.0 <= delay <= 1.5

    def test_custom_base_delay(self):
        """Should respect custom base delay."""
        delay = calculate_backoff(0, base_delay=2.0, jitter=False)
        assert delay == 2.0

    def test_custom_max_delay(self):
        """Should respect custom max delay."""
        delay = calculate_backoff(5, base_delay=1.0, max_delay=10.0, jitter=False)
        assert delay == 10.0
