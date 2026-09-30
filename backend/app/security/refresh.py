"""Refresh token generation and hashing utilities."""

from __future__ import annotations

import hashlib
import secrets


def generate_refresh_token() -> str:
    """Generate a cryptographically secure random refresh token.

    Returns:
        A 64-character hex string (256 bits of entropy).
    """
    return secrets.token_hex(32)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token using SHA-256.

    Args:
        token: Plaintext refresh token.

    Returns:
        SHA-256 hex digest.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_family_id() -> str:
    """Generate a unique family ID for token rotation tracking.

    Returns:
        A 32-character hex string.
    """
    return secrets.token_hex(16)
