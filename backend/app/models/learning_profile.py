"""Learning profile model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.word import VALID_LEVELS


class LearningProfile(Base):
    """User learning profile (1:1 with User)."""

    __tablename__ = "learning_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    level: Mapped[str] = mapped_column(String(2), nullable=False, default="A1")
    dictionary_id: Mapped[int] = mapped_column(
        ForeignKey("dictionaries.id", ondelete="RESTRICT"), nullable=False
    )
    daily_lesson_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    words_per_lesson: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    last_lesson_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="learning_profile")
    dictionary = relationship("Dictionary")
    user_words = relationship("UserWord", back_populates="learning_profile", lazy="selectin")
    lessons = relationship("Lesson", back_populates="learning_profile", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            f"level IN ({', '.join(repr(l) for l in VALID_LEVELS)})",
            name="ck_learning_profiles_level",
        ),
        CheckConstraint("daily_lesson_limit >= 1", name="ck_learning_profiles_daily_limit"),
        CheckConstraint("words_per_lesson >= 1", name="ck_learning_profiles_words_per_lesson"),
    )

    def __repr__(self) -> str:
        return f"<LearningProfile id={self.id} user_id={self.user_id}>"
