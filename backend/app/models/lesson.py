"""Lesson model."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

VALID_LESSON_STATUS = ("in_progress", "completed", "abandoned")


class Lesson(Base):
    """A learning lesson for a user."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey("learning_profiles.id", ondelete="CASCADE"), nullable=False
    )
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    words_per_lesson: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_local_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_local_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    abandoned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    learning_profile = relationship("LearningProfile", back_populates="lessons")
    exercises = relationship("LessonExercise", back_populates="lesson", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("learning_profile_id", "lesson_number", name="uq_lessons_profile_number"),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in VALID_LESSON_STATUS)})",
            name="ck_lessons_status",
        ),
        # Only one in_progress lesson per profile
        Index(
            "ix_lessons_profile_in_progress_unique",
            "learning_profile_id",
            unique=True,
            postgresql_where=(status == "in_progress"),  # noqa: E712
        ),
        Index("ix_lessons_profile_started_local_date", "learning_profile_id", "started_local_date"),
        Index("ix_lessons_completed_local_date", "completed_local_date"),
    )

    def __repr__(self) -> str:
        return f"<Lesson id={self.id} profile={self.learning_profile_id} number={self.lesson_number}>"
