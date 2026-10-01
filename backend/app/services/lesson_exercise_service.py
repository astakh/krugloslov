"""Service for lesson exercise evaluation."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models.event import Event
from app.models.lesson import Lesson
from app.models.lesson_exercise import LessonExercise
from app.models.lesson_exercise_word import LessonExerciseWord
from app.models.lesson_exercise_suggestion import LessonExerciseSuggestion
from app.models.user_word import UserWord
from app.models.word import Word
from app.schemas.lesson_evaluate import EvaluateResponse, SuggestedWord, WordEvaluation
from app.services.evaluate_translation_service import EvaluateTranslationService
from app.services.srs_service import calculate_srs

logger = logging.getLogger(__name__)


class LessonExerciseService:
    """Service for lesson exercise evaluation."""
    
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
    
    async def evaluate_exercise(
        self,
        exercise_id: int,
        user_translation: Optional[str],
        dont_know: bool,
    ) -> EvaluateResponse:
        """
        Evaluate user translation for an exercise.
        
        Args:
            exercise_id: Exercise ID
            user_translation: User's translation
            dont_know: Whether user clicked "I don't know"
        
        Returns:
            EvaluateResponse with evaluation results
        
        Raises:
            AppException: If validation fails or LLM error
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
        
        # Check lesson is in progress
        if lesson.status != "in_progress":
            raise AppException(
                status_code=409,
                code="lesson_not_active",
                message="Урок не активен"
            )
        
        # Check if already evaluated
        if exercise.status == "evaluated":
            # Return cached result
            return await self._get_cached_result(exercise)
        
        # Check if this is the current exercise (first pending)
        is_current = await self._is_current_exercise(lesson.id, exercise_id)
        if not is_current:
            raise AppException(
                status_code=409,
                code="not_current_exercise",
                message="Это не текущее упражнение"
            )
        
        # Evaluate translation using LLM
        eval_service = EvaluateTranslationService(self.session, self.user_id)
        try:
            word_evaluations, suggested_words = await eval_service.evaluate(
                exercise_id=exercise_id,
                user_translation=user_translation,
                dont_know=dont_know
            )
        except AppException as e:
            # Record LLM error event
            await self._create_event("llm_error", {
                "exercise_id": exercise_id,
                "error_code": e.code,
                "error_message": e.message,
            })
            raise
        
        # Start transaction for writing results
        async with self.session.begin():
            # Lock lesson and exercise
            result = await self.session.execute(
                select(Lesson)
                .where(Lesson.id == lesson.id)
                .with_for_update()
            )
            lesson = result.scalar_one()
            
            result = await self.session.execute(
                select(LessonExercise)
                .where(LessonExercise.id == exercise_id)
                .with_for_update()
            )
            exercise = result.scalar_one()
            
            # Check again if already evaluated
            if exercise.status == "evaluated":
                await self.session.rollback()
                return await self._get_cached_result(exercise)
            
            # Check lesson is still in progress
            if lesson.status != "in_progress":
                await self.session.rollback()
                raise AppException(
                    status_code=409,
                    code="lesson_not_active",
                    message="Урок не активен"
                )
            
            # Update SRS for each word
            await self._update_word_srs(word_evaluations, lesson.lesson_number)
            
            # Update exercise words
            await self._update_exercise_words(exercise_id, word_evaluations)
            
            # Update exercise
            exercise.user_translation = user_translation if not dont_know else None
            exercise.dont_know = dont_know
            exercise.status = "evaluated"
            exercise.evaluated_at = datetime.now(timezone.utc)
            
            # Save suggestions
            await self._save_suggestions(exercise_id, suggested_words)
            
            # Check if lesson is completed
            lesson_completed = await self._check_lesson_completed(lesson.id)
            
            # Create event
            await self._create_event("exercise_evaluated", {
                "exercise_id": exercise_id,
                "lesson_id": lesson.id
            })
        
        # Build response
        return EvaluateResponse(
            exercise_id=exercise_id,
            target_sentence=exercise.target_sentence,
            reference_translation=exercise.reference_translation,
            user_translation=exercise.user_translation,
            dont_know=dont_know,
            words=word_evaluations,
            suggestions=suggested_words,
            lesson_completed=lesson_completed
        )
    
    async def _get_exercise_with_lesson(self, exercise_id: int) -> LessonExercise:
        """Get exercise with lesson and profile using eager loading."""
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
    
    async def _is_current_exercise(self, lesson_id: int, exercise_id: int) -> bool:
        """Check if exercise is the current (first pending) exercise."""
        # Get first pending exercise
        result = await self.session.execute(
            select(LessonExercise)
            .where(
                LessonExercise.lesson_id == lesson_id,
                LessonExercise.status == "pending"
            )
            .order_by(LessonExercise.order_index)
            .limit(1)
        )
        first_pending = result.scalar_one_or_none()
        
        return first_pending and first_pending.id == exercise_id
    
    async def _get_cached_result(self, exercise: LessonExercise) -> EvaluateResponse:
        """Get cached evaluation result with eager loading."""
        from sqlalchemy.orm import selectinload
        
        # Get exercise words with eager loading
        result = await self.session.execute(
            select(LessonExerciseWord)
            .where(
                LessonExerciseWord.exercise_id == exercise.id,
                LessonExerciseWord.is_target == True
            )
            .options(selectinload(LessonExerciseWord.word))
        )
        exercise_words = list(result.scalars().all())
        
        # Build word evaluations
        word_evaluations = []
        for ew in exercise_words:
            word_evaluations.append(WordEvaluation(
                word_id=ew.word_id,
                lemma=ew.word.lemma,
                pos=ew.word.pos,
                surface_form=ew.surface_form,
                result=ew.result,
                user_fragment=ew.user_fragment,
                translations=ew.word.translations
            ))
        
        # Get suggestions with eager loading
        result = await self.session.execute(
            select(LessonExerciseSuggestion)
            .where(LessonExerciseSuggestion.exercise_id == exercise.id)
            .options(selectinload(LessonExerciseSuggestion.word))
        )
        suggestions_db = list(result.scalars().all())
        
        suggestions = []
        for sugg in suggestions_db:
            suggestions.append(SuggestedWord(
                word_id=sugg.word_id,
                lemma=sugg.word.lemma,
                pos=sugg.word.pos,
                translations=sugg.word.translations
            ))
        
        # Check if lesson is completed
        lesson_completed = exercise.lesson.status == "completed"
        
        return EvaluateResponse(
            exercise_id=exercise.id,
            target_sentence=exercise.target_sentence,
            reference_translation=exercise.reference_translation,
            user_translation=exercise.user_translation,
            dont_know=exercise.dont_know,
            words=word_evaluations,
            suggestions=suggestions,
            lesson_completed=lesson_completed
        )
    
    async def _update_word_srs(
        self,
        word_evaluations: List[WordEvaluation],
        lesson_number: int
    ):
        """Update SRS for each word based on evaluation."""
        # First, get user's learning_profile_id
        from app.models.learning_profile import LearningProfile
        profile_result = await self.session.execute(
            select(LearningProfile.id)
            .where(LearningProfile.user_id == self.user_id)
        )
        profile_id = profile_result.scalar_one_or_none()
        
        if not profile_id:
            logger.error(f"Learning profile not found for user {self.user_id}")
            return
        
        for eval in word_evaluations:
            # Get user_word using learning_profile_id
            result = await self.session.execute(
                select(UserWord)
                .where(
                    UserWord.learning_profile_id == profile_id,
                    UserWord.word_id == eval.word_id
                )
                .with_for_update()
            )
            user_word = result.scalar_one_or_none()
            
            if not user_word:
                logger.warning(f"UserWord not found for word_id={eval.word_id}")
                continue
            
            # Skip if not active
            if user_word.status != "active":
                logger.info(f"Skipping SRS update for non-active word: {eval.word_id}")
                continue
            
            # Calculate new SRS state
            srs_result = calculate_srs(
                stage=user_word.stage,
                result=eval.result,
                lesson_number=lesson_number
            )
            
            # Update user_word
            user_word.stage = srs_result.new_stage
            user_word.due_lesson_number = srs_result.due_lesson_number
            user_word.status = srs_result.status
            user_word.last_reviewed_at = datetime.now(timezone.utc)
    
    async def _update_exercise_words(
        self,
        exercise_id: int,
        word_evaluations: List[WordEvaluation]
    ):
        """Update exercise words with evaluation results."""
        for eval in word_evaluations:
            await self.session.execute(
                update(LessonExerciseWord)
                .where(
                    LessonExerciseWord.exercise_id == exercise_id,
                    LessonExerciseWord.word_id == eval.word_id,
                    LessonExerciseWord.is_target == True
                )
                .values(
                    result=eval.result,
                    user_fragment=eval.user_fragment,
                    stage_before=None,  # TODO: track stage_before
                    stage_after=None    # TODO: track stage_after
                )
            )
    
    async def _save_suggestions(
        self,
        exercise_id: int,
        suggested_words: List[SuggestedWord]
    ):
        """Save suggested words."""
        for sugg in suggested_words:
            suggestion = LessonExerciseSuggestion(
                exercise_id=exercise_id,
                word_id=sugg.word_id,
                state="suggested"
            )
            self.session.add(suggestion)
    
    async def _check_lesson_completed(self, lesson_id: int) -> bool:
        """Check if all exercises are evaluated and complete lesson if needed."""
        # Count pending exercises
        result = await self.session.execute(
            select(LessonExercise)
            .where(
                LessonExercise.lesson_id == lesson_id,
                LessonExercise.status == "pending"
            )
        )
        pending_count = len(list(result.scalars().all()))
        
        if pending_count == 0:
            # Mark lesson as completed
            await self.session.execute(
                update(Lesson)
                .where(Lesson.id == lesson_id)
                .values(
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                    completed_local_date=datetime.now(timezone.utc).date()
                )
            )
            
            # Create event
            await self._create_event("lesson_completed", {"lesson_id": lesson_id})
            
            return True
        
        return False
    
    async def _create_event(self, event_type: str, payload: dict):
        """Create an event."""
        event = Event(
            user_id=self.user_id,
            type=event_type,
            payload=payload
        )
        self.session.add(event)
    
    async def get_exercise_result(
        self,
        lesson_id: int,
        exercise_id: int
    ) -> EvaluateResponse:
        """
        Get cached result for an evaluated exercise with eager loading.
        
        Args:
            lesson_id: Lesson ID
            exercise_id: Exercise ID
        
        Returns:
            EvaluateResponse with cached results
        """
        from sqlalchemy.orm import selectinload
        
        # Get exercise with eager loading
        result = await self.session.execute(
            select(LessonExercise)
            .where(
                LessonExercise.id == exercise_id,
                LessonExercise.lesson_id == lesson_id
            )
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
        
        # Check lesson belongs to user
        if exercise.lesson.learning_profile.user_id != self.user_id:
            raise AppException(
                status_code=403,
                code="forbidden",
                message="Упражнение не принадлежит пользователю"
            )
        
        # Check if evaluated
        if exercise.status != "evaluated":
            raise AppException(
                status_code=409,
                code="exercise_not_evaluated",
                message="Упражнение ещё не оценено"
            )
        
        # Return cached result
        return await self._get_cached_result(exercise)
    
    async def get_exercise_info(
        self,
        lesson_id: int,
        exercise_id: int
    ) -> dict:
        """
        Get exercise information with eager loading.
        
        Args:
            lesson_id: Lesson ID
            exercise_id: Exercise ID
        
        Returns:
            Dictionary with exercise info
        """
        from sqlalchemy import func
        from sqlalchemy.orm import selectinload
        from app.schemas.lesson_evaluate import ExerciseInfoResponse
        
        # Get exercise with eager loading
        result = await self.session.execute(
            select(LessonExercise)
            .where(
                LessonExercise.id == exercise_id,
                LessonExercise.lesson_id == lesson_id
            )
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
        
        # Check lesson belongs to user
        if exercise.lesson.learning_profile.user_id != self.user_id:
            raise AppException(
                status_code=403,
                code="forbidden",
                message="Упражнение не принадлежит пользователю"
            )
        
        # Count total exercises
        result = await self.session.execute(
            select(func.count(LessonExercise.id)).where(
                LessonExercise.lesson_id == lesson_id
            )
        )
        total_exercises = result.scalar()
        
        # Get target words with eager loading
        from app.schemas.lesson_evaluate import TargetWordInfo
        result = await self.session.execute(
            select(LessonExerciseWord, Word)
            .join(Word, LessonExerciseWord.word_id == Word.id)
            .where(
                LessonExerciseWord.exercise_id == exercise_id,
                LessonExerciseWord.is_target == True
            )
            .options(selectinload(LessonExerciseWord.word))
        )
        target_words = [
            TargetWordInfo(
                word_id=exercise_word.word_id,
                lemma=exercise_word.word.lemma,
                pos=exercise_word.word.pos
            )
            for exercise_word, word in result.all()
        ]
        
        return ExerciseInfoResponse(
            exercise_id=exercise.id,
            lesson_id=lesson_id,
            order_index=exercise.order_index,
            total_exercises=total_exercises,
            target_sentence=exercise.target_sentence,
            status=exercise.status,
            target_words=target_words
        )
