"""Service for profile statistics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lesson, LessonExerciseWord, LearningProfile, User, UserWord
from app.schemas.profile import HeatmapDay, ProfileStatsResponse
from app.services.streak_service import calculate_streak


class ProfileStatsService:
    """Service for calculating profile statistics."""

    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user

    async def get_stats(self) -> ProfileStatsResponse:
        """Calculate and return profile statistics."""
        # Get learning profile
        profile = await self._get_learning_profile()
        
        # Get user's timezone
        user_tz = ZoneInfo(self.user.timezone)
        now_utc = datetime.now(timezone.utc)
        today = now_utc.astimezone(user_tz).date()
        
        # Calculate streak
        current_streak, longest_streak = await self._calculate_streak(user_tz, today)
        
        # Calculate accuracy
        accuracy_30_days = await self._calculate_accuracy(days=30)
        accuracy_all_time = await self._calculate_accuracy(days=None)
        
        # Count words by status
        words_active = await self._count_words_by_status(profile.id, "active")
        words_mastered = await self._count_words_by_status(profile.id, "mastered")
        words_ignored = await self._count_words_by_status(profile.id, "ignored")
        
        # Count completed lessons
        lessons_completed = await self._count_completed_lessons(profile.id)
        
        # Generate heatmap
        heatmap = await self._generate_heatmap(user_tz, today)
        
        return ProfileStatsResponse(
            current_streak=current_streak,
            longest_streak=longest_streak,
            accuracy_30_days=accuracy_30_days,
            accuracy_all_time=accuracy_all_time,
            words_active=words_active,
            words_mastered=words_mastered,
            words_ignored=words_ignored,
            lessons_completed=lessons_completed,
            heatmap=heatmap,
        )

    async def _get_learning_profile(self) -> LearningProfile:
        """Get user's learning profile."""
        result = await self.session.execute(
            select(LearningProfile).where(LearningProfile.user_id == self.user.id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise ValueError("Learning profile not found")
        return profile

    async def _calculate_streak(self, user_tz: ZoneInfo, today) -> tuple[int, int]:
        """Calculate current and longest streak."""
        profile = await self._get_learning_profile()
        
        # Get all completed lesson dates
        result = await self.session.execute(
            select(Lesson.completed_local_date)
            .where(
                Lesson.learning_profile_id == profile.id,
                Lesson.status == "completed",
                Lesson.completed_local_date.isnot(None),
            )
        )
        
        completed_dates: Set = {row[0] for row in result.all()}
        
        # Use streak service
        current, longest, _ = calculate_streak(completed_dates, today)
        
        return current, longest

    async def _calculate_accuracy(self, days: Optional[int]) -> Optional[float]:
        """Calculate accuracy for given period."""
        from sqlalchemy import case
        
        profile = await self._get_learning_profile()
        
        # Build query with case statement for counting correct answers
        query = select(
            func.count(LessonExerciseWord.id).label("total"),
            func.sum(
                case(
                    (LessonExerciseWord.result.in_(["correct", "typo"]), 1),
                    else_=0
                )
            ).label("correct"),
        ).where(
            LessonExerciseWord.is_target == True,
            LessonExerciseWord.result.isnot(None),
        )
        
        # Join with lessons to filter by date
        query = query.join(Lesson, LessonExerciseWord.exercise_id == Lesson.id)
        
        if days:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.where(Lesson.completed_at >= cutoff_date)
        else:
            query = query.where(Lesson.learning_profile_id == profile.id)
        
        result = await self.session.execute(query)
        row = result.first()
        
        if not row or row.total == 0:
            return None
        
        return round(float(row.correct) / float(row.total) * 100, 2)

    async def _count_words_by_status(self, profile_id: int, status: str) -> int:
        """Count words by status."""
        result = await self.session.execute(
            select(func.count(UserWord.id))
            .where(
                UserWord.learning_profile_id == profile_id,
                UserWord.status == status,
            )
        )
        return result.scalar() or 0

    async def _count_completed_lessons(self, profile_id: int) -> int:
        """Count completed lessons."""
        result = await self.session.execute(
            select(func.count(Lesson.id))
            .where(
                Lesson.learning_profile_id == profile_id,
                Lesson.status == "completed",
            )
        )
        return result.scalar() or 0

    async def _generate_heatmap(self, user_tz: ZoneInfo, today) -> List[HeatmapDay]:
        """Generate activity heatmap for last 12 months."""
        profile = await self._get_learning_profile()
        
        # Calculate date range (12 months back)
        start_date = today - timedelta(days=365)
        
        # Get completed lessons grouped by date
        result = await self.session.execute(
            select(
                Lesson.completed_local_date,
                func.count(Lesson.id).label("count"),
            )
            .where(
                Lesson.learning_profile_id == profile.id,
                Lesson.status == "completed",
                Lesson.completed_local_date >= start_date,
                Lesson.completed_local_date.isnot(None),
            )
            .group_by(Lesson.completed_local_date)
        )
        
        # Build heatmap data
        date_counts = {row.completed_local_date: row.count for row in result.all()}
        
        # Generate all dates in range
        heatmap = []
        current_date = start_date
        while current_date <= today:
            count = date_counts.get(current_date, 0)
            heatmap.append(HeatmapDay(date=current_date, count=count))
            current_date += timedelta(days=1)
        
        return heatmap
