"""Service for lesson resume and abandon operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models.lesson import Lesson
from app.models.lesson_exercise import LessonExercise
from app.schemas.lesson_resume import CurrentExerciseResponse
from app.services.events import record_event


class LessonResumeService:
    """Service for resuming and abandoning lessons."""

    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id

    async def get_current_exercise(self, lesson_id: int) -> CurrentExerciseResponse:
        """
        Get current pending exercise for a lesson.
        
        Returns the first pending exercise or raises error if lesson is completed.
        """
        # Get lesson
        lesson = await self._get_lesson(lesson_id)
        
        # Check lesson belongs to user
        if lesson.learning_profile.user_id != self.user_id:
            raise AppException(
                status_code=403,
                code="forbidden",
                message="Урок не принадлежит пользователю"
            )
        
        # Check lesson status
        if lesson.status == "completed":
            raise AppException(
                status_code=409,
                code="lesson_not_active",
                message="Урок завершён"
            )
        
        if lesson.status == "abandoned":
            raise AppException(
                status_code=409,
                code="lesson_not_active",
                message="Урок отменён"
            )
        
        # Get exercises count
        exercises_total = await self._count_exercises(lesson_id)
        exercises_done = await self._count_evaluated_exercises(lesson_id)
        
        # Get first pending exercise
        exercise = await self._get_first_pending_exercise(lesson_id)
        
        if not exercise:
            # All exercises done, lesson should be completed
            raise AppException(
                status_code=409,
                code="lesson_not_active",
                message="Все упражнения выполнены"
            )
        
        return CurrentExerciseResponse(
            exercise_id=exercise.id,
            sentence=exercise.target_sentence,
            order_index=exercise.order_index,
            exercises_done=exercises_done,
            exercises_total=exercises_total
        )

    async def abandon_lesson(self, lesson_id: int) -> str:
        """
        Abandon a lesson.
        
        Marks lesson as abandoned and records event.
        Does not return daily limit.
        Does not revert SRS changes for processed words.
        """
        from sqlalchemy.orm import selectinload
        
        # Get lesson with FOR UPDATE and eager loading
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.id == lesson_id)
            .options(selectinload(Lesson.learning_profile))
            .with_for_update()
        )
        lesson = result.scalar_one_or_none()
        
        if not lesson:
            raise AppException(
                status_code=404,
                code="lesson_not_found",
                message="Урок не найден"
            )
        
        # Check lesson belongs to user
        if lesson.learning_profile.user_id != self.user_id:
            raise AppException(
                status_code=403,
                code="forbidden",
                message="Урок не принадлежит пользователю"
            )
        
        # Idempotent: if already abandoned, return success
        if lesson.status == "abandoned":
            return "Урок уже отменён"
        
        # Check if completed
        if lesson.status == "completed":
            raise AppException(
                status_code=409,
                code="lesson_not_active",
                message="Нельзя отменить завершённый урок"
            )
        
        # Update lesson status
        lesson.status = "abandoned"
        lesson.abandoned_at = datetime.now(timezone.utc)
        
        # Record event
        await record_event(
            self.session,
            self.user_id,
            "lesson_abandoned",
            {"lesson_id": lesson_id}
        )
        
        await self.session.commit()
        
        return "Урок отменён"

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

    async def _count_exercises(self, lesson_id: int) -> int:
        """Count total exercises in lesson."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(LessonExercise.id))
            .where(LessonExercise.lesson_id == lesson_id)
        )
        return result.scalar() or 0

    async def _count_evaluated_exercises(self, lesson_id: int) -> int:
        """Count evaluated exercises in lesson."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(LessonExercise.id))
            .where(
                LessonExercise.lesson_id == lesson_id,
                LessonExercise.status == "evaluated"
            )
        )
        return result.scalar() or 0

    async def _get_first_pending_exercise(self, lesson_id: int) -> Optional[LessonExercise]:
        """Get first pending exercise ordered by order_index."""
        result = await self.session.execute(
            select(LessonExercise)
            .where(
                LessonExercise.lesson_id == lesson_id,
                LessonExercise.status == "pending"
            )
            .order_by(LessonExercise.order_index)
            .limit(1)
        )
        return result.scalar_one_or_none()
