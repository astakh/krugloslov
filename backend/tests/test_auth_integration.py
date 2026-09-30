"""Integration tests for authentication endpoints.

These tests require a running PostgreSQL database.
Set TEST_DATABASE_URL environment variable before running.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models import Base


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


class TestRegister:
    """Tests for POST /auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Successful registration should return access token."""
        response = await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Check refresh token cookie
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        """Registration with existing email should return 409."""
        # First registration
        await client.post(
            "/auth/register",
            json={"email": "duplicate@example.com", "password": "securepassword123"},
        )
        
        # Second registration with same email
        response = await client.post(
            "/auth/register",
            json={"email": "duplicate@example.com", "password": "anotherpassword123"},
        )
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "email_taken"

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Registration with invalid email should return 422."""
        response = await client.post(
            "/auth/register",
            json={"email": "invalid-email", "password": "securepassword123"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Registration with short password should return 422."""
        response = await client.post(
            "/auth/register",
            json={"email": "test2@example.com", "password": "short"},
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """Successful login should return access token."""
        # Register first
        await client.post(
            "/auth/register",
            json={"email": "login@example.com", "password": "securepassword123"},
        )
        
        # Login
        response = await client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in response.cookies

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        """Login with wrong password should return 401."""
        # Register first
        await client.post(
            "/auth/register",
            json={"email": "wrongpass@example.com", "password": "securepassword123"},
        )
        
        # Login with wrong password
        response = await client.post(
            "/auth/login",
            json={"email": "wrongpass@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "invalid_credentials"

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Login with nonexistent email should return 401."""
        response = await client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "invalid_credentials"


class TestGetMe:
    """Tests for GET /auth/me."""

    @pytest.mark.asyncio
    async def test_get_me_authenticated(self, client: AsyncClient):
        """GET /me with valid token should return user info."""
        # Register
        register_response = await client.post(
            "/auth/register",
            json={"email": "me@example.com", "password": "securepassword123"},
        )
        access_token = register_response.json()["access_token"]
        
        # Get me
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"
        assert data["is_onboarded"] is False
        assert data["is_admin"] is False
        assert "password_hash" not in data

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """GET /me without token should return 401."""
        response = await client.get("/auth/me")
        assert response.status_code == 401


class TestRefresh:
    """Tests for POST /auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient):
        """Successful refresh should return new tokens."""
        # Register
        register_response = await client.post(
            "/auth/register",
            json={"email": "refresh@example.com", "password": "securepassword123"},
        )
        refresh_token = register_response.cookies.get("refresh_token")
        
        # Refresh
        client.cookies.set("refresh_token", refresh_token, domain="test", path="/auth")
        response = await client.post("/auth/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in response.cookies
        
        # New refresh token should be different
        new_refresh_token = response.cookies.get("refresh_token")
        assert new_refresh_token != refresh_token

    @pytest.mark.asyncio
    async def test_refresh_replay_attack(self, client: AsyncClient):
        """Using old refresh token should revoke entire family."""
        # Register
        register_response = await client.post(
            "/auth/register",
            json={"email": "replay@example.com", "password": "securepassword123"},
        )
        old_refresh_token = register_response.cookies.get("refresh_token")
        
        # First refresh
        client.cookies.set("refresh_token", old_refresh_token, domain="test", path="/auth")
        refresh_response = await client.post("/auth/refresh")
        assert refresh_response.status_code == 200
        
        # Try to use old refresh token again (replay attack)
        client.cookies.set("refresh_token", old_refresh_token, domain="test", path="/auth")
        response = await client.post("/auth/refresh")
        assert response.status_code == 401
        data = response.json()
        assert "отозваны" in data["error"]["message"].lower()


class TestLogout:
    """Tests for POST /auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient):
        """Logout should revoke refresh token."""
        # Register
        register_response = await client.post(
            "/auth/register",
            json={"email": "logout@example.com", "password": "securepassword123"},
        )
        refresh_token = register_response.cookies.get("refresh_token")
        
        # Logout
        client.cookies.set("refresh_token", refresh_token, domain="test", path="/auth")
        response = await client.post("/auth/logout")
        assert response.status_code == 200
        
        # Try to use revoked refresh token
        client.cookies.set("refresh_token", refresh_token, domain="test", path="/auth")
        refresh_response = await client.post("/auth/refresh")
        assert refresh_response.status_code == 401
