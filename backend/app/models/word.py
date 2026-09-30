"""Word model."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Allowed part-of-speech values
VALID_POS = ("noun", "verb", "adj", "adv", "pron", "prep", "conj", "num", "det", "intj")

# Allowed CEFR levels
VALID_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


class Word(Base):
    """English word entry with translations."""

    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lemma: Mapped[str] = mapped_column(String(255), nullable=False)
    lemma_key: Mapped[str] = mapped_column(String(255), nullable=False)
    pos: Mapped[str] = mapped_column(String(10), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    translations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    dictionary_entries = relationship("DictionaryWord", back_populates="word", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("lemma_key", "pos", name="uq_words_lemma_key_pos"),
        CheckConstraint(
            f"pos IN ({', '.join(repr(p) for p in VALID_POS)})",
            name="ck_words_pos",
        ),
        CheckConstraint(
            f"level IS NULL OR level IN ({', '.join(repr(l) for l in VALID_LEVELS)})",
            name="ck_words_level",
        ),
    )

    def __repr__(self) -> str:
        return f"<Word id={self.id} lemma={self.lemma} pos={self.pos}>"
