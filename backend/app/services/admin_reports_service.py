"""Service for admin reports management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models import (
    LessonExercise,
    LessonExerciseWord,
    LLMCall,
    SentenceReport,
    User,
    Word,
)
from app.schemas.admin_management import (
    AdminReportItem,
    AdminReportsListResponse,
    TargetWordInfo,
)


class AdminReportsService:
    """Service for managing reports in admin panel."""

    def __init__(self, session: AsyncSession, admin: User):
        self.session = session
        self.admin = admin

    async def get_reports(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminReportsListResponse:
        """Get paginated list of reports."""
        # Build base query
        query = select(SentenceReport).order_by(SentenceReport.created_at.desc())

        if status:
            query = query.where(SentenceReport.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        reports = result.scalars().all()

        # Build response items
        items = []
        for report in reports:
            item = await self._build_report_item(report)
            items.append(item)

        return AdminReportsListResponse(
            reports=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def process_report(
        self,
        report_id: int,
        status: str,
        admin_note: Optional[str] = None,
    ) -> str:
        """Process a report (mark as processed)."""
        # Validate status transition
        if status not in ["processed"]:
            raise AppException(
                status_code=422,
                code="invalid_status",
                message="Status must be 'processed'",
            )

        # Get report with FOR UPDATE
        result = await self.session.execute(
            select(SentenceReport)
            .where(SentenceReport.id == report_id)
            .with_for_update()
        )
        report = result.scalar_one_or_none()

        if not report:
            raise AppException(
                status_code=404,
                code="report_not_found",
                message="Report not found",
            )

        # Idempotent: if already processed with same note, just return
        if report.status == "processed" and report.admin_note == admin_note:
            return "Report already processed"

        # Update report
        report.status = status
        if admin_note is not None:
            report.admin_note = admin_note

        await self.session.commit()

        # Log admin action
        await self._log_admin_action(
            action="process_report",
            target_id=report_id,
            details={"status": status, "admin_note": admin_note},
        )

        return "Report processed successfully"

    async def _build_report_item(self, report: SentenceReport) -> AdminReportItem:
        """Build report item with all related data."""
        # Get exercise
        result = await self.session.execute(
            select(LessonExercise).where(LessonExercise.id == report.exercise_id)
        )
        exercise = result.scalar_one_or_none()

        if not exercise:
            raise AppException(
                status_code=404,
                code="exercise_not_found",
                message="Exercise not found",
            )

        # Get user
        result = await self.session.execute(
            select(User).where(User.id == report.user_id)
        )
        user = result.scalar_one_or_none()

        # Get target words
        result = await self.session.execute(
            select(LessonExerciseWord, Word)
            .join(Word, LessonExerciseWord.word_id == Word.id)
            .where(
                LessonExerciseWord.exercise_id == report.exercise_id,
                LessonExerciseWord.is_target == True,
            )
        )
        target_words = [
            TargetWordInfo(
                word_id=ew.word_id,
                lemma=word.lemma,
                pos=word.pos,
                surface_form=ew.surface_form,
            )
            for ew, word in result.all()
        ]

        # Get related LLM calls
        result = await self.session.execute(
            select(LLMCall.id)
            .where(LLMCall.exercise_id == report.exercise_id)
            .order_by(LLMCall.created_at.desc())
        )
        llm_call_ids = [row[0] for row in result.all()]

        return AdminReportItem(
            id=report.id,
            user_id=report.user_id,
            user_email=user.email if user else "unknown",
            exercise_id=report.exercise_id,
            target_sentence=exercise.target_sentence,
            reference_translation=exercise.reference_translation,
            user_translation=exercise.user_translation,
            target_words=target_words,
            reason=report.reason,
            comment=report.comment,
            status=report.status,
            admin_note=report.admin_note,
            created_at=report.created_at,
            llm_call_ids=llm_call_ids,
        )

    async def _log_admin_action(
        self,
        action: str,
        target_id: int,
        details: dict,
    ):
        """Log admin action to events table."""
        from app.models import Event

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
        await self.session.commit()
