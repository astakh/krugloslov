"""Dictionary-Word association model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DictionaryWord(Base):
    """Association between dictionaries and words."""

    __tablename__ = "dictionary_words"

    dictionary_id: Mapped[int] = mapped_column(
        ForeignKey("dictionaries.id", ondelete="CASCADE"), primary_key=True
    )
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), primary_key=True
    )

    # Relationships
    dictionary = relationship("Dictionary", back_populates="words")
    word = relationship("Word", back_populates="dictionary_entries")

    __table_args__ = (
        UniqueConstraint("dictionary_id", "word_id", name="uq_dictionary_words_dict_word"),
    )

    def __repr__(self) -> str:
        return f"<DictionaryWord dict={self.dictionary_id} word={self.word_id}>"
