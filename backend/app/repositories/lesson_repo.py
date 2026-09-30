"""Lesson and UserWord repositories."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import Lesson
from app.models.user_word import UserWord


class LessonRepository:
    """Data access layer for Lesson entity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, lesson_id: int) -> Optional[Lesson]:
        """Get lesson by primary key."""
        result = await self.session.execute(
            select(Lesson).where(Lesson.id == lesson_id)
        )
        return result.scalar_one_or_none()

    async def get_by_profile_and_number(
        self, learning_profile_id: int, lesson_number: int
    ) -> Optional[Lesson]:
        """Get lesson by profile and number."""
        result = await self.session.execute(
            select(Lesson).where(
                Lesson.learning_profile_id == learning_profile_id,
                Lesson.lesson_number == lesson_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_in_progress(self, learning_profile_id: int) -> Optional[Lesson]:
        """Get the currently in-progress lesson for a profile (at most one)."""
        result = await self.session.execute(
            select(Lesson).where(
                Lesson.learning_profile_id == learning_profile_id,
                Lesson.status == "in_progress",
            )
        )
        return result.scalar_one_or_none()


class UserWordRepository:
    """Data access layer for UserWord entity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_word_id: int) -> Optional[UserWord]:
        """Get user word by primary key."""
        result = await self.session.execute(
            select(UserWord).where(UserWord.id == user_word_id)
        )
        return result.scalar_one_or_none()

    async def get_by_profile_and_word(
        self, learning_profile_id: int, word_id: int
    ) -> Optional[UserWord]:
        """Get user word by profile and word."""
        result = await self.session.execute(
            select(UserWord).where(
                UserWord.learning_profile_id == learning_profile_id,
                UserWord.word_id == word_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_due(
        self, learning_profile_id: int, lesson_number: int
    ) -> List[UserWord]:
        """Get active words due for review at or before the given lesson number."""
        result = await self.session.execute(
            select(UserWord).where(
                UserWord.learning_profile_id == learning_profile_id,
                UserWord.status == "active",
                UserWord.due_lesson_number <= lesson_number,
            )
        )
        return list(result.scalars().all())

    async def create(
        self,
        learning_profile_id: int,
        word_id: int,
        status: str = "active",
        stage: int = 0,
        due_lesson_number: Optional[int] = None,
        source: str = "dictionary",
    ) -> UserWord:
        """Create a new user word entry."""
        user_word = UserWord(
            learning_profile_id=learning_profile_id,
            word_id=word_id,
            status=status,
            stage=stage,
            due_lesson_number=due_lesson_number,
            source=source,
        )
        self.session.add(user_word)
        await self.session.flush()
        return user_word
