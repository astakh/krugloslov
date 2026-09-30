"""Service for admin users management."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models import Event, RefreshToken, User
from app.schemas.admin_management import AdminUserItem, AdminUsersListResponse
from app.security import hash_password


class AdminUsersService:
    """Service for managing users in admin panel."""

    def __init__(self, session: AsyncSession, admin: User):
        self.session = session
        self.admin = admin

    async def get_users(
        self,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminUsersListResponse:
        """Get paginated list of users."""
        # Build base query
        query = select(User).order_by(User.created_at.desc())

        if search:
            # Search by email (case-insensitive)
            search_pattern = f"%{search.lower()}%"
            query = query.where(func.lower(User.email).like(search_pattern))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        users = result.scalars().all()

        # Build response items
        items = [
            AdminUserItem(
                id=user.id,
                email=user.email,
                is_onboarded=user.is_onboarded,
                is_admin=user.is_admin,
                created_at=user.created_at,
            )
            for user in users
        ]

        return AdminUsersListResponse(
            users=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def reset_password(self, user_id: int) -> tuple[str, str]:
        """
        Reset user's password and revoke all sessions.
        
        Returns:
            Tuple of (temporary_password, message)
        """
        # Get target user
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise AppException(
                status_code=404,
                code="user_not_found",
                message="User not found",
            )

        # Cannot reset own password through this endpoint
        if target_user.id == self.admin.id:
            raise AppException(
                status_code=400,
                code="cannot_reset_own_password",
                message="Cannot reset own password through admin panel",
            )

        # Generate temporary password
        temporary_password = self._generate_temporary_password()

        # Hash and update password
        new_hash = hash_password(temporary_password)
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(password_hash=new_hash)
        )

        # Revoke all refresh tokens
        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )

        # Log admin action
        await self._log_admin_action(
            action="reset_password",
            target_id=user_id,
            details={"target_email": target_user.email},
        )

        await self.session.commit()

        return temporary_password, "Password reset successfully"

    def _generate_temporary_password(self) -> str:
        """Generate a secure temporary password."""
        # Generate 12-character password with mixed case, digits, and symbols
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        password = "".join(secrets.choice(alphabet) for _ in range(12))
        
        # Ensure at least one of each type
        password += secrets.choice(string.ascii_uppercase)
        password += secrets.choice(string.ascii_lowercase)
        password += secrets.choice(string.digits)
        password += secrets.choice("!@#$%")
        
        # Shuffle
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        return "".join(password_list)

    async def _log_admin_action(
        self,
        action: str,
        target_id: int,
        details: dict,
    ):
        """Log admin action to events table."""
        event = Event(
            user_id=self.admin.id,
            type=f"admin_{action}",
            payload={
                "target_id": target_id,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.session.add(event)
