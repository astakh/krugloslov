"""Integration tests for database constraints.

These tests require a running PostgreSQL database.
Set DATABASE_URL environment variable to a test database before running.

Run with: pytest tests/test_constraints.py -v --database-url=postgresql+asyncpg://...
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base


# Skip all tests if no test database URL is provided
pytestmark = pytest.mark.skipif(
    not pytest.importorskip("asyncpg", reason="asyncpg not installed"),
    reason="asyncpg required",
)


def get_test_db_url() -> str | None:
    """Get test database URL from environment or pytest config."""
    import os
    return os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="module")
def event_loop():
    """Create an event loop for the test module."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def engine():
    """Create test engine and tables."""
    db_url = get_test_db_url()
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not set")

    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create a test session."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


class TestUserConstraints:
    """Tests for users table constraints."""

    @pytest.mark.asyncio
    async def test_unique_email_case_insensitive(self, session: AsyncSession):
        """Email must be unique case-insensitively."""
        from app.models.user import User

        user1 = User(email="test@example.com", password_hash="hash1")
        session.add(user1)
        await session.flush()

        user2 = User(email="TEST@EXAMPLE.COM", password_hash="hash2")
        session.add(user2)

        with pytest.raises(IntegrityError):
            await session.flush()


class TestWordConstraints:
    """Tests for words table constraints."""

    @pytest.mark.asyncio
    async def test_unique_lemma_key_pos(self, session: AsyncSession):
        """(lemma_key, pos) must be unique."""
        from app.models.word import Word

        word1 = Word(lemma="test", lemma_key="test", pos="noun", translations=["тест"])
        session.add(word1)
        await session.flush()

        word2 = Word(lemma="test", lemma_key="test", pos="noun", translations=["проверка"])
        session.add(word2)

        with pytest.raises(IntegrityError):
            await session.flush()

    @pytest.mark.asyncio
    async def test_same_lemma_different_pos_allowed(self, session: AsyncSession):
        """Same lemma with different POS should be allowed."""
        from app.models.word import Word

        word1 = Word(lemma="test", lemma_key="test", pos="noun", translations=["тест"])
        word2 = Word(lemma="test", lemma_key="test", pos="verb", translations=["тестировать"])
        session.add_all([word1, word2])
        await session.flush()  # Should not raise

    @pytest.mark.asyncio
    async def test_invalid_pos_rejected(self, session: AsyncSession):
        """Invalid POS value should be rejected by CHECK constraint."""
        from app.models.word import Word

        word = Word(lemma="test", lemma_key="test", pos="invalid", translations=["тест"])
        session.add(word)

        with pytest.raises(IntegrityError):
            await session.flush()

    @pytest.mark.asyncio
    async def test_invalid_level_rejected(self, session: AsyncSession):
        """Invalid level value should be rejected by CHECK constraint."""
        from app.models.word import Word

        word = Word(lemma="test", lemma_key="test", pos="noun", level="X9", translations=["тест"])
        session.add(word)

        with pytest.raises(IntegrityError):
            await session.flush()


class TestDictionaryConstraints:
    """Tests for dictionaries table constraints."""

    @pytest.mark.asyncio
    async def test_only_one_general_dictionary(self, session: AsyncSession):
        """Only one dictionary can have is_general=true."""
        from app.models.dictionary import Dictionary

        dict1 = Dictionary(code="general1", name="General 1", is_general=True)
        session.add(dict1)
        await session.flush()

        dict2 = Dictionary(code="general2", name="General 2", is_general=True)
        session.add(dict2)

        with pytest.raises(IntegrityError):
            await session.flush()

    @pytest.mark.asyncio
    async def test_multiple_non_general_allowed(self, session: AsyncSession):
        """Multiple non-general dictionaries should be allowed."""
        from app.models.dictionary import Dictionary

        dict1 = Dictionary(code="topic1", name="Topic 1", is_general=False)
        dict2 = Dictionary(code="topic2", name="Topic 2", is_general=False)
        session.add_all([dict1, dict2])
        await session.flush()  # Should not raise


