"""User repository — basic CRUD operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Data access layer for User entity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by primary key."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case-insensitive)."""
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password_hash: str,
        timezone: str = "UTC",
    ) -> User:
        """Create a new user."""
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            timezone=timezone,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email exists."""
        result = await self.session.execute(
            select(func.count()).select_from(User).where(
                func.lower(User.email) == email.lower()
            )
        )
        count = result.scalar_one()
        return count > 0
