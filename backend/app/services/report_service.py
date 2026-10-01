"""Service for handling exercise reports."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models.event import Event
from app.models.lesson_exercise import LessonExercise
from app.models.sentence_report import SentenceReport
from app.schemas.lesson_evaluate import ReportResponse

logger = logging.getLogger(__name__)


class ReportService:
    """Service for handling exercise reports."""
    
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
    
    async def report_exercise(
        self,
        exercise_id: int,
        reason: str,
        comment: str
    ) -> ReportResponse:
        """
        Report an exercise with a reason and comment.
        
        Args:
            exercise_id: Exercise ID
            reason: Report reason
            comment: User comment
        
        Returns:
            ReportResponse
        """
        # Get exercise
        exercise = await self._get_exercise(exercise_id)
        
        # Check exercise belongs to user
        if exercise.lesson.learning_profile.user_id != self.user_id:
            raise AppException(
                status_code=403,
                code="forbidden",
                message="Упражнение не принадлежит пользователю"
            )
        
        # Check if report already exists
        result = await self.session.execute(
            select(SentenceReport)
            .where(
                SentenceReport.user_id == self.user_id,
                SentenceReport.exercise_id == exercise_id
            )
        )
        existing_report = result.scalar_one_or_none()
        
        if existing_report:
            # Update existing report
            existing_report.reason = reason
            existing_report.comment = comment
            existing_report.status = "new"
            report_id = existing_report.id
            message = "Жалоба обновлена"
        else:
            # Create new report
            report = SentenceReport(
                user_id=self.user_id,
                exercise_id=exercise_id,
                reason=reason,
                comment=comment,
                status="new",
                admin_note=""
            )
            self.session.add(report)
            await self.session.flush()
            report_id = report.id
            message = "Жалоба отправлена"
        
        # Create event
        event = Event(
            user_id=self.user_id,
            type="report_sent",
            payload={
                "exercise_id": exercise_id,
                "reason": reason,
                "report_id": report_id
            }
        )
        self.session.add(event)
        
        await self.session.commit()
        
        return ReportResponse(
            message=message,
            report_id=report_id
        )
    
    async def _get_exercise(self, exercise_id: int) -> LessonExercise:
        """Get exercise by ID with eager loading."""
        from sqlalchemy.orm import selectinload
        from app.models.lesson import Lesson
        
        result = await self.session.execute(
            select(LessonExercise)
            .where(LessonExercise.id == exercise_id)
            .options(
                selectinload(LessonExercise.lesson)
                .selectinload(Lesson.learning_profile)
            )
        )
        exercise = result.scalar_one_or_none()
        
        if not exercise:
            raise AppException(
                status_code=404,
                code="exercise_not_found",
                message="Упражнение не найдено"
            )
        
        return exercise
