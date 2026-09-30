"""Tests for rate limiter."""

from __future__ import annotations

import time

import pytest

from app.security.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_allows_requests_under_limit(self):
        """Rate limiter should allow requests under the limit."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        for _ in range(3):
            allowed, retry_after = limiter.check_rate_limit("test_key")
            assert allowed is True
            assert retry_after == 0

    def test_blocks_requests_over_limit(self):
        """Rate limiter should block requests over the limit."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # First 2 requests should be allowed
        allowed1, _ = limiter.check_rate_limit("test_key")
        allowed2, _ = limiter.check_rate_limit("test_key")
        assert allowed1 is True
        assert allowed2 is True
        
        # Third request should be blocked
        allowed3, retry_after = limiter.check_rate_limit("test_key")
        assert allowed3 is False
        assert retry_after > 0

    def test_different_keys_independent(self):
        """Different keys should have independent rate limits."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # Exhaust limit for key1
        limiter.check_rate_limit("key1")
        limiter.check_rate_limit("key1")
        allowed1, _ = limiter.check_rate_limit("key1")
        assert allowed1 is False
        
        # key2 should still be allowed
        allowed2, _ = limiter.check_rate_limit("key2")
        assert allowed2 is True

    def test_record_failure_locks_after_max_failures(self):
        """After max_failures, the key should be locked."""
        limiter = RateLimiter(max_failures=3, lockout_seconds=60)
        
        # Record failures
        for _ in range(3):
            limiter.record_failure("test_email")
        
        # Should be locked
        is_locked, retry_after = limiter.is_locked("test_email")
        assert is_locked is True
        assert retry_after > 0

    def test_record_success_resets_failures(self):
        """record_success should reset the failure counter."""
        limiter = RateLimiter(max_failures=3, lockout_seconds=60)
        
        # Record some failures
        limiter.record_failure("test_email")
        limiter.record_failure("test_email")
        
        # Record success
        limiter.record_success("test_email")
        
        # Should not be locked
        is_locked, _ = limiter.is_locked("test_email")
        assert is_locked is False
        
        # Can fail again without lockout
        limiter.record_failure("test_email")
        limiter.record_failure("test_email")
        is_locked, _ = limiter.is_locked("test_email")
        assert is_locked is False

    def test_cleanup_removes_expired_entries(self):
        """cleanup should remove expired entries."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Add some requests
        limiter.check_rate_limit("test_key")
        limiter.check_rate_limit("test_key")
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Cleanup
        limiter.cleanup()
        
        # Should be allowed again
        allowed, _ = limiter.check_rate_limit("test_key")
        assert allowed is True
