"""Lesson start service - creates lessons with LLM-generated sentences."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AppException
from app.llm import gigachat_client
from app.llm.exceptions import LlmError, LlmInvalidResponse, LlmUnavailable
from app.models.lesson import Lesson
from app.models.lesson_exercise import LessonExercise
from app.models.lesson_exercise_word import LessonExerciseWord
from app.models.learning_profile import LearningProfile
from app.models.user import User
from app.models.user_word import UserWord
from app.models.word import Word
from app.schemas.lesson_start import (
    CurrentExercise,
    LessonStartResponse,
    LlmGenerateResponse,
)
from app.schemas.lesson import ReadyState
from app.services.lesson_preview_service import LessonPreviewService
from app.services.llm_logger import LlmLogger
from app.services.prompt_service import PromptService
from app.services.sentence_validator import validate_all_groups
from app.services.word_clustering import cluster_words

logger = logging.getLogger(__name__)


class LessonStartService:
    """Service for starting lessons with LLM-generated sentences."""
    
    def __init__(self, session: AsyncSession, user: User):
        self.session = session
        self.user = user
        self.N = None  # Will be set from profile in start_lesson()
    
    async def start_lesson(
        self,
        word_ids: List[int],
        idempotency_key: Optional[str] = None,
    ) -> LessonStartResponse:
        """
        Start a new lesson with LLM-generated sentences.
        
        Args:
            word_ids: Word IDs from preview
            idempotency_key: Optional idempotency key
        
        Returns:
            LessonStartResponse with lesson info
        
        Raises:
            AppException: On various error conditions
        """
        # Pre-checks
        await self._pre_checks()
        
        # Get profile
        profile = await self._get_profile()
        
        # Set words per lesson from profile
        self.N = profile.words_per_lesson
        
        # Check idempotency
        if idempotency_key:
            existing = await self._check_idempotency(profile.id, idempotency_key)
            if existing:
                return existing
        
        # Acquire advisory lock
        async with self._advisory_lock(profile.id):
            # Re-verify after lock
            await self._pre_checks()
            
            # Get preview and verify word composition
            preview_service = LessonPreviewService(self.session, self.user)
            preview = await preview_service.preview()
            
            if preview["state"] != "ready":
                raise AppException(
                    status_code=409,
                    code="preview_outdated",
                    message="Preview state changed",
                    details={"preview": preview}
                )
            
            # Verify word composition
            preview_word_ids = [w["word_id"] for w in preview["due_words"]] + \
                              [w["word_id"] for w in preview["new_words"]]
            
            if set(word_ids) != set(preview_word_ids):
                raise AppException(
                    status_code=409,
                    code="preview_outdated",
                    message="Word composition doesn't match preview",
                    details={"preview": preview}
                )
            
            # Cluster words into groups
            seed = self._calculate_seed(profile.id, preview["lesson_number"])
            groups = cluster_words(word_ids, seed)
            
            # Get avoid sentences
            avoid_sentences = await self._get_avoid_sentences(word_ids)
            
            # Generate sentences via LLM
            start_time = time.time()
            try:
                generated_groups = await self._generate_sentences(
                    profile=profile,
                    groups=groups,
                    word_ids=word_ids,
                    avoid_sentences=avoid_sentences,
                    timeout=45.0,
                )
            except LlmError as e:
                logger.error(f"LLM error during lesson generation: {e}")
                raise AppException(
                    status_code=503,
                    code="llm_unavailable",
                    message="Failed to generate sentences",
                    details={"error": str(e)}
                )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log LLM call
            llm_logger = LlmLogger(self.session)
            await llm_logger.log_call(
                purpose="generate",
                user_id=self.user.id,
                request_data={"groups": len(groups), "words": len(word_ids)},
                response_data={"groups_generated": len(generated_groups)},
                status="ok",
                latency_ms=latency_ms,
            )
            
            # Get word info for matching
            word_info = await self._get_word_info(word_ids)
            
            # Create lesson in transaction
            lesson = await self._create_lesson_transaction(
                profile=profile,
                lesson_number=preview["lesson_number"],
                groups=groups,
                generated_groups=generated_groups,
                preview=preview,
                word_ids=word_ids,
                word_info=word_info,
                idempotency_key=idempotency_key,
            )
            
            # Get first exercise
            first_exercise = await self._get_first_exercise(lesson.id)
            
            return LessonStartResponse(
                lesson_id=lesson.id,
                lesson_number=lesson.lesson_number,
                exercises_total=len(groups),
                current_exercise=CurrentExercise(
                    exercise_id=first_exercise.id,
                    order_index=first_exercise.order_index,
                    sentence=first_exercise.target_sentence,
                    words=[
                        {
                            "word_id": w.word_id,
                            "lemma": w.word.lemma,
                            "pos": w.word.pos,
                            "surface_form": w.surface_form,
                            "is_new": w.is_new,
                        }
                        for w in first_exercise.exercise_words
                        if w.is_target
                    ],
                ),
            )
    
    async def _pre_checks(self):
        """Perform pre-checks before starting lesson."""
        # Check onboarding
        if not self.user.is_onboarded:
            raise AppException(
                status_code=403,
                code="onboarding_required",
                message="Onboarding required"
            )
        
        # Get profile
        profile = await self._get_profile()
        
        # Check for in-progress lesson
        result = await self.session.execute(
            select(Lesson).where(
                Lesson.learning_profile_id == profile.id,
                Lesson.status == "in_progress"
            )
        )
        if result.scalar_one_or_none():
            raise AppException(
                status_code=409,
                code="resume_available",
                message="Lesson already in progress"
            )
        
        # Check daily limit
        user_tz = ZoneInfo(self.user.timezone)
        today = datetime.now(timezone.utc).astimezone(user_tz).date()
        
        result = await self.session.execute(
            select(Lesson).where(
                Lesson.learning_profile_id == profile.id,
                Lesson.started_local_date == today
            )
        )
        lessons_today = len(result.scalars().all())
        
        if lessons_today >= profile.daily_lesson_limit:
            raise AppException(
                status_code=409,
                code="limit_reached",
                message="Daily lesson limit reached"
            )
    
    async def _get_profile(self) -> LearningProfile:
        """Get user's learning profile."""
        result = await self.session.execute(
            select(LearningProfile).where(LearningProfile.user_id == self.user.id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise AppException(
                status_code=403,
                code="profile_not_found",
                message="Learning profile not found"
            )
        return profile
    
    async def _check_idempotency(
        self, profile_id: int, idempotency_key: str
    ) -> Optional[LessonStartResponse]:
        """Check if lesson already created with this idempotency key."""
        # For now, just check if there's an in-progress lesson
        # In production, you'd store idempotency keys in a separate table
        result = await self.session.execute(
            select(Lesson).where(
                Lesson.learning_profile_id == profile_id,
                Lesson.status == "in_progress"
            )
        )
        lesson = result.scalar_one_or_none()
        
        if lesson:
            first_exercise = await self._get_first_exercise(lesson.id)
            return LessonStartResponse(
                lesson_id=lesson.id,
                lesson_number=lesson.lesson_number,
                exercises_total=await self._count_exercises(lesson.id),
                current_exercise=CurrentExercise(
                    exercise_id=first_exercise.id,
                    order_index=first_exercise.order_index,
                    sentence=first_exercise.target_sentence,
                    words=[
                        {
                            "word_id": w.word_id,
                            "lemma": w.word.lemma,
                            "pos": w.word.pos,
                            "surface_form": w.surface_form,
                            "is_new": w.is_new,
                        }
                        for w in first_exercise.exercise_words
                        if w.is_target
                    ],
                ),
            )
        
        return None
    
    def _advisory_lock(self, profile_id: int):
        """Context manager for advisory lock."""
        class AdvisoryLockContext:
            def __init__(self, session, profile_id):
                self.session = session
                self.profile_id = profile_id
                self.locked = False
            
            async def __aenter__(self):
                # Try to acquire lock
                result = await self.session.execute(
                    text(f"SELECT pg_try_advisory_xact_lock(:id)"),
                    {"id": self.profile_id}
                )
                self.locked = result.scalar_one()
                
                if not self.locked:
                    raise AppException(
                        status_code=409,
                        code="start_in_progress",
                        message="Lesson start already in progress"
                    )
                
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                # Lock is automatically released at transaction end
                pass
        
        return AdvisoryLockContext(self.session, profile_id)
    
    def _calculate_seed(self, profile_id: int, lesson_number: int) -> str:
        """Calculate deterministic seed for lesson."""
        import hashlib
        data = f"{profile_id}:{lesson_number}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def _get_avoid_sentences(self, word_ids: List[int]) -> List[str]:
        """Get recent sentences containing these words."""
        # Get last 2 sentences per word from completed exercises
        result = await self.session.execute(
            text("""
                SELECT DISTINCT le.target_sentence
                FROM lesson_exercise_words lew
                JOIN lesson_exercises le ON lew.exercise_id = le.id
                JOIN lessons l ON le.lesson_id = l.id
                WHERE lew.word_id = ANY(:word_ids)
                  AND l.status = 'completed'
                ORDER BY le.target_sentence
                LIMIT 4
            """),
            {"word_ids": word_ids}
        )
        
        return [row[0] for row in result.all()]
    
    async def _generate_sentences(
        self,
        profile: LearningProfile,
        groups: List[List[int]],
        word_ids: List[int],
        avoid_sentences: List[str],
        timeout: float,
    ) -> List[dict]:
        """Generate sentences via LLM with validation and retries."""
        logger.info(f"Starting sentence generation for {len(groups)} groups, timeout={timeout}s")
        
        # Track start time for timeout
        start_time = time.time()
        
        # Get word info
        word_info = await self._get_word_info(word_ids)
        logger.debug(f"Retrieved word info for {len(word_ids)} words")
        
        # Get prompt
        prompt_service = PromptService(self.session)
        template = await prompt_service.get_prompt("generate_sentences")
        logger.debug(f"Loaded prompt template: {template[:100]}...")
        
        # Prepare groups for LLM
        llm_groups = []
        for idx, group in enumerate(groups):
            group_words = [word_info[wid] for wid in group]
            llm_groups.append({
                "group_index": idx,
                "words": group_words,
            })
        
        # Format prompt
        system_prompt = prompt_service.format_prompt(
            template,
            level=profile.level,
            count=len(groups),
            word="multiple words"  # Placeholder
        )
        
        user_prompt = f"""Generate {len(groups)} English sentences, one for each word group.

CRITICAL: Each sentence MUST contain ALL the words from its group. Do not skip any words.

Groups:
"""
        for group_data in llm_groups:
            words_str = ", ".join([f"{w['lemma']} ({w['pos']})" for w in group_data["words"]])
            user_prompt += f"Group {group_data['group_index']}: {words_str} (ALL these words must appear in the sentence)\n"
        
        if avoid_sentences:
            user_prompt += f"\nAvoid these sentences:\n" + "\n".join(avoid_sentences[:4])
        
        user_prompt += "\n\nReturn JSON with 'groups' array. Remember: every word in each group must be used in the corresponding sentence."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        logger.info(f"Prepared messages for LLM: system={len(system_prompt)} chars, user={len(user_prompt)} chars")
        
        # Call LLM with retries
        max_retries = 2
        valid_groups = []
        invalid_group_indices = list(range(len(groups)))
        
        for attempt in range(max_retries + 1):
            if not invalid_group_indices:
                break
            
            # Check timeout - FIXED: compare elapsed time with timeout
            elapsed = time.time() - start_time
            logger.debug(f"Attempt {attempt + 1}/{max_retries + 1}, elapsed={elapsed:.2f}s, timeout={timeout}s")
            
            if elapsed > timeout:
                logger.error(f"Timeout exceeded: {elapsed:.2f}s > {timeout}s")
                raise LlmUnavailable(f"Timeout exceeded: {elapsed:.2f}s > {timeout}s")
            
            try:
                logger.info(f"Calling GigaChat API (attempt {attempt + 1})")
                
                # Get raw JSON response without validation (single attempt, no retries)
                raw_response = await gigachat_client.chat_json_raw(
                    messages=messages,
                    temperature=settings.GEN_TEMPERATURE,
                    max_tokens=2000,
                    timeout=min(timeout - elapsed, 25.0),
                    max_retries=0,
                )
                logger.info(f"LLM raw response received")
                
                # Adapt response to expected format
                from app.services.llm_response_adapter import adapt_llm_response
                
                # Prepare expected groups format for adapter
                expected_groups_for_adapter = []
                for idx in invalid_group_indices:
                    group_words = []
                    for wid in groups[idx]:
                        word_data = word_info[wid]
                        group_words.append({
                            "lemma": word_data["lemma"],
                            "pos": word_data["pos"]
                        })
                    expected_groups_for_adapter.append(group_words)
                
                try:
                    response = adapt_llm_response(raw_response, expected_groups_for_adapter)
                    logger.info(f"LLM response adapted successfully")
                except ValueError as e:
                    logger.warning(f"Failed to adapt LLM response: {e}")
                    if attempt < max_retries:
                        continue
                    raise LlmInvalidResponse(f"Failed to adapt LLM response: {e}")
                
                # Validate groups
                expected_groups = [
                    [(word_info[wid]["lemma"], word_info[wid]["pos"]) for wid in groups[idx]]
                    for idx in invalid_group_indices
                ]
                
                logger.debug(f"Validating {len(response.groups)} groups from LLM response")
                
                valid_indices, new_invalid_indices = validate_all_groups(
                    groups=response.groups,
                    expected_groups=expected_groups,
                    avoid_sentences=avoid_sentences,
                )
                
                logger.info(f"Validation result: {len(valid_indices)} valid, {len(new_invalid_indices)} invalid")
                
                # Collect valid groups
                for idx in valid_indices:
                    valid_groups.append(response.groups[idx])
                
                # Update invalid indices for next retry
                invalid_group_indices = [invalid_group_indices[i] for i in new_invalid_indices]
                
            except LlmInvalidResponse as e:
                logger.warning(f"LLM returned invalid response: {e}")
                if attempt == max_retries:
                    logger.error(f"Max retries reached, raising LlmInvalidResponse")
                    raise
                logger.info(f"Retrying after invalid response...")
                continue
            except LlmError as e:
                logger.error(f"LLM error on attempt {attempt + 1}: {type(e).__name__}: {e}")
                if attempt == max_retries:
                    raise
                logger.info(f"Retrying after LLM error...")
                continue
        
        if invalid_group_indices:
            logger.error(f"Failed to generate valid sentences for groups: {invalid_group_indices}")
            raise LlmInvalidResponse(f"Failed to generate valid sentences for groups: {invalid_group_indices}")
        
        total_elapsed = time.time() - start_time
        logger.info(f"Sentence generation completed successfully in {total_elapsed:.2f}s, generated {len(valid_groups)} groups")
        
        return [g.model_dump() for g in valid_groups]
    
    async def _get_word_info(self, word_ids: List[int]) -> dict:
        """Get word information for given IDs."""
        result = await self.session.execute(
            select(Word).where(Word.id.in_(word_ids))
        )
        words = result.scalars().all()
        
        word_info = {
            w.id: {
                "word_id": w.id,
                "lemma": w.lemma,
                "pos": w.pos,
                "translations": w.translations,
            }
            for w in words
        }
        
        logger.info(f"Word info for {len(word_ids)} words:")
        for wid, info in word_info.items():
            logger.info(f"  word_id={wid}: {info['lemma']} ({info['pos']})")
        
        return word_info
    
    async def _create_lesson_transaction(
        self,
        profile: LearningProfile,
        lesson_number: int,
        groups: List[List[int]],
        generated_groups: List[dict],
        preview: dict,
        word_ids: List[int],
        word_info: dict,
        idempotency_key: Optional[str],
    ) -> Lesson:
        """Create lesson in a single transaction."""
        # Lock profile row
        result = await self.session.execute(
            select(LearningProfile)
            .where(LearningProfile.id == profile.id)
            .with_for_update()
        )
        profile = result.scalar_one()
        
        # Re-verify conditions
        result = await self.session.execute(
            select(Lesson).where(
                Lesson.learning_profile_id == profile.id,
                Lesson.status == "in_progress"
            )
        )
        if result.scalar_one_or_none():
            raise AppException(
                status_code=409,
                code="resume_available",
                message="Lesson already in progress"
            )
        
        # Verify lesson number
        if profile.last_lesson_number + 1 != lesson_number:
            raise AppException(
                status_code=409,
                code="preview_outdated",
                message="Lesson number changed"
            )
        
        # Re-verify words
        due_word_ids = [w["word_id"] for w in preview["due_words"]]
        new_word_ids = [w["word_id"] for w in preview["new_words"]]
        
        # Check due words still active and due
        for wid in due_word_ids:
            result = await self.session.execute(
                select(UserWord).where(
                    UserWord.learning_profile_id == profile.id,
                    UserWord.word_id == wid,
                    UserWord.status == "active",
                    UserWord.due_lesson_number <= lesson_number,
                )
            )
            if not result.scalar_one_or_none():
                raise AppException(
                    status_code=409,
                    code="preview_outdated",
                    message="Due word no longer valid"
                )
        
        # Check new words not in user_words
        for wid in new_word_ids:
            result = await self.session.execute(
                select(UserWord).where(
                    UserWord.learning_profile_id == profile.id,
                    UserWord.word_id == wid,
                )
            )
            if result.scalar_one_or_none():
                raise AppException(
                    status_code=409,
                    code="preview_outdated",
                    message="New word already in user_words"
                )
        
        # Create new user_words for new words
        user_tz = ZoneInfo(self.user.timezone)
        now_utc = datetime.now(timezone.utc)
        
        for wid in new_word_ids:
            user_word = UserWord(
                learning_profile_id=profile.id,
                word_id=wid,
                status="active",
                stage=0,
                due_lesson_number=lesson_number,
                source="dictionary",
            )
            self.session.add(user_word)
        
        # Update profile
        profile.last_lesson_number = lesson_number
        
        # Create lesson
        lesson = Lesson(
            learning_profile_id=profile.id,
            lesson_number=lesson_number,
            status="in_progress",
            words_per_lesson=self.N,
            started_at=now_utc,
            started_local_date=now_utc.astimezone(user_tz).date(),
        )
        self.session.add(lesson)
        await self.session.flush()
        
        # Create exercises
        for idx, (group, generated) in enumerate(zip(groups, generated_groups)):
            logger.info(f"Creating exercise {idx} with group: {group}")
            logger.info(f"Generated words: {generated['words']}")
            
            exercise = LessonExercise(
                lesson_id=lesson.id,
                order_index=idx,
                target_sentence=generated["sentence"],
                reference_translation=generated["reference_translation"],
                status="pending",
            )
            self.session.add(exercise)
            await self.session.flush()
            
            # Create exercise words - match by lemma and pos
            for word_data in generated["words"]:
                logger.info(f"Matching word: {word_data['lemma']} ({word_data['pos']})")
                
                # Normalize pos (adjective -> adj)
                llm_pos = word_data["pos"]
                if llm_pos == "adjective":
                    llm_pos = "adj"
                elif llm_pos == "adverb":
                    llm_pos = "adv"
                
                # Find matching word_id by comparing lemma and pos
                word_id = None
                for wid in group:
                    if wid in word_info:
                        info = word_info[wid]
                        logger.debug(f"Checking word_id={wid}: {info['lemma']} ({info['pos']}) vs {word_data['lemma']} ({llm_pos})")
                        if info["lemma"] == word_data["lemma"] and info["pos"] == llm_pos:
                            word_id = wid
                            logger.info(f"✓ Matched word_id={wid}")
                            break
                
                if word_id is None:
                    logger.warning(f"✗ Could not match word: {word_data['lemma']} ({word_data['pos']})")
                    logger.warning(f"  Available words in group: {[(wid, word_info[wid]['lemma'], word_info[wid]['pos']) for wid in group if wid in word_info]}")
                    continue
                
                exercise_word = LessonExerciseWord(
                    exercise_id=exercise.id,
                    word_id=word_id,
                    surface_form=word_data["surface_form"],
                    is_target=True,
                    is_new=word_id in new_word_ids,
                )
                self.session.add(exercise_word)
        
        # Create events
        from app.services.events import record_event
        
        await record_event(
            self.session,
            self.user.id,
            "lesson_started",
            {"lesson_id": lesson.id, "lesson_number": lesson_number}
        )
        
        for wid in new_word_ids:
            await record_event(
                self.session,
                self.user.id,
                "new_word_accepted",
                {"word_id": wid}
            )
        
        return lesson
    
    async def _get_first_exercise(self, lesson_id: int) -> LessonExercise:
        """Get first exercise for lesson with eager loading."""
        from sqlalchemy.orm import selectinload
        
        result = await self.session.execute(
            select(LessonExercise)
            .where(LessonExercise.lesson_id == lesson_id)
            .order_by(LessonExercise.order_index)
            .options(
                selectinload(LessonExercise.exercise_words).selectinload(LessonExerciseWord.word)
            )
        )
        return result.scalars().first()
    
    async def _count_exercises(self, lesson_id: int) -> int:
        """Count exercises in lesson."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(LessonExercise.id))
            .where(LessonExercise.lesson_id == lesson_id)
        )
        return result.scalar_one()
