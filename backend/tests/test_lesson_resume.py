"""Tests for lesson resume and summary services."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import AppException
from app.models.lesson import Lesson
from app.services.lesson_resume_service import LessonResumeService
from app.services.lesson_summary_service import LessonSummaryService


class TestLessonResumeService:
    """Tests for LessonResumeService."""

    @pytest.mark.asyncio
    async def test_get_current_exercise_success(self):
        """Should return current pending exercise."""
        session = AsyncMock()
        user_id = 1
        
        # Mock lesson
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.status = "in_progress"
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = user_id
        
        # Mock exercise
        exercise = MagicMock()
        exercise.id = 10
        exercise.target_sentence = "Test sentence"
        exercise.order_index = 0
        
        # Mock query results
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.side_effect = [
            lesson,  # get_lesson
            exercise,  # get_first_pending_exercise
        ]
        session.execute.return_value.scalar.side_effect = [
            5,  # count_exercises
            2,  # count_evaluated_exercises
        ]
        
        service = LessonResumeService(session, user_id)
        result = await service.get_current_exercise(1)
        
        assert result.exercise_id == 10
        assert result.sentence == "Test sentence"
        assert result.order_index == 0
        assert result.exercises_done == 2
        assert result.exercises_total == 5

    @pytest.mark.asyncio
    async def test_get_current_exercise_lesson_completed(self):
        """Should raise error if lesson is completed."""
        session = AsyncMock()
        user_id = 1
        
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.status = "completed"
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = user_id
        
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = lesson
        
        service = LessonResumeService(session, user_id)
        
        with pytest.raises(AppException) as exc_info:
            await service.get_current_exercise(1)
        
        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "lesson_not_active"

    @pytest.mark.asyncio
    async def test_abandon_lesson_success(self):
        """Should mark lesson as abandoned."""
        session = AsyncMock()
        user_id = 1
        
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.status = "in_progress"
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = user_id
        
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = lesson
        session.commit = AsyncMock()
        
        service = LessonResumeService(session, user_id)
        result = await service.abandon_lesson(1)
        
        assert result == "Урок отменён"
        assert lesson.status == "abandoned"
        assert lesson.abandoned_at is not None
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_abandon_lesson_already_abandoned(self):
        """Should return success if already abandoned (idempotent)."""
        session = AsyncMock()
        user_id = 1
        
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.status = "abandoned"
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = user_id
        
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = lesson
        
        service = LessonResumeService(session, user_id)
        result = await service.abandon_lesson(1)
        
        assert result == "Урок уже отменён"

    @pytest.mark.asyncio
    async def test_abandon_lesson_completed(self):
        """Should raise error if lesson is completed."""
        session = AsyncMock()
        user_id = 1
        
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.status = "completed"
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = user_id
        
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = lesson
        
        service = LessonResumeService(session, user_id)
        
        with pytest.raises(AppException) as exc_info:
            await service.abandon_lesson(1)
        
        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "lesson_not_active"

    @pytest.mark.asyncio
    async def test_abandon_lesson_wrong_user(self):
        """Should raise error if lesson belongs to different user."""
        session = AsyncMock()
        user_id = 1
        
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.status = "in_progress"
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = 2  # Different user
        
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = lesson
        
        service = LessonResumeService(session, user_id)
        
        with pytest.raises(AppException) as exc_info:
            await service.abandon_lesson(1)
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.code == "forbidden"


class TestLessonSummaryService:
    """Tests for LessonSummaryService."""

    @pytest.mark.asyncio
    async def test_get_summary_success(self):
        """Should return lesson summary with statistics."""
        session = AsyncMock()
        user = MagicMock()
        user.id = 1
        user.timezone = "UTC"
        
        # Mock lesson
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.lesson_number = 5
        lesson.status = "completed"
        lesson.completed_local_date = datetime.now(timezone.utc).date()
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = user.id
        
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = lesson
        session.execute.return_value.scalar.side_effect = [
            10,  # words_total
            3,   # new_words
            5,   # correct
            2,   # typo
            3,   # incorrect
            1,   # suggestions_added
            0,   # other_lessons_today
        ]
        session.execute.return_value.all.return_value = []
        
        service = LessonSummaryService(session, user)
        result = await service.get_summary(1)
        
        assert result.lesson_number == 5
        assert result.words_total == 10
        assert result.new_words == 3
        assert result.reviewed == 7
        assert result.correct == 5
        assert result.typo == 2
        assert result.incorrect == 3
        assert result.without_errors == 7
        assert result.suggestions_added == 1

    @pytest.mark.asyncio
    async def test_get_summary_not_completed(self):
        """Should raise error if lesson is not completed."""
        session = AsyncMock()
        user = MagicMock()
        user.id = 1
        
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.status = "in_progress"
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = user.id
        
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = lesson
        
        service = LessonSummaryService(session, user)
        
        with pytest.raises(AppException) as exc_info:
            await service.get_summary(1)
        
        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "lesson_not_completed"

    @pytest.mark.asyncio
    async def test_get_summary_wrong_user(self):
        """Should raise error if lesson belongs to different user."""
        session = AsyncMock()
        user = MagicMock()
        user.id = 1
        
        lesson = MagicMock(spec=Lesson)
        lesson.id = 1
        lesson.status = "completed"
        lesson.learning_profile = MagicMock()
        lesson.learning_profile.user_id = 2  # Different user
        
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = lesson
        
        service = LessonSummaryService(session, user)
        
        with pytest.raises(AppException) as exc_info:
            await service.get_summary(1)
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.code == "forbidden"