class TestUserWordConstraints:
    """Tests for user_words table constraints."""

    @pytest.mark.asyncio
    async def test_unique_profile_word(self, session: AsyncSession):
        """(learning_profile_id, word_id) must be unique."""
        from app.models.user import User
        from app.models.dictionary import Dictionary
        from app.models.learning_profile import LearningProfile
        from app.models.word import Word
        from app.models.user_word import UserWord

        # Setup prerequisites
        user = User(email="uw_test@test.com", password_hash="hash")
        session.add(user)
        await session.flush()

        dictionary = Dictionary(code="uw_dict", name="Test Dict")
        session.add(dictionary)
        await session.flush()

        profile = LearningProfile(user_id=user.id, dictionary_id=dictionary.id)
        session.add(profile)
        await session.flush()

        word = Word(lemma="unique", lemma_key="unique", pos="noun", translations=["уникальный"])
        session.add(word)
        await session.flush()

        uw1 = UserWord(learning_profile_id=profile.id, word_id=word.id, status="active", due_lesson_number=1)
        session.add(uw1)
        await session.flush()

        uw2 = UserWord(learning_profile_id=profile.id, word_id=word.id, status="active", due_lesson_number=2)
        session.add(uw2)

        with pytest.raises(IntegrityError):
            await session.flush()

    @pytest.mark.asyncio
    async def test_stage_range(self, session: AsyncSession):
        """Stage must be between 0 and 6."""
        from app.models.user import User
        from app.models.dictionary import Dictionary
        from app.models.learning_profile import LearningProfile
        from app.models.word import Word
        from app.models.user_word import UserWord

        user = User(email="stage_test@test.com", password_hash="hash")
        session.add(user)
        await session.flush()

        dictionary = Dictionary(code="stage_dict", name="Test Dict")
        session.add(dictionary)
        await session.flush()

        profile = LearningProfile(user_id=user.id, dictionary_id=dictionary.id)
        session.add(profile)
        await session.flush()

        word = Word(lemma="stage", lemma_key="stage", pos="noun", translations=["стадия"])
        session.add(word)
        await session.flush()

        uw = UserWord(learning_profile_id=profile.id, word_id=word.id, stage=7)
        session.add(uw)

        with pytest.raises(IntegrityError):
            await session.flush()

    @pytest.mark.asyncio
    async def test_due_lesson_only_for_active(self, session: AsyncSession):
        """due_lesson_number can only be NOT NULL when status='active'."""
        from app.models.user import User
        from app.models.dictionary import Dictionary
        from app.models.learning_profile import LearningProfile
        from app.models.word import Word
        from app.models.user_word import UserWord

        user = User(email="due_test@test.com", password_hash="hash")
        session.add(user)
        await session.flush()

        dictionary = Dictionary(code="due_dict", name="Test Dict")
        session.add(dictionary)
        await session.flush()

        profile = LearningProfile(user_id=user.id, dictionary_id=dictionary.id)
        session.add(profile)
        await session.flush()

        word = Word(lemma="due", lemma_key="due", pos="noun", translations=["срок"])
        session.add(word)
        await session.flush()

        # mastered word with due_lesson_number should fail
        uw = UserWord(
            learning_profile_id=profile.id,
            word_id=word.id,
            status="mastered",
            due_lesson_number=5,
        )
        session.add(uw)

        with pytest.raises(IntegrityError):
            await session.flush()


