"""Tests for onboarding schemas."""

from __future__ import annotations

import pytest

from app.schemas.onboarding import OnboardingRequest, ONBOARDING_LEVELS


class TestOnboardingRequest:
    """Tests for OnboardingRequest schema."""

    def test_valid_request(self):
        """Valid onboarding request should pass validation."""
        request = OnboardingRequest(
            timezone="Europe/Berlin",
            level="A2"
        )
        assert request.timezone == "Europe/Berlin"
        assert request.level == "A2"

    def test_valid_levels(self):
        """All valid levels should be accepted."""
        for level in ONBOARDING_LEVELS:
            request = OnboardingRequest(
                timezone="Europe/Moscow",
                level=level
            )
            assert request.level == level

    def test_invalid_level(self):
        """Invalid level should fail validation."""
        with pytest.raises(Exception):
            OnboardingRequest(
                timezone="Europe/Berlin",
                level="C1"  # Not allowed in onboarding
            )

    def test_invalid_timezone_offset(self):
        """Offset timezone formats should be rejected."""
        invalid_timezones = [
            "+03:00",
            "UTC+3",
            "-05:00",
            "GMT+2",
        ]
        for tz in invalid_timezones:
            with pytest.raises(Exception):
                OnboardingRequest(
                    timezone=tz,
                    level="A1"
                )

    def test_valid_iana_timezones(self):
        """Valid IANA timezones should be accepted."""
        valid_timezones = [
            "Europe/Berlin",
            "America/New_York",
            "Asia/Tokyo",
            "Europe/Moscow",
            "Australia/Sydney",
        ]
        for tz in valid_timezones:
            request = OnboardingRequest(
                timezone=tz,
                level="A1"
            )
            assert request.timezone == tz

    def test_invalid_timezone_format(self):
        """Invalid timezone formats should be rejected."""
        invalid_timezones = [
            "Invalid/Timezone/Format",
            "just_a_word",
            "123/456",
        ]
        for tz in invalid_timezones:
            with pytest.raises(Exception):
                OnboardingRequest(
                    timezone=tz,
                    level="A1"
                )

    def test_timezone_trimmed(self):
        """Timezone should be trimmed."""
        request = OnboardingRequest(
            timezone="  Europe/Berlin  ",
            level="A1"
        )
        assert request.timezone == "Europe/Berlin"

    def test_level_uppercase(self):
        """Level should be converted to uppercase."""
        request = OnboardingRequest(
            timezone="Europe/Berlin",
            level="a2"
        )
        assert request.level == "A2"
