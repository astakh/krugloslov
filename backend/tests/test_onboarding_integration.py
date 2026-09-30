"""Integration tests for onboarding.

These tests require a running PostgreSQL database.
Set TEST_DATABASE_URL environment variable before running.
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models import Base
from app.models.dictionary import Dictionary
from app.models.learning_profile import LearningProfile
from app.models.user import User


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
async def user_token(client: AsyncClient):
    """Create a new user and return access token."""
    import random
    email = f"onboard_{random.randint(1000, 9999)}@test.com"
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
async def general_dictionary(db_session: AsyncSession):
    """Create a general dictionary for tests."""
    # Check if exists
    result = await db_session.execute(
        select(Dictionary).where(Dictionary.is_general == True)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    
    # Create new
    dictionary = Dictionary(
        code="general-test",
        name="General Test Dictionary",
        description="Test general dictionary",
        is_general=True,
    )
    db_session.add(dictionary)
    await db_session.commit()
    return dictionary


class TestOnboarding:
    """Tests for onboarding endpoint."""

    @pytest.mark.asyncio
    async def test_complete_onboarding_success(
        self, client: AsyncClient, user_token: str, general_dictionary: Dictionary
    ):
        """Successful onboarding should create learning profile."""
        response = await client.post(
            "/onboarding/complete",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "timezone": "Europe/Berlin",
                "level": "A2",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Онбординг успешно завершён"

    @pytest.mark.asyncio
    async def test_already_onboarded(
        self, client: AsyncClient, user_token: str, general_dictionary: Dictionary
    ):
        """Onboarding already completed user should return 409."""
        # First onboarding
        await client.post(
            "/onboarding/complete",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "timezone": "Europe/Berlin",
                "level": "A1",
            },
        )
        
        # Second attempt
        response = await client.post(
            "/onboarding/complete",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "timezone": "Europe/Moscow",
                "level": "B1",
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "already_onboarded"

    @pytest.mark.asyncio
    async def test_invalid_level(self, client: AsyncClient, user_token: str):
        """Invalid level should return 422."""
        response = await client.post(
            "/onboarding/complete",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "timezone": "Europe/Berlin",
                "level": "C1",  # Not allowed
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_timezone(self, client: AsyncClient, user_token: str):
        """Invalid timezone should return 422."""
        response = await client.post(
            "/onboarding/complete",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "timezone": "+03:00",  # Offset not allowed
                "level": "A1",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated(self, client: AsyncClient):
        """Unauthenticated request should return 401."""
        response = await client.post(
            "/onboarding/complete",
            json={
                "timezone": "Europe/Berlin",
                "level": "A1",
            },
        )
        assert response.status_code == 401
