"""Tests for security utilities."""

from __future__ import annotations

import pytest

from app.security import (
    create_access_token,
    decode_access_token,
    generate_family_id,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    JWTDecodeError,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password_returns_string(self):
        """hash_password should return a string."""
        result = hash_password("test_password")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        password = "my_secure_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for incorrect password."""
        password = "my_secure_password"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False

    def test_hash_password_different_each_time(self):
        """hash_password should produce different hashes for same password (salt)."""
        password = "test_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts


class TestJWT:
    """Tests for JWT utilities."""

    def test_create_access_token_returns_string(self):
        """create_access_token should return a JWT string."""
        token = create_access_token(user_id=1, email="test@example.com")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_valid(self):
        """decode_access_token should decode a valid token."""
        user_id = 42
        email = "user@example.com"
        token = create_access_token(user_id=user_id, email=email)
        
        payload = decode_access_token(token)
        
        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert "iat" in payload
        assert "exp" in payload

    def test_decode_access_token_invalid(self):
        """decode_access_token should raise JWTDecodeError for invalid token."""
        with pytest.raises(JWTDecodeError):
            decode_access_token("invalid.token.here")


class TestRefreshToken:
    """Tests for refresh token utilities."""

    def test_generate_refresh_token_returns_string(self):
        """generate_refresh_token should return a hex string."""
        token = generate_refresh_token()
        assert isinstance(token, str)
        assert len(token) == 64  # 32 bytes = 64 hex chars

    def test_generate_refresh_token_unique(self):
        """generate_refresh_token should produce unique tokens."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()
        assert token1 != token2

    def test_hash_refresh_token_returns_string(self):
        """hash_refresh_token should return a hex string."""
        token = "test_token"
        hashed = hash_refresh_token(token)
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 = 64 hex chars

    def test_hash_refresh_token_deterministic(self):
        """hash_refresh_token should produce same hash for same input."""
        token = "test_token"
        hash1 = hash_refresh_token(token)
        hash2 = hash_refresh_token(token)
        assert hash1 == hash2

    def test_generate_family_id_returns_string(self):
        """generate_family_id should return a hex string."""
        family_id = generate_family_id()
        assert isinstance(family_id, str)
        assert len(family_id) == 32  # 16 bytes = 32 hex chars

    def test_generate_family_id_unique(self):
        """generate_family_id should produce unique IDs."""
        id1 = generate_family_id()
        id2 = generate_family_id()
        assert id1 != id2
