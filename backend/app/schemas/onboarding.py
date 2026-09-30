"""Onboarding Pydantic schemas."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

# IANA timezone pattern (simplified but covers most cases)
# Examples: Europe/Berlin, America/New_York, Asia/Tokyo
IANA_TIMEZONE_PATTERN = re.compile(r"^[A-Za-z]+/[A-Za-z_]+$")

# Valid onboarding levels
ONBOARDING_LEVELS = ("A1", "A2", "B1", "B2")


class OnboardingRequest(BaseModel):
    """Request schema for completing onboarding."""
    timezone: str = Field(..., min_length=1, max_length=64)
    level: str = Field(..., min_length=2, max_length=2)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone is in IANA format."""
        v = v.strip()
        # Reject offset formats like +03:00, UTC+3, etc.
        if v.startswith("+") or v.startswith("-") or v.startswith("UTC"):
            raise ValueError("Timezone must be in IANA format (e.g., Europe/Berlin)")
        
        # Check IANA pattern
        if not IANA_TIMEZONE_PATTERN.match(v):
            raise ValueError("Timezone must be in IANA format (e.g., Europe/Berlin)")
        
        return v

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate level is one of A1-B2."""
        v = v.strip().upper()
        if v not in ONBOARDING_LEVELS:
            raise ValueError(f"Level must be one of: {', '.join(ONBOARDING_LEVELS)}")
        return v


class OnboardingResponse(BaseModel):
    """Response schema for completed onboarding."""
    message: str = "Онбординг успешно завершён"
