"""Authentication service — business logic for auth operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AppException, UnauthorizedException
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.security import (
    create_access_token,
    generate_family_id,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.services.events import record_event


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, email: str, password: str) -> Tuple[User, str, str]:
        """Register a new user.

        Args:
            email: User's email (already normalized to lowercase).
            password: Plaintext password.

        Returns:
            Tuple of (user, access_token, refresh_token).

        Raises:
            AppException: If email is already taken (409).
        """
        # Check if email exists
        existing = await self.session.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="email_taken",
                message="Пользователь с таким email уже существует",
                status_code=409,
            )

        # Create user
        user = User(
            email=email,
            password_hash=hash_password(password),
        )
        self.session.add(user)
        await self.session.flush()

        # Record signup event
        await record_event(self.session, user.id, "signup")

        # Generate tokens
        access_token = create_access_token(user.id, user.email)
        refresh_token = await self._create_refresh_token(user.id)

        await self.session.commit()
        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> Tuple[User, str, str]:
        """Authenticate a user and issue tokens.

        Args:
            email: User's email (already normalized to lowercase).
            password: Plaintext password.

        Returns:
            Tuple of (user, access_token, refresh_token).

        Raises:
            UnauthorizedException: If credentials are invalid.
        """
        # Find user
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException(message="Неверный email или пароль")

        # Generate tokens
        access_token = create_access_token(user.id, user.email)
        refresh_token = await self._create_refresh_token(user.id)

        await self.session.commit()
        return user, access_token, refresh_token

    async def refresh(self, old_refresh_token: str) -> Tuple[str, str]:
        """Refresh tokens using a valid refresh token.

        Implements token rotation with family tracking.
        If the token was already used (replay attack), revokes the entire family.

        Args:
            old_refresh_token: The plaintext refresh token from the cookie.

        Returns:
            Tuple of (new_access_token, new_refresh_token).

        Raises:
            UnauthorizedException: If token is invalid, expired, or revoked.
        """
        token_hash = hash_refresh_token(old_refresh_token)

        # Find the token in database
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise UnauthorizedException(message="Недействительный токен")

        # Check if token is expired
        if token_record.expires_at < datetime.now(timezone.utc):
            raise UnauthorizedException(message="Срок действия токена истёк")

        # Check if token was already used (replay attack)
        if token_record.revoked_at is not None:
            # This is a replay attack — revoke entire family
            await self._revoke_family(token_record.family_id)
            await self.session.commit()
            raise UnauthorizedException(message="Токен уже использован. Все сессии отозваны.")

        # Get user
        result = await self.session.execute(
            select(User).where(User.id == token_record.user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise UnauthorizedException(message="Пользователь не найден")

        # Mark old token as used
        token_record.revoked_at = datetime.now(timezone.utc)

        # Create new refresh token with same family_id
        new_refresh_token = await self._create_refresh_token(
            user.id, family_id=token_record.family_id, replaced_by=token_record.id
        )

        # Generate new access token
        new_access_token = create_access_token(user.id, user.email)

        await self.session.commit()
        return new_access_token, new_refresh_token

    async def logout(self, refresh_token: str) -> None:
        """Revoke a refresh token (logout).

        Args:
            refresh_token: The plaintext refresh token to revoke.
        """
        token_hash = hash_refresh_token(refresh_token)

        # Find and revoke the token
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.session.commit()

    async def _create_refresh_token(
        self,
        user_id: int,
        family_id: Optional[str] = None,
        replaced_by: Optional[int] = None,
    ) -> str:
        """Create a new refresh token in the database.

        Args:
            user_id: User ID.
            family_id: Optional family ID (for token rotation).
            replaced_by: Optional ID of the token this one replaces.

        Returns:
            The plaintext refresh token.
        """
        token = generate_refresh_token()
        token_hash = hash_refresh_token(token)

        if family_id is None:
            family_id = generate_family_id()

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)

        refresh_token_record = RefreshToken(
            user_id=user_id,
            family_id=family_id,
            token_hash=token_hash,
            expires_at=expires_at,
            replaced_by=replaced_by,
        )
        self.session.add(refresh_token_record)
        await self.session.flush()

        return token

    async def _revoke_family(self, family_id: str) -> None:
        """Revoke all tokens in a family (security measure for replay attacks).

        Args:
            family_id: The family ID to revoke.
        """
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
