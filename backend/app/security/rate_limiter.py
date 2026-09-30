"""In-memory rate limiter for authentication endpoints."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class RateLimitEntry:
    """Tracks rate limit state for a single key."""
    timestamps: List[float] = field(default_factory=list)
    failed_attempts: int = 0
    locked_until: float = 0.0


class RateLimiter:
    """Simple in-memory rate limiter for auth endpoints.

    Implements two types of limits:
    1. General rate limit: max_requests per window_seconds per IP.
    2. Failed login lockout: after max_failures consecutive failures for an email,
       lock that email for lockout_seconds.
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
        max_failures: int = 5,
        lockout_seconds: int = 900,  # 15 minutes
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        self._entries: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

    def check_rate_limit(self, key: str) -> Tuple[bool, int]:
        """Check if a request is allowed under the rate limit.

        Args:
            key: Identifier (e.g., IP address or email).

        Returns:
            Tuple of (allowed, retry_after_seconds).
            If allowed is False, retry_after_seconds indicates how long to wait.
        """
        now = time.time()
        entry = self._entries[key]

        # Clean old timestamps
        cutoff = now - self.window_seconds
        entry.timestamps = [t for t in entry.timestamps if t > cutoff]

        # Check if locked out
        if entry.locked_until > now:
            retry_after = int(entry.locked_until - now) + 1
            return False, retry_after

        # Check rate limit
        if len(entry.timestamps) >= self.max_requests:
            oldest = min(entry.timestamps) if entry.timestamps else now
            retry_after = int(oldest + self.window_seconds - now) + 1
            return False, max(retry_after, 1)

        # Record this request
        entry.timestamps.append(now)
        return True, 0

    def record_failure(self, key: str) -> None:
        """Record a failed authentication attempt.

        Args:
            key: Identifier (e.g., email address).
        """
        entry = self._entries[key]
        entry.failed_attempts += 1

        if entry.failed_attempts >= self.max_failures:
            entry.locked_until = time.time() + self.lockout_seconds
            entry.failed_attempts = 0  # Reset counter after lockout

    def record_success(self, key: str) -> None:
        """Record a successful authentication attempt (reset failure counter).

        Args:
            key: Identifier (e.g., email address).
        """
        entry = self._entries[key]
        entry.failed_attempts = 0

    def is_locked(self, key: str) -> Tuple[bool, int]:
        """Check if a key is currently locked out.

        Args:
            key: Identifier (e.g., email address).

        Returns:
            Tuple of (is_locked, retry_after_seconds).
        """
        entry = self._entries[key]
        now = time.time()

        if entry.locked_until > now:
            retry_after = int(entry.locked_until - now) + 1
            return True, retry_after

        return False, 0

    def cleanup(self) -> None:
        """Remove expired entries to prevent memory leaks.

        Should be called periodically (e.g., by a background task).
        """
        now = time.time()
        cutoff = now - self.window_seconds

        keys_to_delete = []
        for key, entry in self._entries.items():
            # Remove if no recent timestamps and not locked
            entry.timestamps = [t for t in entry.timestamps if t > cutoff]
            if not entry.timestamps and entry.locked_until <= now and entry.failed_attempts == 0:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._entries[key]


# Global rate limiter instance for auth endpoints
auth_rate_limiter = RateLimiter(
    max_requests=10,
    window_seconds=60,
    max_failures=5,
    lockout_seconds=900,
)
