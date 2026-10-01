"""Lesson preview service."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import List, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dictionary_word import DictionaryWord
from app.models.learning_profile import LearningProfile
from app.models.lesson import Lesson
from app.models.user import User
from app.models.user_word import UserWord
from app.models.word import Word
from app.schemas.lesson import (
    LimitReachedState,
    NoWordsState,
    ReadyState,
    ResumeState,
    WordInfo,
    WordInfoWithTranslations,
)


class LessonPreviewService:
    """Service for lesson word selection preview."""

    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user
        self.N = None  # Will be set from profile in preview()

    async def preview(self) -> dict:
        """
        Generate lesson preview without creating anything in DB.
        
        Returns:
            Dictionary with state and data based on current conditions
        """
        # Get user's timezone
        user_tz = ZoneInfo(self.user.timezone)
        now_utc = datetime.now(ZoneInfo("UTC"))
        today = now_utc.astimezone(user_tz).date()

        # Get profile
        profile = await self._get_profile()
        if not profile:
            raise ValueError("Learning profile not found")

        # Set words per lesson from profile
        self.N = profile.words_per_lesson

        # Step 1: Check for in-progress lesson
        in_progress = await self._get_in_progress_lesson(profile.id)
        if in_progress:
            lesson, done, total = in_progress
            return ResumeState(
                state="resume",
                lesson_id=lesson.id,
                exercises_done=done,
                exercises_total=total,
            ).model_dump()

        # Step 2: Check daily limit
        lessons_today = await self._count_lessons_today(profile.id, today)
        if lessons_today >= profile.daily_lesson_limit:
            # Calculate resets_at (next midnight in user's timezone)
            from datetime import date, time, timedelta
            tomorrow = today + timedelta(days=1)
            resets_at = datetime(
                tomorrow.year, tomorrow.month, tomorrow.day,
                tzinfo=user_tz
            ).astimezone(ZoneInfo("UTC"))
            
            return LimitReachedState(
                state="limit_reached",
                resets_at=resets_at,
            ).model_dump()

        # Step 3: Calculate next lesson number and seed
        next_lesson_number = profile.last_lesson_number + 1
        seed = self._calculate_seed(profile.id, next_lesson_number)

        # Step 5: Get due words
        due_words = await self._get_due_words(profile.id, next_lesson_number, seed)

        # Step 6: Get new words if needed
        new_words = []
        dictionary_exhausted = False
        
        if len(due_words) < self.N:
            k = self.N - len(due_words)
            new_words, dictionary_exhausted = await self._get_new_words(
                profile.id, profile.dictionary_id, profile.level, seed, due_words
            )

        # Step 7: Determine final state
        if len(due_words) == 0 and len(new_words) == 0:
            return NoWordsState(state="no_words").model_dump()

        return ReadyState(
            state="ready",
            lesson_number=next_lesson_number,
            due_words=[WordInfo(**w) for w in due_words],
            new_words=[WordInfoWithTranslations(**w) for w in new_words],
            dictionary_exhausted=dictionary_exhausted,
        ).model_dump()

    async def decline_word(self, word_id: int) -> dict:
        """
        Decline a new word and recalculate preview.
        
        Args:
            word_id: ID of the word to decline
            
        Returns:
            Updated preview after declining
        """
        from app.services.events import record_event
        from app.exceptions import AppException

        # Check onboarding
        if not self.user.is_onboarded:
            raise AppException(
                status_code=409,
                code="onboarding_required",
                message="Требуется завершение онбординга"
            )

        # Get profile
        profile = await self._get_profile()
        if not profile:
            raise ValueError("Learning profile not found")

        # Check for in-progress lesson
        in_progress = await self._get_in_progress_lesson(profile.id)
        if in_progress:
            raise AppException(
                status_code=409,
                code="lesson_in_progress",
                message="Нельзя отклонять слово во время активного урока"
            )

        # Check if word is in active dictionary
        word_in_dict = await self._check_word_in_dictionary(word_id, profile.dictionary_id)
        if not word_in_dict:
            raise AppException(
                status_code=404,
                code="word_not_found",
                message="Слово не найдено в вашем словаре"
            )

        # Check existing user_word record
        user_word = await self._get_user_word(profile.id, word_id)
        
        if user_word:
            if user_word.status == "ignored":
                # Idempotent success
                pass
            elif user_word.status in ["active", "mastered"]:
                raise AppException(
                    status_code=409,
                    code="word_already_learning",
                    message="Нельзя отклонить слово, которое уже изучается"
                )
        else:
            # Create ignored record
            from app.models.user_word import UserWord
            new_user_word = UserWord(
                learning_profile_id=profile.id,
                word_id=word_id,
                status="ignored",
                stage=0,
                due_lesson_number=None,
                source="decline",
            )
            self.session.add(new_user_word)

            # Record event
            await record_event(
                self.session,
                self.user.id,
                "new_word_declined",
                {"word_id": word_id}
            )

            await self.session.commit()

        # Recalculate preview
        return await self.preview()

    async def _get_profile(self) -> LearningProfile | None:
        """Get user's learning profile."""
        result = await self.session.execute(
            select(LearningProfile).where(LearningProfile.user_id == self.user.id)
        )
        return result.scalar_one_or_none()

    async def _get_in_progress_lesson(self, profile_id: int) -> Tuple[Lesson, int, int] | None:
        """Get in-progress lesson with exercise counts."""
        from app.models.lesson_exercise import LessonExercise

        result = await self.session.execute(
            select(Lesson).where(
                Lesson.learning_profile_id == profile_id,
                Lesson.status == "in_progress"
            )
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            return None

        # Count exercises
        total_result = await self.session.execute(
            select(func.count(LessonExercise.id)).where(
                LessonExercise.lesson_id == lesson.id
            )
        )
        total = total_result.scalar_one()

        done_result = await self.session.execute(
            select(func.count(LessonExercise.id)).where(
                LessonExercise.lesson_id == lesson.id,
                LessonExercise.status == "evaluated"
            )
        )
        done = done_result.scalar_one()

        return lesson, done, total

    async def _count_lessons_today(self, profile_id: int, today) -> int:
        """Count lessons started today."""
        result = await self.session.execute(
            select(func.count(Lesson.id)).where(
                Lesson.learning_profile_id == profile_id,
                Lesson.started_local_date == today
            )
        )
        return result.scalar_one()

    def _calculate_seed(self, profile_id: int, lesson_number: int) -> str:
        """Calculate deterministic seed for lesson."""
        data = f"{profile_id}:{lesson_number}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _calculate_rank(self, seed: str, word_id: int) -> str:
        """Calculate deterministic rank for word."""
        data = f"{seed}:{word_id}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def _get_due_words(
        self, profile_id: int, next_lesson_number: int, seed: str
    ) -> List[dict]:
        """Get words due for review."""
        result = await self.session.execute(
            select(UserWord, Word).join(Word, UserWord.word_id == Word.id).where(
                UserWord.learning_profile_id == profile_id,
                UserWord.status == "active",
                UserWord.due_lesson_number <= next_lesson_number
            )
        )
        
        candidates = []
        for user_word, word in result.all():
            rank = self._calculate_rank(seed, word.id)
            candidates.append({
                "word_id": word.id,
                "lemma": word.lemma,
                "pos": word.pos,
                "rank": rank,
            })

        # Sort by rank and take first N
        candidates.sort(key=lambda x: x["rank"])
        result_words = []
        for c in candidates[:self.N]:
            result_words.append({
                "word_id": c["word_id"],
                "lemma": c["lemma"],
                "pos": c["pos"],
            })

        return result_words

    async def _get_new_words(
        self,
        profile_id: int,
        dictionary_id: int,
        profile_level: str,
        seed: str,
        due_words: List[dict],
    ) -> Tuple[List[dict], bool]:
        """Get new words from dictionary."""
        # Get words already in user_words (any status)
        existing_result = await self.session.execute(
            select(UserWord.word_id).where(
                UserWord.learning_profile_id == profile_id
            )
        )
        existing_word_ids = {row[0] for row in existing_result.all()}

        # Add due words to exclusion list
        due_word_ids = {w["word_id"] for w in due_words}
        exclude_ids = existing_word_ids | due_word_ids

        # Determine allowed levels
        allowed_levels = [profile_level]
        if profile_level != "A1":
            # Allow one level below
            level_order = ["A1", "A2", "B1", "B2", "C1", "C2"]
            idx = level_order.index(profile_level)
            if idx > 0:
                allowed_levels.append(level_order[idx - 1])

        # Get candidate words from dictionary
        result = await self.session.execute(
            select(Word, DictionaryWord).join(
                DictionaryWord, Word.id == DictionaryWord.word_id
            ).where(
                DictionaryWord.dictionary_id == dictionary_id,
                ~Word.id.in_(exclude_ids)
            )
        )

        candidates = []
        for word, _ in result.all():
            # Check level constraint
            if word.level is not None and word.level not in allowed_levels:
                continue
            
            rank = self._calculate_rank(seed, word.id)
            candidates.append({
                "word_id": word.id,
                "lemma": word.lemma,
                "pos": word.pos,
                "translations": word.translations,
                "rank": rank,
            })

        # Sort by rank
        candidates.sort(key=lambda x: x["rank"])

        # Take what we need
        k = self.N - len(due_words)
        selected = candidates[:k]
        dictionary_exhausted = len(selected) < k

        result_words = []
        for c in selected:
            result_words.append({
                "word_id": c["word_id"],
                "lemma": c["lemma"],
                "pos": c["pos"],
                "translations": c["translations"],
            })

        return result_words, dictionary_exhausted

    async def _check_word_in_dictionary(self, word_id: int, dictionary_id: int) -> bool:
        """Check if word is in the active dictionary."""
        result = await self.session.execute(
            select(DictionaryWord).where(
                DictionaryWord.word_id == word_id,
                DictionaryWord.dictionary_id == dictionary_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def _get_user_word(self, profile_id: int, word_id: int) -> UserWord | None:
        """Get user_word record if exists."""
        result = await self.session.execute(
            select(UserWord).where(
                UserWord.learning_profile_id == profile_id,
                UserWord.word_id == word_id
            )
        )
        return result.scalar_one_or_none()
