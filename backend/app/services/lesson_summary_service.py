"""Service for lesson summary."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Set
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models.lesson import Lesson
from app.models.lesson_exercise import LessonExercise
from app.models.lesson_exercise_suggestion import LessonExerciseSuggestion
from app.models.lesson_exercise_word import LessonExerciseWord
from app.models.user import User
from app.schemas.lesson_resume import LessonSummaryResponse, StreakSummary
from app.services.streak_service import calculate_streak


class LessonSummaryService:
    """Service for generating lesson summary."""

    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user

    async def get_summary(self, lesson_id: int) -> LessonSummaryResponse:
        """
        Get lesson summary with statistics.
        
        Only available for completed lessons.
        """
        # Get lesson
        lesson = await self._get_lesson(lesson_id)
        
        # Check lesson belongs to user
        if lesson.learning_profile.user_id != self.user.id:
            raise AppException(
                status_code=403,
                code="forbidden",
                message="Урок не принадлежит пользователю"
            )
        
        # Check lesson is completed
        if lesson.status != "completed":
            raise AppException(
                status_code=409,
                code="lesson_not_completed",
                message="Итоги доступны только для завершённых уроков"
            )
        
        # Calculate statistics
        words_total = await self._count_total_words(lesson_id)
        new_words = await self._count_new_words(lesson_id)
        reviewed = words_total - new_words
        
        correct = await self._count_words_by_result(lesson_id, "correct")
        typo = await self._count_words_by_result(lesson_id, "typo")
        incorrect = await self._count_words_by_result(lesson_id, "incorrect")
        without_errors = correct + typo
        
        suggestions_added = await self._count_added_suggestions(lesson_id)
        
        # Calculate streak
        streak = await self._calculate_streak(lesson)
        
        return LessonSummaryResponse(
            lesson_number=lesson.lesson_number,
            words_total=words_total,
            reviewed=reviewed,
            new_words=new_words,
            correct=correct,
            typo=typo,
            incorrect=incorrect,
            without_errors=without_errors,
            suggestions_added=suggestions_added,
            streak=streak
        )

    async def _get_lesson(self, lesson_id: int) -> Lesson:
        """Get lesson by ID with eager loading."""
        from sqlalchemy.orm import selectinload
        
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.id == lesson_id)
            .options(selectinload(Lesson.learning_profile))
        )
        lesson = result.scalar_one_or_none()
        
        if not lesson:
            raise AppException(
                status_code=404,
                code="lesson_not_found",
                message="Урок не найден"
            )
        
        return lesson

    async def _count_total_words(self, lesson_id: int) -> int:
        """Count all target words in lesson."""
        result = await self.session.execute(
            select(func.count(LessonExerciseWord.id))
            .join(LessonExercise)
            .where(
                LessonExercise.lesson_id == lesson_id,
                LessonExerciseWord.is_target == True
            )
        )
        return result.scalar() or 0

    async def _count_new_words(self, lesson_id: int) -> int:
        """Count new words (is_new=True) in lesson."""
        result = await self.session.execute(
            select(func.count(LessonExerciseWord.id))
            .join(LessonExercise)
            .where(
                LessonExercise.lesson_id == lesson_id,
                LessonExerciseWord.is_target == True,
                LessonExerciseWord.is_new == True
            )
        )
        return result.scalar() or 0

    async def _count_words_by_result(self, lesson_id: int, result_value: str) -> int:
        """Count words with specific result."""
        result = await self.session.execute(
            select(func.count(LessonExerciseWord.id))
            .join(LessonExercise)
            .where(
                LessonExercise.lesson_id == lesson_id,
                LessonExerciseWord.is_target == True,
                LessonExerciseWord.result == result_value
            )
        )
        return result.scalar() or 0

    async def _count_added_suggestions(self, lesson_id: int) -> int:
        """Count suggestions with state='added'."""
        result = await self.session.execute(
            select(func.count(LessonExerciseSuggestion.id))
            .join(LessonExercise)
            .where(
                LessonExercise.lesson_id == lesson_id,
                LessonExerciseSuggestion.state == "added"
            )
        )
        return result.scalar() or 0

    async def _calculate_streak(self, lesson: Lesson) -> StreakSummary:
        """Calculate streak including this lesson."""
        from app.models.learning_profile import LearningProfile
        
        # Get user's timezone
        user_tz = ZoneInfo(self.user.timezone)
        now_utc = datetime.now(timezone.utc)
        today = now_utc.astimezone(user_tz).date()
        
        # Get all completed lesson dates for this user
        result = await self.session.execute(
            select(Lesson.completed_local_date)
            .join(LearningProfile, Lesson.learning_profile_id == LearningProfile.id)
            .where(
                LearningProfile.user_id == self.user.id,
                Lesson.status == "completed",
                Lesson.completed_local_date.isnot(None)
            )
        )
        
        completed_dates: Set[date] = {row[0] for row in result.all()}
        
        # Calculate streak
        current, longest, today_done = calculate_streak(completed_dates, today)
        
        # Check if this lesson extended the streak today
        # This is true if:
        # 1. today_done is True (we completed a lesson today)
        # 2. This lesson's completed_local_date is today
        # 3. Before this lesson, there was no completed lesson today
        extended_today = False
        if lesson.completed_local_date == today:
            # Check if there were other lessons completed today before this one
            result = await self.session.execute(
                select(func.count(Lesson.id))
                .join(LearningProfile, Lesson.learning_profile_id == LearningProfile.id)
                .where(
                    LearningProfile.user_id == self.user.id,
                    Lesson.status == "completed",
                    Lesson.completed_local_date == today,
                    Lesson.id != lesson.id
                )
            )
            other_lessons_today = result.scalar() or 0
            
            # If this is the first lesson today, it extended the streak
            if other_lessons_today == 0:
                extended_today = True
        
        return StreakSummary(
            current=current,
            longest=longest,
            today_done=today_done,
            extended_today=extended_today
        )
