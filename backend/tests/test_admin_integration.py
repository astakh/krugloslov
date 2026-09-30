"""Integration tests for admin dictionary import.

These tests require a running PostgreSQL database.
Set TEST_DATABASE_URL environment variable before running.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models import Base
from app.models.user import User
from app.security import hash_password


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
async def admin_token(client: AsyncClient):
    """Create admin user and get access token."""
    # Register admin
    response = await client.post(
        "/auth/register",
        json={"email": "admin@test.com", "password": "adminpassword123"},
    )
    return response.json()["access_token"]


@pytest.fixture
async def user_token(client: AsyncClient):
    """Create regular user and get access token."""
    response = await client.post(
        "/auth/register",
        json={"email": "user@test.com", "password": "userpassword123"},
    )
    return response.json()["access_token"]


class TestAdminAccess:
    """Tests for admin access control."""

    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, client: AsyncClient, user_token: str):
        """Non-admin user should get 403."""
        response = await client.get(
            "/admin/dictionaries",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_forbidden(self, client: AsyncClient):
        """Unauthenticated request should get 401."""
        response = await client.get("/admin/dictionaries")
        assert response.status_code == 401


class TestDictionaryImport:
    """Tests for dictionary import."""

    @pytest.mark.asyncio
    async def test_dry_run(self, client: AsyncClient, admin_token: str):
        """Dry run should validate without writing."""
        file_content = json.dumps({
            "schema_version": 1,
            "dictionary": {
                "code": "test-dry",
                "name": "Test Dry Run",
                "description": "Test",
                "is_general": False,
            },
            "words": [
                {
                    "lemma": "test",
                    "pos": "noun",
                    "level": "A1",
                    "translations": ["тест"],
                }
            ],
        }).encode()

        response = await client.post(
            "/admin/dictionaries/import?dry_run=true",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.json", file_content, "application/json")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_words" in data
        assert "valid_words" in data

    @pytest.mark.asyncio
    async def test_import_success(self, client: AsyncClient, admin_token: str):
        """Successful import should create dictionary and words."""
        file_content = json.dumps({
            "schema_version": 1,
            "dictionary": {
                "code": "test-import",
                "name": "Test Import",
                "description": "Test",
                "is_general": False,
            },
            "words": [
                {
                    "lemma": "apple",
                    "pos": "noun",
                    "level": "A1",
                    "translations": ["яблоко"],
                },
                {
                    "lemma": "banana",
                    "pos": "noun",
                    "level": "A1",
                    "translations": ["банан"],
                },
            ],
        }).encode()

        response = await client.post(
            "/admin/dictionaries/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.json", file_content, "application/json")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 2
        assert data["linked"] == 2
        assert data["errors"] == 0

    @pytest.mark.asyncio
    async def test_no_duplicates_on_reimport(self, client: AsyncClient, admin_token: str):
        """Re-importing same file should not create duplicates."""
        file_content = json.dumps({
            "schema_version": 1,
            "dictionary": {
                "code": "test-nodup",
                "name": "Test No Duplicates",
                "description": "Test",
                "is_general": False,
            },
            "words": [
                {
                    "lemma": "unique",
                    "pos": "noun",
                    "level": "A1",
                    "translations": ["уникальный"],
                }
            ],
        }).encode()

        # First import
        response1 = await client.post(
            "/admin/dictionaries/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.json", file_content, "application/json")},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["added"] == 1

        # Second import (same file)
        response2 = await client.post(
            "/admin/dictionaries/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.json", file_content, "application/json")},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["added"] == 0  # No new words
        assert data2["linked"] == 0  # No new links

    @pytest.mark.asyncio
    async def test_invalid_words_skipped(self, client: AsyncClient, admin_token: str):
        """Invalid words should be skipped with error details."""
        file_content = json.dumps({
            "schema_version": 1,
            "dictionary": {
                "code": "test-invalid",
                "name": "Test Invalid",
                "description": "Test",
                "is_general": False,
            },
            "words": [
                {
                    "lemma": "valid",
                    "pos": "noun",
                    "level": "A1",
                    "translations": ["валидный"],
                },
                {
                    "lemma": "invalid",
                    "pos": "wrong_pos",  # Invalid POS
                    "level": "A1",
                    "translations": ["невалидный"],
                },
            ],
        }).encode()

        response = await client.post(
            "/admin/dictionaries/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("test.json", file_content, "application/json")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 1  # Only valid word
        assert data["errors"] >= 1  # At least one error
        assert len(data["error_details"]) >= 1
        assert data["error_details"][0]["code"] == "invalid_pos"

    @pytest.mark.asyncio
    async def test_file_too_large(self, client: AsyncClient, admin_token: str):
        """File larger than 10 MB should be rejected."""
        # Create a large file (> 10 MB)
        large_content = b"x" * (11 * 1024 * 1024)

        response = await client.post(
            "/admin/dictionaries/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("large.json", large_content, "application/json")},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_json(self, client: AsyncClient, admin_token: str):
        """Invalid JSON should be rejected."""
        response = await client.post(
            "/admin/dictionaries/import",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("invalid.json", b"not json", "application/json")},
        )
        assert response.status_code == 422
