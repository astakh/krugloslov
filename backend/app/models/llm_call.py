"""LLM call log model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

VALID_LLM_PURPOSE = ("generate", "evaluate")
VALID_LLM_STATUS = ("ok", "http_error", "timeout", "invalid_json", "invalid_schema", "validation_failed")


class LLMCall(Base):
    """Log of every LLM API call."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )
    exercise_id: Mapped[int | None] = mapped_column(
        ForeignKey("lesson_exercises.id", ondelete="SET NULL"), nullable=True
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    request: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user = relationship("User")
    lesson = relationship("Lesson")
    exercise = relationship("LessonExercise")

    __table_args__ = (
        CheckConstraint(
            f"purpose IN ({', '.join(repr(p) for p in VALID_LLM_PURPOSE)})",
            name="ck_llm_calls_purpose",
        ),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in VALID_LLM_STATUS)})",
            name="ck_llm_calls_status",
        ),
        Index("ix_llm_calls_user_id", "user_id"),
        Index("ix_llm_calls_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<LLMCall id={self.id} purpose={self.purpose} status={self.status}>"
