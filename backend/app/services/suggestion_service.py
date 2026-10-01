"""Service for handling exercise suggestions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models.event import Event
from app.models.lesson_exercise import LessonExercise
from app.models.lesson_exercise_suggestion import LessonExerciseSuggestion
from app.models.lesson_exercise_word import LessonExerciseWord
from app.models.user_word import UserWord
from app.schemas.lesson_evaluate import SuggestionActionResponse

logger = logging.getLogger(__name__)


class SuggestionService:
    """Service for handling exercise suggestions."""
    
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
    
    async def handle_suggestion(
        self,
        exercise_id: int,
        word_id: int,
        action: str
    ) -> SuggestionActionResponse:
        """
        Handle suggestion action (add or ignore).
        
        Args:
            exercise_id: Exercise ID
            word_id: Word ID
            action: "add" or "ignore"
        
        Returns:
            SuggestionActionResponse
        """
        # Get exercise with lesson
        exercise = await self._get_exercise_with_lesson(exercise_id)
        lesson = exercise.lesson
        
        # Check lesson belongs to user
        if lesson.learning_profile.user_id != self.user_id:
            raise AppException(
                status_code=403,
                code="forbidden",
                message="Упражнение не принадлежит пользователю"
            )
        
        # Get suggestion
        suggestion = await self._get_suggestion(exercise_id, word_id)
        
        if action == "add":
            return await self._add_suggestion(suggestion, lesson.lesson_number)
        elif action == "ignore":
            return await self._ignore_suggestion(suggestion)
        else:
            raise AppException(
                status_code=422,
                code="invalid_action",
                message="Действие должно быть 'add' или 'ignore'"
            )
    
    async def _get_exercise_with_lesson(self, exercise_id: int) -> LessonExercise:
        """Get exercise with lesson using eager loading."""
        from sqlalchemy.orm import selectinload
        from app.models.lesson import Lesson
        
        result = await self.session.execute(
            select(LessonExercise)
            .where(LessonExercise.id == exercise_id)
            .options(
                selectinload(LessonExercise.lesson)
                .selectinload(Lesson.learning_profile)
            )
        )
        exercise = result.scalar_one_or_none()
        
        if not exercise:
            raise AppException(
                status_code=404,
                code="exercise_not_found",
                message="Упражнение не найдено"
            )
        
        return exercise
    
    async def _get_suggestion(
        self,
        exercise_id: int,
        word_id: int
    ) -> LessonExerciseSuggestion:
        """Get suggestion for exercise and word."""
        result = await self.session.execute(
            select(LessonExerciseSuggestion)
            .where(
                LessonExerciseSuggestion.exercise_id == exercise_id,
                LessonExerciseSuggestion.word_id == word_id
            )
        )
        suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            raise AppException(
                status_code=404,
                code="suggestion_not_found",
                message="Подсказка не найдена"
            )
        
        return suggestion
    
    async def _add_suggestion(
        self,
        suggestion: LessonExerciseSuggestion,
        lesson_number: int
    ) -> SuggestionActionResponse:
        """Add suggested word to user vocabulary."""
        # Check if already added
        if suggestion.state == "added":
            return SuggestionActionResponse(message="Слово уже добавлено")
        
        # Check if already ignored
        if suggestion.state == "ignored":
            raise AppException(
                status_code=409,
                code="suggestion_ignored",
                message="Подсказка была отклонена"
            )
        
        # Check if user_word already exists
        result = await self.session.execute(
            select(UserWord)
            .where(
                UserWord.user_id == self.user_id,
                UserWord.word_id == suggestion.word_id
            )
        )
        existing_user_word = result.scalar_one_or_none()
        
        if existing_user_word:
            if existing_user_word.status != "ignored":
                raise AppException(
                    status_code=409,
                    code="already_in_vocabulary",
                    message="Слово уже в словаре"
                )
            # Update existing ignored word
            existing_user_word.status = "active"
            existing_user_word.stage = 0
            existing_user_word.due_lesson_number = lesson_number + 1
            existing_user_word.source = "suggestion"
        else:
            # Create new user_word
            user_word = UserWord(
                user_id=self.user_id,
                word_id=suggestion.word_id,
                status="active",
                stage=0,
                due_lesson_number=lesson_number + 1,
                source="suggestion"
            )
            self.session.add(user_word)
        
        # Create lesson_exercise_word entry
        exercise_word = LessonExerciseWord(
            exercise_id=suggestion.exercise_id,
            word_id=suggestion.word_id,
            is_target=False,
            is_new=True,
            surface_form=None,
            result=None,
            user_fragment=None,
            stage_before=None,
            stage_after=None
        )
        self.session.add(exercise_word)
        
        # Update suggestion state
        suggestion.state = "added"
        
        # Create event
        event = Event(
            user_id=self.user_id,
            type="new_word_accepted",
            payload={
                "word_id": suggestion.word_id,
                "source": "suggestion",
                "exercise_id": suggestion.exercise_id
            }
        )
        self.session.add(event)
        
        await self.session.commit()
        
        return SuggestionActionResponse(message="Слово добавлено в словарь")
    
    async def _ignore_suggestion(
        self,
        suggestion: LessonExerciseSuggestion
    ) -> SuggestionActionResponse:
        """Ignore suggested word."""
        # Check if already ignored
        if suggestion.state == "ignored":
            return SuggestionActionResponse(message="Подсказка уже отклонена")
        
        # Check if already added
        if suggestion.state == "added":
            raise AppException(
                status_code=409,
                code="suggestion_added",
                message="Подсказка была добавлена"
            )
        
        # Check if user_word already exists
        result = await self.session.execute(
            select(UserWord)
            .where(
                UserWord.user_id == self.user_id,
                UserWord.word_id == suggestion.word_id
            )
        )
        existing_user_word = result.scalar_one_or_none()
        
        if not existing_user_word:
            # Create user_word with ignored status
            user_word = UserWord(
                user_id=self.user_id,
                word_id=suggestion.word_id,
                status="ignored",
                stage=0,
                due_lesson_number=None,
                source="decline"
            )
            self.session.add(user_word)
        
        # Update suggestion state
        suggestion.state = "ignored"
        
        # Create event
        event = Event(
            user_id=self.user_id,
            type="new_word_declined",
            payload={
                "word_id": suggestion.word_id,
                "source": "suggestion",
                "exercise_id": suggestion.exercise_id
            }
        )
        self.session.add(event)
        
        await self.session.commit()
        
        return SuggestionActionResponse(message="Подсказка отклонена")
