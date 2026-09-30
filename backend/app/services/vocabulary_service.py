"""Service for vocabulary operations."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models import (
    Lesson,
    LessonExercise,
    LessonExerciseWord,
    LearningProfile,
    User,
    UserWord,
    Word,
)
from app.schemas.vocabulary import (
    ContextHistoryItem,
    VocabularyListResponse,
    VocabularyWordDetail,
    VocabularyWordItem,
)


class VocabularyService:
    """Service for managing user vocabulary."""

    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user

    async def get_vocabulary_list(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> VocabularyListResponse:
        """
        Get user's vocabulary list with filtering and search.

        Args:
            status: Filter by status (active/mastered/ignored)
            search: Search by lemma or translations
            page: Page number (1-indexed)
            page_size: Items per page (max 50)

        Returns:
            VocabularyListResponse with paginated results
        """
        # Validate page_size
        page_size = min(page_size, 50)

        # Get user's learning profile
        profile = await self._get_learning_profile()

        # Build base query
        query = (
            select(UserWord, Word)
            .join(Word, UserWord.word_id == Word.id)
            .where(UserWord.learning_profile_id == profile.id)
        )

        # Apply status filter
        if status:
            query = query.where(UserWord.status == status)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            # Search in lemma (case-insensitive)
            lemma_match = func.lower(Word.lemma).like(func.lower(search_pattern))
            # Search in translations (JSONB array)
            # PostgreSQL: check if any translation contains the search term
            translation_match = Word.translations.op("@>")(
                func.to_jsonb([search])
            )
            query = query.where(or_(lemma_match, translation_match))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(func.lower(Word.lemma)).offset(offset).limit(page_size)

        # Execute query
        result = await self.session.execute(query)
        rows = result.all()

        # Get last_lesson_number for due_in_lessons calculation
        last_lesson_number = profile.last_lesson_number

        # Build response items
        words = []
        for user_word, word in rows:
            # Calculate due_in_lessons
            if user_word.status == "active" and user_word.due_lesson_number:
                due_in_lessons = max(
                    user_word.due_lesson_number - last_lesson_number, 0
                )
            else:
                due_in_lessons = 0

            words.append(
                VocabularyWordItem(
                    word_id=word.id,
                    lemma=word.lemma,
                    pos=word.pos,
                    translations=word.translations,
                    status=user_word.status,
                    stage=user_word.stage,
                    due_in_lessons=due_in_lessons,
                )
            )

        return VocabularyListResponse(
            words=words, total=total, page=page, page_size=page_size
        )

    async def get_word_detail(self, word_id: int) -> VocabularyWordDetail:
        """
        Get detailed information about a word including context history.

        Args:
            word_id: ID of the word

        Returns:
            VocabularyWordDetail with full information

        Raises:
            AppException: If word not found in user's vocabulary
        """
        # Get user's learning profile
        profile = await self._get_learning_profile()

        # Get user_word with word data
        query = (
            select(UserWord, Word)
            .join(Word, UserWord.word_id == Word.id)
            .where(
                and_(
                    UserWord.learning_profile_id == profile.id,
                    UserWord.word_id == word_id,
                )
            )
        )
        result = await self.session.execute(query)
        row = result.first()

        if not row:
            raise AppException(
                status_code=404,
                code="word_not_found",
                message="Слово не найдено в вашем словаре",
            )

        user_word, word = row

        # Calculate due_in_lessons
        if user_word.status == "active" and user_word.due_lesson_number:
            due_in_lessons = max(
                user_word.due_lesson_number - profile.last_lesson_number, 0
            )
        else:
            due_in_lessons = 0

        # Get context history (last 20 exercises)
        context_history = await self._get_context_history(word_id)

        return VocabularyWordDetail(
            word_id=word.id,
            lemma=word.lemma,
            pos=word.pos,
            translations=word.translations,
            status=user_word.status,
            stage=user_word.stage,
            due_in_lessons=due_in_lessons,
            context_history=context_history,
        )

    async def change_status(self, word_id: int, new_status: str) -> str:
        """
        Change word status with validation.

        Args:
            word_id: ID of the word
            new_status: New status (active/ignored)

        Returns:
            Success message

        Raises:
            AppException: If transition is invalid
        """
        # Get user's learning profile
        profile = await self._get_learning_profile()

        # Get user_word with FOR UPDATE
        query = (
            select(UserWord)
            .where(
                and_(
                    UserWord.learning_profile_id == profile.id,
                    UserWord.word_id == word_id,
                )
            )
            .with_for_update()
        )
        result = await self.session.execute(query)
        user_word = result.scalar_one_or_none()

        if not user_word:
            raise AppException(
                status_code=404,
                code="word_not_found",
                message="Слово не найдено в вашем словаре",
            )

        current_status = user_word.status

        # Validate transition
        if current_status == new_status:
            # Idempotent: same status
            return "Статус не изменён"

        if current_status == "active" and new_status == "ignored":
            # active → ignored
            user_word.status = "ignored"
            user_word.due_lesson_number = None
        elif current_status == "ignored" and new_status == "active":
            # ignored → active
            user_word.status = "active"
            user_word.stage = 0
            user_word.due_lesson_number = profile.last_lesson_number + 1
        elif current_status == "mastered" and new_status == "active":
            # mastered → active
            user_word.status = "active"
            user_word.stage = 0
            user_word.due_lesson_number = profile.last_lesson_number + 1
        else:
            # Invalid transition
            raise AppException(
                status_code=409,
                code="invalid_transition",
                message=f"Переход из '{current_status}' в '{new_status}' невозможен",
            )

        await self.session.commit()
        return f"Статус изменён на '{new_status}'"

    async def _get_learning_profile(self) -> LearningProfile:
        """Get user's learning profile."""
        query = select(LearningProfile).where(
            LearningProfile.user_id == self.user.id
        )
        result = await self.session.execute(query)
        profile = result.scalar_one_or_none()

        if not profile:
            raise AppException(
                status_code=404,
                code="profile_not_found",
                message="Профиль обучения не найден",
            )

        return profile

    async def _get_context_history(self, word_id: int) -> List[ContextHistoryItem]:
        """
        Get context history for a word (last 20 exercises).

        Includes both target words and hints (is_target=false).
        """
        query = (
            select(
                LessonExercise.target_sentence,
                LessonExerciseWord.surface_form,
                LessonExerciseWord.result,
                Lesson.evaluated_at,
            )
            .join(
                LessonExercise,
                LessonExerciseWord.exercise_id == LessonExercise.id,
            )
            .join(Lesson, LessonExercise.lesson_id == Lesson.id)
            .where(
                and_(
                    LessonExerciseWord.word_id == word_id,
                    Lesson.status == "completed",
                    Lesson.evaluated_at.isnot(None),
                )
            )
            .order_by(Lesson.evaluated_at.desc())
            .limit(20)
        )

        result = await self.session.execute(query)
        rows = result.all()

        return [
            ContextHistoryItem(
                sentence=row.target_sentence,
                surface_form=row.surface_form,
                result=row.result,
                date=row.evaluated_at,
            )
            for row in rows
        ]
