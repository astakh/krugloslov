"""Service for timezone settings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models import Lesson, LearningProfile, User
from app.schemas.profile import ProfileStatsResponse


class TimezoneService:
    """Service for managing user timezone."""

    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user

    async def change_timezone(self, new_timezone: str) -> dict:
        """
        Change user's timezone.
        
        Args:
            new_timezone: IANA timezone string
            
        Returns:
            Updated profile information
            
        Raises:
            AppException: If timezone is invalid or change is too soon
        """
        # Validate timezone
        try:
            tz = ZoneInfo(new_timezone)
        except ZoneInfoNotFoundError:
            raise AppException(
                status_code=422,
                code="invalid_timezone",
                message=f"Invalid timezone: {new_timezone}",
            )
        
        # Check if timezone is the same
        if self.user.timezone == new_timezone:
            return await self._get_updated_info()
        
        # Check if change is allowed (7 days since last change)
        if self.user.timezone_changed_at:
            days_since_change = (datetime.now(timezone.utc) - self.user.timezone_changed_at).days
            if days_since_change < 7:
                available_at = self.user.timezone_changed_at + timedelta(days=7)
                raise AppException(
                    status_code=409,
                    code="timezone_change_too_soon",
                    message="Timezone can only be changed once per 7 days",
                    details={"available_at": available_at.isoformat()},
                )
        
        # Update timezone
        self.user.timezone = new_timezone
        self.user.timezone_changed_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        
        return await self._get_updated_info()

    async def _get_updated_info(self) -> dict:
        """Get updated profile information after timezone change."""
        user_tz = ZoneInfo(self.user.timezone)
        now_utc = datetime.now(timezone.utc)
        today = now_utc.astimezone(user_tz).date()
        
        # Calculate lessons today
        profile = await self._get_learning_profile()
        lessons_today = await self._count_lessons_today(profile.id, today)
        
        # Calculate resets_at (next midnight in user's timezone)
        tomorrow = today + timedelta(days=1)
        resets_at = datetime.combine(tomorrow, datetime.min.time(), tzinfo=user_tz)
        resets_at_utc = resets_at.astimezone(timezone.utc)
        
        # Calculate streak
        from app.services.streak_service import calculate_streak
        
        result = await self.session.execute(
            select(Lesson.completed_local_date)
            .where(
                Lesson.learning_profile_id == profile.id,
                Lesson.status == "completed",
                Lesson.completed_local_date.isnot(None),
            )
        )
        completed_dates = {row[0] for row in result.all()}
        current_streak, longest_streak, _ = calculate_streak(completed_dates, today)
        
        return {
            "today": today.isoformat(),
            "lessons_today": lessons_today,
            "resets_at": resets_at_utc.isoformat(),
            "current_streak": current_streak,
            "longest_streak": longest_streak,
        }

    async def _get_learning_profile(self) -> LearningProfile:
        """Get user's learning profile."""
        result = await self.session.execute(
            select(LearningProfile).where(LearningProfile.user_id == self.user.id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise ValueError("Learning profile not found")
        return profile

    async def _count_lessons_today(self, profile_id: int, today) -> int:
        """Count lessons started today."""
        from sqlalchemy import func
        
        result = await self.session.execute(
            select(func.count(Lesson.id))
            .where(
                Lesson.learning_profile_id == profile_id,
                Lesson.started_local_date == today,
            )
        )
        return result.scalar() or 0
