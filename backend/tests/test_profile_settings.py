"""Tests for profile and settings services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import AppException
from app.models import Dictionary, Lesson, LearningProfile, User, UserWord
from app.services.dictionaries_service import DictionariesService
from app.services.learning_profile_service import LearningProfileService
from app.services.profile_stats_service import ProfileStatsService
from app.services.timezone_service import TimezoneService


class TestProfileStatsService:
    """Tests for ProfileStatsService."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self):
        """Should return zeros when no data."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1
        user.timezone = "UTC"

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile
        session.execute.return_value.scalar.return_value = 0
        session.execute.return_value.all.return_value = []

        service = ProfileStatsService(session, user)
        result = await service.get_stats()

        assert result.current_streak == 0
        assert result.longest_streak == 0
        assert result.words_active == 0
        assert result.words_mastered == 0
        assert result.words_ignored == 0
        assert result.lessons_completed == 0


class TestTimezoneService:
    """Tests for TimezoneService."""

    @pytest.mark.asyncio
    async def test_change_timezone_success(self):
        """Should change timezone successfully."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1
        user.timezone = "UTC"
        user.timezone_changed_at = None

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile
        session.execute.return_value.scalar.return_value = 0
        session.execute.return_value.all.return_value = []
        session.commit = AsyncMock()

        service = TimezoneService(session, user)
        result = await service.change_timezone("Europe/Moscow")

        assert user.timezone == "Europe/Moscow"
        assert user.timezone_changed_at is not None
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_timezone_same(self):
        """Should return success if timezone is the same."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1
        user.timezone = "UTC"

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile
        session.execute.return_value.scalar.return_value = 0
        session.execute.return_value.all.return_value = []

        service = TimezoneService(session, user)
        result = await service.change_timezone("UTC")

        assert "today" in result

    @pytest.mark.asyncio
    async def test_change_timezone_too_soon(self):
        """Should raise error if change is too soon."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1
        user.timezone = "UTC"
        user.timezone_changed_at = datetime.now(timezone.utc) - timedelta(days=3)

        service = TimezoneService(session, user)

        with pytest.raises(AppException) as exc_info:
            await service.change_timezone("Europe/Moscow")

        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "timezone_change_too_soon"

    @pytest.mark.asyncio
    async def test_change_timezone_invalid(self):
        """Should raise error for invalid timezone."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1
        user.timezone = "UTC"

        service = TimezoneService(session, user)

        with pytest.raises(AppException) as exc_info:
            await service.change_timezone("Invalid/Timezone")

        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "invalid_timezone"


class TestLearningProfileService:
    """Tests for LearningProfileService."""

    @pytest.mark.asyncio
    async def test_get_profile(self):
        """Should return learning profile."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1
        profile.level = "A1"
        profile.dictionary_id = 1
        profile.daily_lesson_limit = 5

        # Mock dictionary
        dictionary = MagicMock(spec=Dictionary)
        dictionary.name = "General"

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile
        session.execute.return_value.scalar_one.return_value = dictionary
        session.execute.return_value.scalar.return_value = 0

        service = LearningProfileService(session, user)
        result = await service.get_profile()

        assert result.level == "A1"
        assert result.dictionary_id == 1
        assert result.daily_lesson_limit == 5

    @pytest.mark.asyncio
    async def test_update_profile_level(self):
        """Should update level."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1
        profile.level = "A1"
        profile.dictionary_id = 1
        profile.daily_lesson_limit = 5

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile
        session.commit = AsyncMock()

        service = LearningProfileService(session, user)
        result = await service.update_profile(level="A2")

        assert profile.level == "A2"
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_invalid_level(self):
        """Should raise error for invalid level."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile

        service = LearningProfileService(session, user)

        with pytest.raises(AppException) as exc_info:
            await service.update_profile(level="C1")

        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "invalid_level"

    @pytest.mark.asyncio
    async def test_update_profile_invalid_limit(self):
        """Should raise error for invalid daily limit."""
        session = AsyncMock()
        user = MagicMock(spec=User)
        user.id = 1

        # Mock learning profile
        profile = MagicMock(spec=LearningProfile)
        profile.id = 1

        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none.return_value = profile

        service = LearningProfileService(session, user)

        with pytest.raises(AppException) as exc_info:
            await service.update_profile(daily_lesson_limit=100)

        assert exc_info.value.status_code == 422
        assert exc_info.value.code == "invalid_daily_limit"


class TestDictionariesService:
    """Tests for DictionariesService."""

    @pytest.mark.asyncio
    async def test_get_dictionaries(self):
        """Should return list of dictionaries."""
        session = AsyncMock()

        # Mock dictionary rows
        row1 = MagicMock()
        row1.id = 1
        row1.code = "general"
        row1.name = "General"
        row1.description = "General dictionary"
        row1.is_general = True
        row1.words_total = 100

        row2 = MagicMock()
        row2.id = 2
        row2.code = "it"
        row2.name = "IT"
        row2.description = "IT dictionary"
        row2.is_general = False
        row2.words_total = 50

        session.execute = AsyncMock()
        session.execute.return_value.all.return_value = [row1, row2]

        service = DictionariesService(session)
        result = await service.get_dictionaries()

        assert len(result.dictionaries) == 2
        assert result.dictionaries[0].name == "General"
        assert result.dictionaries[1].name == "IT"
