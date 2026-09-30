"""Tests for vocabulary service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import AppException
from app.models import LearningProfile, User, UserWord, Word
from app.services.vocabulary_service import VocabularyService


class TestVocabularyService:
    """Tests for VocabularyService."""

    @pytest.mark.asyncio
    async def test_get_vocabulary_list_empty(self):
        """Should return empty list when no words."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1
        profile.last_lesson_number = 5

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile
        session.execute.return_value.scalar.return_value = 0
        session.execute.return_value.all.return_value = []

        service = VocabularyService(session, user)
        result = await service.get_vocabulary_list()

        assert result.words == []
        assert result.total == 0
        assert result.page == 1
        assert result.page_size == 20

    @pytest.mark.asyncio
    async def test_get_vocabulary_list_with_words(self):
        """Should return list of words."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1
        profile.last_lesson_number = 5

        # Mock word data
        user_word = MagicMock(spec=UserWord)
        user_word.status = "active"
        user_word.stage = 2
        user_word.due_lesson_number = 8

        word = MagicMock(spec=Word)
        word.id = 1
        word.lemma = "run"
        word.pos = "verb"
        word.translations = ["бегать"]

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile
        session.execute.return_value.scalar.return_value = 1
        session.execute.return_value.all.return_value = [(user_word, word)]

        service = VocabularyService(session, user)
        result = await service.get_vocabulary_list()

        assert len(result.words) == 1
        assert result.words[0].word_id == 1
        assert result.words[0].lemma == "run"
        assert result.words[0].status == "active"
        assert result.words[0].stage == 2
        assert result.words[0].due_in_lessons == 3  # 8 - 5

    @pytest.mark.asyncio
    async def test_get_word_detail_not_found(self):
        """Should raise 404 if word not in user's vocabulary."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile
        session.execute.return_value.first.return_value = None

        service = VocabularyService(session, user)

        with pytest.raises(AppException) as exc_info:
            await service.get_word_detail(999)

        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "word_not_found"

    @pytest.mark.asyncio
    async def test_change_status_active_to_ignored(self):
        """Should change status from active to ignored."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1
        profile.last_lesson_number = 5

        # Mock user_word
        user_word = MagicMock(spec=UserWord)
        user_word.status = "active"
        user_word.due_lesson_number = 8

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.side_effect = [
            profile,
            user_word,
        ]
        session.commit = AsyncMock()

        service = VocabularyService(session, user)
        result = await service.change_status(1, "ignored")

        assert "изменён" in result.lower()
        assert user_word.status == "ignored"
        assert user_word.due_lesson_number is None
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_status_ignored_to_active(self):
        """Should change status from ignored to active."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1
        profile.last_lesson_number = 5

        # Mock user_word
        user_word = MagicMock(spec=UserWord)
        user_word.status = "ignored"
        user_word.stage = 0

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.side_effect = [
            profile,
            user_word,
        ]
        session.commit = AsyncMock()

        service = VocabularyService(session, user)
        result = await service.change_status(1, "active")

        assert "изменён" in result.lower()
        assert user_word.status == "active"
        assert user_word.stage == 0
        assert user_word.due_lesson_number == 6  # last_lesson_number + 1
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_status_idempotent(self):
        """Should return success if status is the same."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        # Mock user_word
        user_word = MagicMock(spec=UserWord)
        user_word.status = "active"

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.side_effect = [
            profile,
            user_word,
        ]

        service = VocabularyService(session, user)
        result = await service.change_status(1, "active")

        assert "не изменён" in result.lower()

    @pytest.mark.asyncio
    async def test_change_status_invalid_transition(self):
        """Should raise 409 for invalid transition."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        # Mock user_word
        user_word = MagicMock(spec=UserWord)
        user_word.status = "mastered"

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.side_effect = [
            profile,
            user_word,
        ]

        service = VocabularyService(session, user)

        with pytest.raises(AppException) as exc_info:
            await service.change_status(1, "ignored")

        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "invalid_transition"

    @pytest.mark.asyncio
    async def test_change_status_word_not_found(self):
        """Should raise 404 if word not in user's vocabulary."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.side_effect = [
            profile,
            None,  # user_word not found
        ]

        service = VocabularyService(session, user)

        with pytest.raises(AppException) as exc_info:
            await service.change_status(999, "ignored")

        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "word_not_found"
