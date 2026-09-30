"""Word and Dictionary repositories."""

from __future__ import annotations

import unicodedata
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dictionary import Dictionary
from app.models.dictionary_word import DictionaryWord
from app.models.word import Word


def normalize_lemma(lemma: str) -> str:
    """Normalize a lemma to its canonical key form.

    Applies: trim -> NFC normalization -> casefold.
    """
    return unicodedata.normalize("NFC", lemma.strip()).casefold()


class WordRepository:
    """Data access layer for Word entity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, word_id: int) -> Optional[Word]:
        """Get word by primary key."""
        result = await self.session.execute(select(Word).where(Word.id == word_id))
        return result.scalar_one_or_none()

    async def get_by_lemma_key_and_pos(self, lemma_key: str, pos: str) -> Optional[Word]:
        """Get word by normalized lemma key and part of speech."""
        result = await self.session.execute(
            select(Word).where(Word.lemma_key == lemma_key, Word.pos == pos)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        lemma: str,
        pos: str,
        translations: List[str],
        level: Optional[str] = None,
    ) -> Word:
        """Create a new word with normalized lemma_key."""
        word = Word(
            lemma=lemma.strip(),
            lemma_key=normalize_lemma(lemma),
            pos=pos,
            level=level,
            translations=translations,
        )
        self.session.add(word)
        await self.session.flush()
        return word

    async def get_or_create(
        self,
        lemma: str,
        pos: str,
        translations: List[str],
        level: Optional[str] = None,
    ) -> tuple[Word, bool]:
        """Get existing word or create a new one. Returns (word, created)."""
        lemma_key = normalize_lemma(lemma)
        existing = await self.get_by_lemma_key_and_pos(lemma_key, pos)
        if existing:
            return existing, False
        word = await self.create(lemma, pos, translations, level)
        return word, True


class DictionaryRepository:
    """Data access layer for Dictionary entity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, dictionary_id: int) -> Optional[Dictionary]:
        """Get dictionary by primary key."""
        result = await self.session.execute(
            select(Dictionary).where(Dictionary.id == dictionary_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Dictionary]:
        """Get dictionary by code."""
        result = await self.session.execute(
            select(Dictionary).where(Dictionary.code == code)
        )
        return result.scalar_one_or_none()

    async def get_general(self) -> Optional[Dictionary]:
        """Get the general dictionary (at most one exists)."""
        result = await self.session.execute(
            select(Dictionary).where(Dictionary.is_general == True)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        code: str,
        name: str,
        description: str = "",
        is_general: bool = False,
    ) -> Dictionary:
        """Create a new dictionary."""
        dictionary = Dictionary(
            code=code,
            name=name,
            description=description,
            is_general=is_general,
        )
        self.session.add(dictionary)
        await self.session.flush()
        return dictionary

    async def link_word(self, dictionary_id: int, word_id: int) -> DictionaryWord:
        """Link a word to a dictionary."""
        entry = DictionaryWord(dictionary_id=dictionary_id, word_id=word_id)
        self.session.add(entry)
        await self.session.flush()
        return entry
