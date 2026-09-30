"""Dictionary model."""

from __future__ import annotations

from typing import List

from sqlalchemy import Boolean, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Dictionary(Base):
    """Word dictionary (e.g., general, thematic)."""

    __tablename__ = "dictionaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_general: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    words = relationship("DictionaryWord", back_populates="dictionary", lazy="selectin")

    __table_args__ = (
        # Partial unique index: only one dictionary can have is_general = true
        Index(
            "ix_dictionaries_is_general_unique",
            "is_general",
            unique=True,
            postgresql_where=(is_general == True),  # noqa: E712
        ),
    )

    def __repr__(self) -> str:
        return f"<Dictionary id={self.id} code={self.code}>"
