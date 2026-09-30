"""Service for dictionaries list."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dictionary, DictionaryWord
from app.schemas.profile import DictionaryListItem, DictionariesListResponse


class DictionariesService:
    """Service for listing dictionaries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dictionaries(self) -> DictionariesListResponse:
        """Get list of all dictionaries with word counts."""
        # Query dictionaries with word counts
        result = await self.session.execute(
            select(
                Dictionary.id,
                Dictionary.code,
                Dictionary.name,
                Dictionary.description,
                Dictionary.is_general,
                func.count(DictionaryWord.word_id).label("words_total"),
            )
            .outerjoin(DictionaryWord, Dictionary.id == DictionaryWord.dictionary_id)
            .group_by(
                Dictionary.id,
                Dictionary.code,
                Dictionary.name,
                Dictionary.description,
                Dictionary.is_general,
            )
            .order_by(Dictionary.name)
        )
        
        dictionaries = [
            DictionaryListItem(
                id=row.id,
                code=row.code,
                name=row.name,
                description=row.description,
                is_general=row.is_general,
                words_total=row.words_total,
            )
            for row in result.all()
        ]
        
        return DictionariesListResponse(dictionaries=dictionaries)
