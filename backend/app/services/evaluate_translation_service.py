"""Service for evaluating user translations using LLM."""

from __future__ import annotations

import logging
import re
import secrets
import unicodedata
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AppException
from app.llm import gigachat_client
from app.llm.exceptions import LlmError, LlmInvalidResponse, LlmRefused
from app.models.lesson_exercise import LessonExercise
from app.models.lesson_exercise_word import LessonExerciseWord
from app.models.word import Word
from app.schemas.lesson_evaluate import (
    LlmEvaluateResponse,
    LlmSuggestedWord,
    LlmWordEvaluation,
    SuggestedWord,
    WordEvaluation,
)
from app.services.llm_logger import LlmLogger
from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)


class EvaluateTranslationService:
    """Service for evaluating user translations using LLM."""
    
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
    
    async def evaluate(
        self,
        exercise_id: int,
        user_translation: Optional[str],
        dont_know: bool,
    ) -> Tuple[List[WordEvaluation], List[SuggestedWord]]:
        """
        Evaluate user translation for an exercise.
        
        Args:
            exercise_id: Exercise ID
            user_translation: User's translation (None if dont_know)
            dont_know: Whether user clicked "I don't know"
        
        Returns:
            Tuple of (word_evaluations, suggested_words)
        
        Raises:
            AppException: If LLM fails or returns invalid response
        """
        # Get exercise and target words
        exercise = await self._get_exercise(exercise_id)
        target_words = await self._get_target_words(exercise_id)
        
        if dont_know:
            # Don't call LLM, mark all as incorrect
            return self._create_dont_know_evaluations(target_words), []
        
        # Validate user translation
        validated_translation = self._validate_translation(user_translation)
        
        # Call LLM for evaluation (single attempt, no retries)
        try:
            llm_response = await self._call_llm(exercise, target_words, validated_translation)
        except LlmRefused:
            raise AppException(
                status_code=422,
                code="llm_refused",
                message="Модель отказалась проверять перевод"
            )
        except LlmInvalidResponse as e:
            logger.error(f"LLM returned invalid response: {e}")
            raise AppException(
                status_code=503,
                code="llm_invalid_response",
                message="Модель вернула некорректный ответ, попробуйте ещё раз"
            )
        except LlmError as e:
            logger.error(f"LLM evaluation failed: {e}")
            raise AppException(
                status_code=503,
                code="llm_unavailable",
                message="Сервер перегружен, попробуйте ещё раз"
            )
        
        # Validate and process LLM response
        word_evaluations = await self._process_llm_evaluations(
            llm_response.evaluations, target_words, validated_translation
        )
        
        suggested_words = await self._process_suggested_words(
            llm_response.new_suggested_words, target_words
        )
        
        return word_evaluations, suggested_words
    
    async def _get_exercise(self, exercise_id: int) -> LessonExercise:
        """Get exercise by ID."""
        result = await self.session.execute(
            select(LessonExercise).where(LessonExercise.id == exercise_id)
        )
        exercise = result.scalar_one_or_none()
        if not exercise:
            raise AppException(
                status_code=404,
                code="exercise_not_found",
                message="Упражнение не найдено"
            )
        return exercise
    
    async def _get_target_words(self, exercise_id: int) -> List[LessonExerciseWord]:
        """Get target words for exercise with eager loading."""
        from sqlalchemy.orm import selectinload
        
        result = await self.session.execute(
            select(LessonExerciseWord)
            .where(
                LessonExerciseWord.exercise_id == exercise_id,
                LessonExerciseWord.is_target == True
            )
            .options(selectinload(LessonExerciseWord.word))
        )
        return list(result.scalars().all())
    
    def _validate_translation(self, translation: Optional[str]) -> str:
        """Validate and normalize user translation."""
        if translation is None:
            return ""
        
        # NFC normalization
        translation = unicodedata.normalize("NFC", translation)
        
        # Trim
        translation = translation.strip()
        
        # Collapse whitespace
        translation = re.sub(r"\s+", " ", translation)
        
        # Remove control characters
        translation = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", translation)
        
        # Remove <<< and >>> sequences
        translation = re.sub(r"<<<|>>>", "", translation)
        
        # Check length
        if len(translation) < 1 or len(translation) > 500:
            raise AppException(
                status_code=422,
                code="invalid_translation",
                message="Перевод должен быть от 1 до 500 символов"
            )
        
        return translation
    
    def _create_dont_know_evaluations(
        self, target_words: List[LessonExerciseWord]
    ) -> List[WordEvaluation]:
        """Create evaluations for 'don't know' case."""
        evaluations = []
        for tw in target_words:
            evaluations.append(WordEvaluation(
                word_id=tw.word_id,
                lemma=tw.word.lemma,
                pos=tw.word.pos,
                surface_form=tw.surface_form,
                result="incorrect",
                user_fragment=None,
                translations=tw.word.translations
            ))
        return evaluations
    
    async def _call_llm(
        self,
        exercise: LessonExercise,
        target_words: List[LessonExerciseWord],
        user_translation: str,
    ) -> LlmEvaluateResponse:
        """Call LLM to evaluate translation."""
        # Generate random delimiter
        delimiter = f"<<<UT_{secrets.token_hex(4)}>>>"
        
        # Get prompt
        prompt_service = PromptService(self.session)
        system_prompt = await prompt_service.get_prompt("evaluate_translation")
        
        # Build user message
        words_info = []
        for tw in target_words:
            words_info.append(f"- {tw.word.lemma} ({tw.word.pos}): {tw.surface_form}")
        
        user_message = f"""Исходное предложение: {exercise.target_sentence}
Эталонный перевод: {exercise.reference_translation}

Целевые слова для оценки (оцени ТОЛЬКО эти слова):
{chr(10).join(words_info)}

Перевод ученика:
{delimiter}{user_translation}{delimiter}

Оцени каждое целевое слово из списка выше. Предоставь ровно {len(target_words)} оценок (одну на каждое слово)."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Prepare expected words for adapter
        expected_words = [
            {"lemma": tw.word.lemma, "pos": tw.word.pos}
            for tw in target_words
        ]
        
        # === ПОДРОБНОЕ ЛОГИРОВАНИЕ ===
        logger.info("=" * 80)
        logger.info("LLM EVALUATION REQUEST")
        logger.info("=" * 80)
        logger.info(f"Exercise ID: {exercise.id}")
        logger.info(f"Target sentence: {exercise.target_sentence}")
        logger.info(f"Reference translation: {exercise.reference_translation}")
        logger.info(f"User translation: {user_translation}")
        logger.info(f"Target words count: {len(target_words)}")
        logger.info("Target words:")
        for i, tw in enumerate(target_words, 1):
            logger.info(f"  {i}. {tw.word.lemma} ({tw.word.pos}): {tw.surface_form}")
        logger.info("=" * 80)
        
        # Call LLM
        start_time = __import__("time").time()
        try:
            # Get raw JSON response (with 1 retry on parse error)
            raw_response = await gigachat_client.chat_json_raw(
                messages=messages,
                temperature=settings.EVAL_TEMPERATURE,
                max_tokens=1000,
                timeout=10.0,
                max_retries=1
            )
            
            # === ЛОГИРОВАНИЕ СЫРОГО ОТВЕТА LLM ===
            logger.info("=" * 80)
            logger.info("LLM RAW RESPONSE")
            logger.info("=" * 80)
            import json
            logger.info(json.dumps(raw_response, indent=2, ensure_ascii=False))
            logger.info("=" * 80)
            
            # Adapt response to expected format
            from app.services.llm_evaluation_adapter import adapt_evaluation_response
            
            try:
                response = adapt_evaluation_response(raw_response, expected_words)
                
                # === ЛОГИРОВАНИЕ АДАПТИРОВАННОГО ОТВЕТА ===
                logger.info("=" * 80)
                logger.info("ADAPTED RESPONSE")
                logger.info("=" * 80)
                logger.info(f"Evaluations count: {len(response.evaluations)}")
                for i, eval in enumerate(response.evaluations, 1):
                    logger.info(f"  {i}. {eval.lemma} ({eval.pos}): {eval.result}")
                    logger.info(f"     user_fragment: {eval.user_fragment}")
                logger.info("=" * 80)
                
                logger.info(f"Evaluation response adapted successfully")
            except ValueError as e:
                logger.warning(f"Failed to adapt evaluation response: {e}")
                logger.warning(f"Raw response was: {json.dumps(raw_response, indent=2, ensure_ascii=False)}")
                raise LlmInvalidResponse(f"Failed to adapt evaluation response: {e}")
            
            # Log successful call
            latency_ms = int(( __import__("time").time() - start_time) * 1000)
            llm_logger = LlmLogger(self.session)
            await llm_logger.log_call(
                purpose="evaluate",
                user_id=self.user_id,
                exercise_id=exercise.id,
                request_data={"messages": messages},
                response_data=response.model_dump(),
                status="ok",
                latency_ms=latency_ms
            )
            
            return response
            
        except LlmError as e:
            # Log failed call
            latency_ms = int((__import__("time").time() - start_time) * 1000)
            llm_logger = LlmLogger(self.session)
            await llm_logger.log_call(
                purpose="evaluate",
                user_id=self.user_id,
                exercise_id=exercise.id,
                request_data={"messages": messages},
                response_data=None,
                status="http_error",
                latency_ms=latency_ms
            )
            raise
    
    async def _process_llm_evaluations(
        self,
        llm_evaluations: List[LlmWordEvaluation],
        target_words: List[LessonExerciseWord],
        user_translation: str,
    ) -> List[WordEvaluation]:
        """Process and validate LLM evaluations."""
        logger.info("=" * 80)
        logger.info("PROCESSING LLM EVALUATIONS")
        logger.info("=" * 80)
        logger.info(f"LLM returned {len(llm_evaluations)} evaluations")
        logger.info(f"Expected {len(target_words)} target words")
        
        # Build lookup maps
        target_map = {tw.word_id: tw for tw in target_words}
        lemma_pos_map = {(tw.word.lemma, tw.word.pos): tw for tw in target_words}
        
        # Build lemma-only map for fallback matching
        lemma_map = {tw.word.lemma: tw for tw in target_words}
        
        logger.info(f"Target words map:")
        for word_id, tw in target_map.items():
            logger.info(f"  word_id={word_id}: {tw.word.lemma} ({tw.word.pos})")
        
        evaluations = []
        
        for idx, llm_eval in enumerate(llm_evaluations, 1):
            logger.info(f"Processing LLM evaluation {idx}: {llm_eval.lemma} ({llm_eval.pos}) = {llm_eval.result}")
            
            # Try to find matching target word
            # First try exact match with lemma and pos
            tw = lemma_pos_map.get((llm_eval.lemma, llm_eval.pos))
            
            if tw:
                logger.info(f"  ✓ Exact match found: word_id={tw.word_id}")
            
            # If not found and pos is "unknown", try lemma-only match
            if not tw and (llm_eval.pos == "unknown" or not llm_eval.pos):
                tw = lemma_map.get(llm_eval.lemma)
                if tw:
                    # Use the actual pos from target word
                    llm_eval.pos = tw.word.pos
                    logger.info(f"  ✓ Lemma-only match found: word_id={tw.word_id}, using pos '{tw.word.pos}'")
            
            if not tw:
                logger.warning(f"  ✗ LLM returned evaluation for unknown word: {llm_eval.lemma} ({llm_eval.pos})")
                continue
            
            # Validate user_fragment
            user_fragment = llm_eval.user_fragment
            if user_fragment:
                # Check if it's a substring of user translation (case-insensitive, whitespace-normalized)
                normalized_translation = re.sub(r"\s+", " ", user_translation.lower())
                normalized_fragment = re.sub(r"\s+", " ", user_fragment.lower())
                
                if normalized_fragment not in normalized_translation:
                    logger.warning(f"user_fragment '{user_fragment}' not found in translation, setting to null")
                    user_fragment = None
            
            evaluations.append(WordEvaluation(
                word_id=tw.word_id,
                lemma=tw.word.lemma,
                pos=tw.word.pos,
                surface_form=tw.surface_form,
                result=llm_eval.result,
                user_fragment=user_fragment,
                translations=tw.word.translations
            ))
        
        # Check if all target words are covered
        covered_word_ids = {e.word_id for e in evaluations}
        missing_word_ids = set(target_map.keys()) - covered_word_ids
        
        logger.info(f"Coverage check: {len(covered_word_ids)} covered, {len(missing_word_ids)} missing")
        
        if missing_word_ids:
            logger.warning(f"LLM didn't evaluate all target words. Missing word_ids: {missing_word_ids}")
            # Add missing words as incorrect
            for word_id in missing_word_ids:
                tw = target_map[word_id]
                logger.info(f"  Adding missing word as incorrect: {tw.word.lemma} ({tw.word.pos})")
                evaluations.append(WordEvaluation(
                    word_id=tw.word_id,
                    lemma=tw.word.lemma,
                    pos=tw.word.pos,
                    surface_form=tw.surface_form,
                    result="incorrect",
                    user_fragment=None,
                    translations=tw.word.translations
                ))
        
        logger.info("=" * 80)
        logger.info(f"FINAL RESULT: {len(evaluations)} evaluations")
        for idx, eval in enumerate(evaluations, 1):
            logger.info(f"  {idx}. word_id={eval.word_id}: {eval.lemma} ({eval.pos}) = {eval.result}")
            logger.info(f"     surface_form: {eval.surface_form}")
            logger.info(f"     user_fragment: {eval.user_fragment}")
        logger.info("=" * 80)
        
        return evaluations
    
    async def _process_suggested_words(
        self,
        llm_suggestions: List[LlmSuggestedWord],
        target_words: List[LessonExerciseWord],
    ) -> List[SuggestedWord]:
        """Process and validate suggested words."""
        # Build exclusion set
        target_word_ids = {tw.word_id for tw in target_words}
        
        suggestions = []
        
        for llm_sugg in llm_suggestions[:3]:  # Max 3 suggestions
            # Normalize
            lemma = llm_sugg.lemma.strip().lower()
            lemma = unicodedata.normalize("NFC", lemma)
            pos = llm_sugg.pos
            
            # Calculate lemma_key
            lemma_key = re.sub(r"\s+", " ", lemma)
            
            # Find word in database
            result = await self.session.execute(
                select(Word).where(
                    Word.lemma_key == lemma_key,
                    Word.pos == pos
                )
            )
            word = result.scalar_one_or_none()
            
            if not word:
                logger.debug(f"Suggested word not found: {lemma} ({pos})")
                continue
            
            # Check if already in target words
            if word.id in target_word_ids:
                logger.debug(f"Suggested word is already a target: {word.id}")
                continue
            
            # Check if already in user_words
            from app.models.user_word import UserWord
            result = await self.session.execute(
                select(UserWord).where(
                    UserWord.user_id == self.user_id,
                    UserWord.word_id == word.id
                )
            )
            if result.scalar_one_or_none():
                logger.debug(f"Suggested word already in user_words: {word.id}")
                continue
            
            suggestions.append(SuggestedWord(
                word_id=word.id,
                lemma=word.lemma,
                pos=word.pos,
                translations=word.translations
            ))
        
        return suggestions
