"""User word tracking model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

VALID_USER_WORD_STATUS = ("active", "mastered", "ignored")
VALID_USER_WORD_SOURCE = ("dictionary", "suggestion", "decline")


class UserWord(Base):
    """Tracks a user's learning state for a specific word."""

    __tablename__ = "user_words"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey("learning_profiles.id", ondelete="CASCADE"), nullable=False
    )
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    stage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    due_lesson_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="dictionary")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    learning_profile = relationship("LearningProfile", back_populates="user_words")
    word = relationship("Word")

    __table_args__ = (
        UniqueConstraint("learning_profile_id", "word_id", name="uq_user_words_profile_word"),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in VALID_USER_WORD_STATUS)})",
            name="ck_user_words_status",
        ),
        CheckConstraint(
            f"source IN ({', '.join(repr(s) for s in VALID_USER_WORD_SOURCE)})",
            name="ck_user_words_source",
        ),
        CheckConstraint("stage >= 0 AND stage <= 6", name="ck_user_words_stage"),
        # due_lesson_number can be NOT NULL only when status = 'active'
        CheckConstraint(
            "status = 'active' OR due_lesson_number IS NULL",
            name="ck_user_words_due_only_active",
        ),
        Index("ix_user_words_profile_status_due", "learning_profile_id", "status", "due_lesson_number"),
    )

    def __repr__(self) -> str:
        return f"<UserWord id={self.id} profile={self.learning_profile_id} word={self.word_id}>"
