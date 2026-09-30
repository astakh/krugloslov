"""Lesson exercise suggestion model."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

VALID_SUGGESTION_STATE = ("suggested", "added", "ignored")


class LessonExerciseSuggestion(Base):
    """LLM-suggested new words for an exercise."""

    __tablename__ = "lesson_exercise_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_exercises.id", ondelete="CASCADE"), nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="suggested")

    # Relationships
    exercise = relationship("LessonExercise", back_populates="suggestions")
    word = relationship("Word")

    __table_args__ = (
        UniqueConstraint("exercise_id", "word_id", name="uq_suggestions_exercise_word"),
        CheckConstraint(
            f"state IN ({', '.join(repr(s) for s in VALID_SUGGESTION_STATE)})",
            name="ck_suggestions_state",
        ),
    )

    def __repr__(self) -> str:
        return f"<LessonExerciseSuggestion id={self.id} exercise={self.exercise_id}>"
