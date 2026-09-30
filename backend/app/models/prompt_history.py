"""Prompt history model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PromptHistory(Base):
    """Historical versions of prompt templates."""

    __tablename__ = "prompt_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(128), ForeignKey("prompts.key", ondelete="CASCADE"), nullable=False
    )
    system_template: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    prompt = relationship("Prompt", back_populates="history")
    created_by_user = relationship("User")

    __table_args__ = (
        Index("ix_prompt_history_key_created_at", "key", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PromptHistory id={self.id} key={self.key}>"
