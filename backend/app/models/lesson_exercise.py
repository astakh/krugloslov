"""Lesson exercise model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

VALID_EXERCISE_STATUS = ("pending", "evaluated")


class LessonExercise(Base):
    """A single translation exercise within a lesson."""

    __tablename__ = "lesson_exercises"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    target_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    reference_translation: Mapped[str] = mapped_column(Text, nullable=False)
    user_translation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dont_know: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    lesson = relationship("Lesson", back_populates="exercises")
    exercise_words = relationship("LessonExerciseWord", back_populates="exercise", lazy="selectin")
    suggestions = relationship("LessonExerciseSuggestion", back_populates="exercise", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in VALID_EXERCISE_STATUS)})",
            name="ck_exercises_status",
        ),
        Index("ix_exercises_lesson_id", "lesson_id"),
    )

    def __repr__(self) -> str:
        return f"<LessonExercise id={self.id} lesson={self.lesson_id} order={self.order_index}>"
