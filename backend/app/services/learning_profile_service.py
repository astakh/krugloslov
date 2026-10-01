"""Service for learning profile settings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AppException
from app.models import Dictionary, Lesson, LearningProfile, User, UserWord
from app.schemas.profile import LearningProfileResponse, LearningStats, WordsByStatus


class LearningProfileService:
    """Service for managing learning profile settings."""

    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user

    async def get_profile(self) -> LearningProfileResponse:
        """Get learning profile with statistics."""
        profile = await self._get_learning_profile()
        
        # Get dictionary info
        result = await self.session.execute(
            select(Dictionary).where(Dictionary.id == profile.dictionary_id)
        )
        dictionary = result.scalar_one()
        
        # Calculate statistics
        stats = await self._calculate_stats(profile.id)
        
        return LearningProfileResponse(
            level=profile.level,
            dictionary_id=profile.dictionary_id,
            dictionary_name=dictionary.name,
            daily_lesson_limit=profile.daily_lesson_limit,
            daily_lesson_limit_max=settings.DAILY_LESSON_LIMIT_MAX,
            words_per_lesson=profile.words_per_lesson,
            words_per_lesson_max=settings.WORDS_PER_LESSON_MAX,
            stats=stats,
        )

    async def update_profile(
        self,
        level: Optional[str] = None,
        dictionary_id: Optional[int] = None,
        daily_lesson_limit: Optional[int] = None,
        words_per_lesson: Optional[int] = None,
    ) -> dict:
        """
        Update learning profile settings.
        
        Args:
            level: New level (A1-B2)
            dictionary_id: New dictionary ID
            daily_lesson_limit: New daily lesson limit
            words_per_lesson: New words per lesson count
            
        Returns:
            Updated profile information
        """
        profile = await self._get_learning_profile()
        
        # Validate and update level
        if level is not None:
            if level not in ["A1", "A2", "B1", "B2"]:
                raise AppException(
                    status_code=422,
                    code="invalid_level",
                    message="Level must be A1, A2, B1, or B2",
                )
            profile.level = level
        
        # Validate and update dictionary
        if dictionary_id is not None:
            result = await self.session.execute(
                select(Dictionary).where(Dictionary.id == dictionary_id)
            )
            dictionary = result.scalar_one_or_none()
            if not dictionary:
                raise AppException(
                    status_code=404,
                    code="dictionary_not_found",
                    message="Dictionary not found",
                )
            profile.dictionary_id = dictionary_id
        
        # Validate and update daily lesson limit
        if daily_lesson_limit is not None:
            if daily_lesson_limit < 1 or daily_lesson_limit > settings.DAILY_LESSON_LIMIT_MAX:
                raise AppException(
                    status_code=422,
                    code="invalid_daily_limit",
                    message=f"Daily lesson limit must be between 1 and {settings.DAILY_LESSON_LIMIT_MAX}",
                )
            profile.daily_lesson_limit = daily_lesson_limit
        
        # Validate and update words per lesson
        if words_per_lesson is not None:
            if words_per_lesson < 1 or words_per_lesson > settings.WORDS_PER_LESSON_MAX:
                raise AppException(
                    status_code=422,
                    code="invalid_words_per_lesson",
                    message=f"Words per lesson must be between 1 and {settings.WORDS_PER_LESSON_MAX}",
                )
            profile.words_per_lesson = words_per_lesson
        
        await self.session.commit()
        
        return {
            "message": "Learning profile updated successfully",
            "level": profile.level,
            "dictionary_id": profile.dictionary_id,
            "daily_lesson_limit": profile.daily_lesson_limit,
            "words_per_lesson": profile.words_per_lesson,
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

    async def _calculate_stats(self, profile_id: int) -> LearningStats:
        """Calculate learning statistics."""
        # Count words by status
        words_active = await self._count_words_by_status(profile_id, "active")
        words_mastered = await self._count_words_by_status(profile_id, "mastered")
        words_ignored = await self._count_words_by_status(profile_id, "ignored")
        
        # Calculate accuracy
        accuracy_30_days = await self._calculate_accuracy(profile_id, days=30)
        accuracy_all_time = await self._calculate_accuracy(profile_id, days=None)
        
        # Count completed lessons
        lessons_completed = await self._count_completed_lessons(profile_id)
        
        return LearningStats(
            words=WordsByStatus(
                active=words_active,
                mastered=words_mastered,
                ignored=words_ignored,
            ),
            accuracy_30_days=accuracy_30_days,
            accuracy_all_time=accuracy_all_time,
            lessons_completed=lessons_completed,
        )

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

    async def _calculate_accuracy(self, profile_id: int, days: Optional[int]) -> Optional[float]:
        """Calculate accuracy for given period."""
        from sqlalchemy import case
        from app.models import LessonExerciseWord, Lesson
        
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
        
        # Join with lessons to filter by date and profile
        query = query.join(Lesson, LessonExerciseWord.exercise_id == Lesson.id)
        query = query.where(Lesson.learning_profile_id == profile_id)
        
        if days:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.where(Lesson.completed_at >= cutoff_date)
        
        result = await self.session.execute(query)
        row = result.first()
        
        if not row or row.total == 0:
            return None
        
        return round(float(row.correct) / float(row.total) * 100, 2)

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
