"""Authentication Pydantic schemas."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate and normalize email."""
        v = v.strip().lower()
        # Basic email format validation
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v


class LoginRequest(BaseModel):
    """Request schema for user login."""
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate and normalize email."""
        return v.strip().lower()


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """Response schema for GET /me endpoint."""
    id: int
    email: str
    is_onboarded: bool
    is_admin: bool

    class Config:
        from_attributes = True


class RefreshRequest(BaseModel):
    """Request schema for token refresh (refresh token comes from cookie)."""
    pass