class TestLessonConstraints:
    """Tests for lessons table constraints."""

    @pytest.mark.asyncio
    async def test_unique_profile_lesson_number(self, session: AsyncSession):
        """(learning_profile_id, lesson_number) must be unique."""
        from app.models.user import User
        from app.models.dictionary import Dictionary
        from app.models.learning_profile import LearningProfile
        from app.models.lesson import Lesson

        user = User(email="lesson_test@test.com", password_hash="hash")
        session.add(user)
        await session.flush()

        dictionary = Dictionary(code="lesson_dict", name="Test Dict")
        session.add(dictionary)
        await session.flush()

        profile = LearningProfile(user_id=user.id, dictionary_id=dictionary.id)
        session.add(profile)
        await session.flush()

        lesson1 = Lesson(
            learning_profile_id=profile.id,
            lesson_number=1,
            status="completed",
            words_per_lesson=10,
            started_local_date=date.today(),
            completed_at=datetime.now(timezone.utc),
            completed_local_date=date.today(),
        )
        session.add(lesson1)
        await session.flush()

        lesson2 = Lesson(
            learning_profile_id=profile.id,
            lesson_number=1,
            status="completed",
            words_per_lesson=10,
            started_local_date=date.today(),
            completed_at=datetime.now(timezone.utc),
            completed_local_date=date.today(),
        )
        session.add(lesson2)

        with pytest.raises(IntegrityError):
            await session.flush()

    @pytest.mark.asyncio
    async def test_only_one_in_progress_per_profile(self, session: AsyncSession):
        """Only one lesson with status='in_progress' per profile."""
        from app.models.user import User
        from app.models.dictionary import Dictionary
        from app.models.learning_profile import LearningProfile
        from app.models.lesson import Lesson

        user = User(email="inprogress_test@test.com", password_hash="hash")
        session.add(user)
        await session.flush()

        dictionary = Dictionary(code="ip_dict", name="Test Dict")
        session.add(dictionary)
        await session.flush()

        profile = LearningProfile(user_id=user.id, dictionary_id=dictionary.id)
        session.add(profile)
        await session.flush()

        lesson1 = Lesson(
            learning_profile_id=profile.id,
            lesson_number=1,
            status="in_progress",
            words_per_lesson=10,
            started_local_date=date.today(),
        )
        session.add(lesson1)
        await session.flush()

        lesson2 = Lesson(
            learning_profile_id=profile.id,
            lesson_number=2,
            status="in_progress",
            words_per_lesson=10,
            started_local_date=date.today(),
        )
        session.add(lesson2)

        with pytest.raises(IntegrityError):
            await session.flush()


class TestSentenceReportConstraints:
    """Tests for sentence_reports table constraints."""

    @pytest.mark.asyncio
    async def test_unique_user_exercise(self, session: AsyncSession):
        """(user_id, exercise_id) must be unique."""
        from app.models.user import User
        from app.models.dictionary import Dictionary
        from app.models.learning_profile import LearningProfile
        from app.models.lesson import Lesson
        from app.models.lesson_exercise import LessonExercise
        from app.models.sentence_report import SentenceReport

        user = User(email="report_test@test.com", password_hash="hash")
        session.add(user)
        await session.flush()

        dictionary = Dictionary(code="report_dict", name="Test Dict")
        session.add(dictionary)
        await session.flush()

        profile = LearningProfile(user_id=user.id, dictionary_id=dictionary.id)
        session.add(profile)
        await session.flush()

        lesson = Lesson(
            learning_profile_id=profile.id,
            lesson_number=1,
            status="completed",
            words_per_lesson=10,
            started_local_date=date.today(),
            completed_at=datetime.now(timezone.utc),
            completed_local_date=date.today(),
        )
        session.add(lesson)
        await session.flush()

        exercise = LessonExercise(
            lesson_id=lesson.id,
            order_index=1,
            target_sentence="The cat sits on the mat.",
            reference_translation="Кот сидит на коврике.",
        )
        session.add(exercise)
        await session.flush()

        report1 = SentenceReport(
            user_id=user.id,
            exercise_id=exercise.id,
            reason="bad_sentence",
        )
        session.add(report1)
        await session.flush()

        report2 = SentenceReport(
            user_id=user.id,
            exercise_id=exercise.id,
            reason="bad_translation",
        )
        session.add(report2)

        with pytest.raises(IntegrityError):
            await session.flush()
