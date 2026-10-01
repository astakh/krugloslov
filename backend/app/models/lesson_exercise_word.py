"""Lesson exercise word model."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

VALID_EXERCISE_WORD_RESULT = ("correct", "typo", "incorrect")


class LessonExerciseWord(Base):
    """Word-level tracking within an exercise.

    When is_target=true, this is a target word the user must translate.
    When is_target=false, this is a hint/scaffold word (result and surface_form are NULL).
    """

    __tablename__ = "lesson_exercise_words"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_exercises.id", ondelete="CASCADE"), nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="RESTRICT"), nullable=False
    )
    is_target: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    surface_form: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    result: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    user_fragment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stage_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stage_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    exercise = relationship("LessonExercise", back_populates="exercise_words")
    word = relationship("Word")

    __table_args__ = (
        CheckConstraint(
            f"result IS NULL OR result IN ({', '.join(repr(r) for r in VALID_EXERCISE_WORD_RESULT)})",
            name="ck_exercise_words_result",
        ),
        CheckConstraint("stage_before IS NULL OR (stage_before >= 0 AND stage_before <= 6)", name="ck_exercise_words_stage_before"),
        CheckConstraint("stage_after IS NULL OR (stage_after >= 0 AND stage_after <= 6)", name="ck_exercise_words_stage_after"),
        Index("ix_exercise_words_exercise_id", "exercise_id"),
        Index("ix_exercise_words_word_id", "word_id"),
    )

    def __repr__(self) -> str:
        return f"<LessonExerciseWord id={self.id} exercise={self.exercise_id} word={self.word_id}>"
