"""JWT access token utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

from app.config import settings


class JWTDecodeError(Exception):
    """Raised when JWT decoding fails."""
    pass


def create_access_token(user_id: int, email: str) -> str:
    """Create a signed JWT access token.

    Args:
        user_id: User's database ID.
        email: User's email address.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_TTL_MIN)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        JWTDecodeError: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError as e:
        raise JWTDecodeError(f"Invalid token: {e}")
