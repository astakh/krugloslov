"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from typing import Optional

from fastapi import Cookie, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.exceptions import UnauthorizedException
from app.models.user import User
from app.security.jwt import JWTDecodeError, decode_access_token


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Dependency to extract and validate the current user from the access token.

    The access token is expected in the Authorization header as a Bearer token.

    Args:
        request: FastAPI request object.
        session: Database session.

    Returns:
        The authenticated User object.

    Raises:
        UnauthorizedException: If token is missing, invalid, or user not found.
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise UnauthorizedException(message="Требуется авторизация")

    # Parse Bearer token
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException(message="Неверный формат токена")

    token = parts[1]

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (JWTDecodeError, KeyError, ValueError) as e:
        raise UnauthorizedException(message="Недействительный или просроченный токен")

    # Fetch user from database
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(message="Пользователь не найден")

    return user


async def get_current_user_optional(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """Dependency to optionally extract the current user (returns None if not authenticated).

    Args:
        request: FastAPI request object.
        session: Database session.

    Returns:
        The authenticated User object or None.
    """
    try:
        return await get_current_user(request, session)
    except UnauthorizedException:
        return None


async def get_refresh_token_from_cookie(
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
) -> str:
    """Dependency to extract refresh token from cookie.

    Args:
        refresh_token: The refresh token from the cookie.

    Returns:
        The refresh token string.

    Raises:
        UnauthorizedException: If refresh token is missing.
    """
    if not refresh_token:
        raise UnauthorizedException(message="Refresh token отсутствует")
    return refresh_token


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to require admin privileges.

    Args:
        current_user: The authenticated user.

    Returns:
        The admin User object.

    Raises:
        ForbiddenException: If user is not an admin.
    """
    from app.exceptions import ForbiddenException
    
    if not current_user.is_admin:
        raise ForbiddenException(message="Доступ запрещён. Требуются права администратора.")
    
    return current_user
