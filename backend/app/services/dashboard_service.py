"""Dashboard service."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Set
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.models.user import User
from app.models.user_word import UserWord
from app.schemas.dashboard import (
    DashboardSummary,
    DictionaryInfo,
    ProfileInfo,
    ResumeInfo,
    StreakInfo,
    WordsSummary,
)
from app.services.streak_service import calculate_streak


class DashboardService:
    """Service for dashboard data."""

    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user

    async def get_summary(self) -> DashboardSummary:
        """
        Get dashboard summary for the user.
        
        Returns:
            DashboardSummary with all dashboard data
        """
        # Get user's timezone
        user_tz = ZoneInfo(self.user.timezone)
        
        # Get current date in user's timezone
        now_utc = datetime.now(ZoneInfo("UTC"))
        today = now_utc.astimezone(user_tz).date()
        
        # Calculate resets_at (next midnight in user's timezone)
        tomorrow = today + timedelta(days=1)
        resets_at_local = datetime.combine(tomorrow, time.min)
        resets_at = datetime(
            tomorrow.year, tomorrow.month, tomorrow.day,
            tzinfo=user_tz
        ).astimezone(ZoneInfo("UTC"))
        
        # Get profile info
        profile = await self._get_profile_info()
        
        # Get lessons today count
        lessons_today = await self._count_lessons_today(today)
        
        # Get daily lesson limit
        daily_limit = await self._get_daily_lesson_limit()
        
        # Get in-progress lesson
        in_progress_lesson = await self._get_in_progress_lesson()
        
        # Determine CTA
        cta, resume = self._determine_cta(
            in_progress_lesson, lessons_today, daily_limit
        )
        
        # Get words summary
        words = await self._get_words_summary()
        
        # Get streak
        streak = await self._get_streak(today)
        
        return DashboardSummary(
            profile=profile,
            today=today,
            lessons_today=lessons_today,
            daily_lesson_limit=daily_limit,
            resets_at=resets_at,
            cta=cta,
            resume=resume,
            words=words,
            streak=streak,
        )

    async def _get_profile_info(self) -> ProfileInfo:
        """Get profile information."""
        from app.models.learning_profile import LearningProfile
        from app.models.dictionary import Dictionary
        from app.exceptions import AppException
        
        result = await self.session.execute(
            select(LearningProfile, Dictionary)
            .join(Dictionary, LearningProfile.dictionary_id == Dictionary.id)
            .where(LearningProfile.user_id == self.user.id)
        )
        row = result.one_or_none()
        
        if not row:
            raise AppException(
                status_code=409,
                code="onboarding_required",
                message="Learning profile not found. Please complete onboarding first."
            )
        
        profile, dictionary = row
        
        return ProfileInfo(
            level=profile.level,
            dictionary=DictionaryInfo(
                id=dictionary.id,
                name=dictionary.name,
            ),
        )

    async def _count_lessons_today(self, today: date) -> int:
        """Count lessons started today."""
        from app.models.learning_profile import LearningProfile
        
        result = await self.session.execute(
            select(func.count(Lesson.id))
            .join(LearningProfile, Lesson.learning_profile_id == LearningProfile.id)
            .where(
                LearningProfile.user_id == self.user.id,
                Lesson.started_local_date == today,
            )
        )
        return result.scalar_one()

    async def _get_daily_lesson_limit(self) -> int:
        """Get daily lesson limit from profile."""
        from app.models.learning_profile import LearningProfile
        
        result = await self.session.execute(
            select(LearningProfile.daily_lesson_limit)
            .where(LearningProfile.user_id == self.user.id)
        )
        return result.scalar_one()

    async def _get_in_progress_lesson(self) -> tuple[Lesson, int, int] | None:
        """
        Get in-progress lesson with exercise counts.
        
        Returns:
            Tuple of (lesson, exercises_done, exercises_total) or None
        """
        from app.models.lesson_exercise import LessonExercise
        
        # Find in-progress lesson
        from app.models.learning_profile import LearningProfile
        
        result = await self.session.execute(
            select(Lesson)
            .join(LearningProfile, Lesson.learning_profile_id == LearningProfile.id)
            .where(
                LearningProfile.user_id == self.user.id,
                Lesson.status == "in_progress",
            )
        )
        lesson = result.scalar_one_or_none()
        
        if not lesson:
            return None
        
        # Count exercises
        total_result = await self.session.execute(
            select(func.count(LessonExercise.id))
            .where(LessonExercise.lesson_id == lesson.id)
        )
        total = total_result.scalar_one()
        
        done_result = await self.session.execute(
            select(func.count(LessonExercise.id))
            .where(
                LessonExercise.lesson_id == lesson.id,
                LessonExercise.status == "evaluated",
            )
        )
        done = done_result.scalar_one()
        
        return lesson, done, total

    def _determine_cta(
        self,
        in_progress_lesson: tuple[Lesson, int, int] | None,
        lessons_today: int,
        daily_limit: int,
    ) -> tuple[str, ResumeInfo | None]:
        """
        Determine CTA and resume info.
        
        Returns:
            Tuple of (cta, resume_info)
        """
        if in_progress_lesson:
            lesson, done, total = in_progress_lesson
            resume = ResumeInfo(
                lesson_id=lesson.id,
                exercises_done=done,
                exercises_total=total,
            )
            return "resume", resume
        
        if lessons_today >= daily_limit:
            return "limit_reached", None
        
        return "start", None

    async def _get_words_summary(self) -> WordsSummary:
        """Get words count by status."""
        from app.models.learning_profile import LearningProfile
        
        # Get profile ID
        profile_result = await self.session.execute(
            select(LearningProfile.id)
            .where(LearningProfile.user_id == self.user.id)
        )
        profile_id = profile_result.scalar_one()
        
        # Count by status
        result = await self.session.execute(
            select(UserWord.status, func.count(UserWord.id))
            .where(UserWord.learning_profile_id == profile_id)
            .group_by(UserWord.status)
        )
        
        counts = {status: count for status, count in result.all()}
        
        return WordsSummary(
            active=counts.get("active", 0),
            mastered=counts.get("mastered", 0),
            ignored=counts.get("ignored", 0),
        )

    async def _get_streak(self, today: date) -> StreakInfo:
        """Calculate streak from completed lessons."""
        from app.models.learning_profile import LearningProfile
        
        # Get profile ID
        profile_result = await self.session.execute(
            select(LearningProfile.id)
            .where(LearningProfile.user_id == self.user.id)
        )
        profile_id = profile_result.scalar_one()
        
        # Get all completed lesson dates
        result = await self.session.execute(
            select(Lesson.completed_local_date)
            .where(
                Lesson.learning_profile_id == profile_id,
                Lesson.status == "completed",
                Lesson.completed_local_date.isnot(None),
            )
        )
        
        completed_dates: Set[date] = {row[0] for row in result.all()}
        
        # Calculate streak
        current, longest, today_done = calculate_streak(completed_dates, today)
        
        return StreakInfo(
            current=current,
            longest=longest,
            today_done=today_done,
        )
