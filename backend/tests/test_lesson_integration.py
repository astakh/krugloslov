"""Integration tests for lesson preview and decline endpoints."""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models import Base
from app.models.dictionary import Dictionary
from app.models.dictionary_word import DictionaryWord
from app.models.learning_profile import LearningProfile
from app.models.user import User
from app.models.word import Word


def get_test_db_url() -> str | None:
    """Get test database URL from environment."""
    import os
    return os.environ.get("TEST_DATABASE_URL")


pytestmark = pytest.mark.skipif(
    not get_test_db_url(),
    reason="TEST_DATABASE_URL not set",
)


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
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(engine):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session(engine):
    """Create a database session for setup."""
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def setup_user_with_words(db_session: AsyncSession):
    """Create a user with profile, dictionary, and words."""
    # Create dictionary
    dict_result = await db_session.execute(
        Dictionary.__table__.select().where(Dictionary.is_general == True)
    )
    dictionary = dict_result.first()
    
    if not dictionary:
        dictionary = Dictionary(
            code="general-test",
            name="General Test",
            is_general=True,
        )
        db_session.add(dictionary)
        await db_session.commit()
        await db_session.refresh(dictionary)
    
    # Create user
    import random
    email = f"lesson_{random.randint(1000, 9999)}@test.com"
    user = User(
        email=email,
        password_hash="hashed",
        timezone="UTC",
        is_onboarded=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create profile
    profile = LearningProfile(
        user_id=user.id,
        level="A1",
        dictionary_id=dictionary.id,
        daily_lesson_limit=5,
    )
    db_session.add(profile)
    await db_session.commit()
    
    # Create some words
    words = []
    for i in range(10):
        word = Word(
            lemma=f"word{i}",
            lemma_key=f"word{i}",
            pos="noun",
            level="A1",
            translations=[f"перевод{i}"],
        )
        db_session.add(word)
        await db_session.flush()
        
        # Link to dictionary
        dict_word = DictionaryWord(
            dictionary_id=dictionary.id,
            word_id=word.id,
        )
        db_session.add(dict_word)
        words.append(word)
    
    await db_session.commit()
    
    return user, profile, words, dictionary


@pytest.fixture
async def user_token(client: AsyncClient, setup_user_with_words):
    """Get access token for the test user."""
    user, _, _, _ = setup_user_with_words
    # We need to mock the auth or use a different approach
    # For now, we'll skip this test if we can't easily get a token
    pytest.skip("Need proper auth setup for integration tests")


class TestLessonPreview:
    """Tests for POST /lesson/preview."""

    @pytest.mark.asyncio
    async def test_preview_requires_onboarding(self, client: AsyncClient):
        """Preview should require onboarding."""
        # This test would need a user without onboarding
        pytest.skip("Need to create user without onboarding")

    @pytest.mark.asyncio
    async def test_preview_returns_state(self, client: AsyncClient, user_token: str):
        """Preview should return a valid state."""
        response = await client.post(
            "/lesson/preview",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert data["state"] in ["resume", "limit_reached", "ready", "no_words"]

    @pytest.mark.asyncio
    async def test_preview_deterministic(self, client: AsyncClient, user_token: str):
        """Preview should be deterministic for same state."""
        response1 = await client.post(
            "/lesson/preview",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        response2 = await client.post(
            "/lesson/preview",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        
        assert response1.json() == response2.json()

    @pytest.mark.asyncio
    async def test_preview_ready_structure(self, client: AsyncClient, user_token: str):
        """Ready state should have correct structure."""
        response = await client.post(
            "/lesson/preview",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        data = response.json()
        
        if data["state"] == "ready":
            assert "lesson_number" in data
            assert "due_words" in data
            assert "new_words" in data
            assert "dictionary_exhausted" in data
            
            # Check due_words structure (no translations)
            for word in data["due_words"]:
                assert "word_id" in word
                assert "lemma" in word
                assert "pos" in word
                assert "translations" not in word
            
            # Check new_words structure (with translations)
            for word in data["new_words"]:
                assert "word_id" in word
                assert "lemma" in word
                assert "pos" in word
                assert "translations" in word


class TestDeclineWord:
    """Tests for POST /lesson/new-word/decline."""

    @pytest.mark.asyncio
    async def test_decline_requires_onboarding(self, client: AsyncClient):
        """Decline should require onboarding."""
        pytest.skip("Need to create user without onboarding")

    @pytest.mark.asyncio
    async def test_decline_word(self, client: AsyncClient, user_token: str):
        """Decline should mark word as ignored."""
        # First get preview to find a new word
        preview_response = await client.post(
            "/lesson/preview",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        preview_data = preview_response.json()
        
        if preview_data["state"] != "ready" or not preview_data["new_words"]:
            pytest.skip("No new words to decline")
        
        word_id = preview_data["new_words"][0]["word_id"]
        
        # Decline the word
        response = await client.post(
            "/lesson/new-word/decline",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"word_id": word_id},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "preview" in data

    @pytest.mark.asyncio
    async def test_decline_idempotent(self, client: AsyncClient, user_token: str):
        """Declining same word twice should be idempotent."""
        # Get preview
        preview_response = await client.post(
            "/lesson/preview",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        preview_data = preview_response.json()
        
        if preview_data["state"] != "ready" or not preview_data["new_words"]:
            pytest.skip("No new words to decline")
        
        word_id = preview_data["new_words"][0]["word_id"]
        
        # Decline first time
        response1 = await client.post(
            "/lesson/new-word/decline",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"word_id": word_id},
        )
        assert response1.status_code == 200
        
        # Decline second time
        response2 = await client.post(
            "/lesson/new-word/decline",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"word_id": word_id},
        )
        assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_decline_replaces_word(self, client: AsyncClient, user_token: str):
        """Declining a word should replace it with next by rank."""
        # Get initial preview
        preview1_response = await client.post(
            "/lesson/preview",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        preview1_data = preview1_response.json()
        
        if preview1_data["state"] != "ready" or len(preview1_data["new_words"]) < 2:
            pytest.skip("Not enough new words")
        
        word_id = preview1_data["new_words"][0]["word_id"]
        
        # Decline the word
        decline_response = await client.post(
            "/lesson/new-word/decline",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"word_id": word_id},
        )
        preview2_data = decline_response.json()["preview"]
        
        # The declined word should not be in new_words
        if preview2_data["state"] == "ready":
            new_word_ids = [w["word_id"] for w in preview2_data["new_words"]]
            assert word_id not in new_word_ids

    @pytest.mark.asyncio
    async def test_decline_word_not_in_dictionary(self, client: AsyncClient, user_token: str):
        """Declining word not in dictionary should return 404."""
        response = await client.post(
            "/lesson/new-word/decline",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"word_id": 999999},
        )
        assert response.status_code == 404
