"""Prompt template model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Prompt(Base):
    """Current version of an LLM prompt template."""

    __tablename__ = "prompts"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    system_template: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    updated_by_user = relationship("User")
    history = relationship("PromptHistory", back_populates="prompt", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Prompt key={self.key}>"
