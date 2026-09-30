"""Sentence report model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

VALID_REPORT_STATUS = ("new", "processed")


class SentenceReport(Base):
    """User report about a problematic sentence."""

    __tablename__ = "sentence_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_exercises.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new")
    admin_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user = relationship("User")
    exercise = relationship("LessonExercise")

    __table_args__ = (
        UniqueConstraint("user_id", "exercise_id", name="uq_reports_user_exercise"),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in VALID_REPORT_STATUS)})",
            name="ck_reports_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<SentenceReport id={self.id} user={self.user_id} exercise={self.exercise_id}>"
