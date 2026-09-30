"""Tests for streak calculation service."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.streak_service import calculate_streak, is_streak_at_risk


class TestCalculateStreak:
    """Tests for calculate_streak function."""

    def test_empty_dates(self):
        """Empty dates should return 0, 0, False."""
        today = date(2026, 1, 10)
        current, longest, today_done = calculate_streak(set(), today)
        assert current == 0
        assert longest == 0
        assert today_done is False

    def test_today_only(self):
        """{10}, today=10 → current 1, longest 1."""
        today = date(2026, 1, 10)
        dates = {date(2026, 1, 10)}
        current, longest, today_done = calculate_streak(dates, today)
        assert current == 1
        assert longest == 1
        assert today_done is True

    def test_yesterday_only(self):
        """{9}, today=10 → current 1, longest 1, at risk."""
        today = date(2026, 1, 10)
        dates = {date(2026, 1, 9)}
        current, longest, today_done = calculate_streak(dates, today)
        assert current == 1
        assert longest == 1
        assert today_done is False
        assert is_streak_at_risk(current, today_done) is True

    def test_old_date_only(self):
        """{8}, today=10 → current 0, longest 1."""
        today = date(2026, 1, 10)
        dates = {date(2026, 1, 8)}
        current, longest, today_done = calculate_streak(dates, today)
        assert current == 0
        assert longest == 1
        assert today_done is False

    def test_consecutive_four_days(self):
        """{7,8,9,10}, today=10 → current 4, longest 4."""
        today = date(2026, 1, 10)
        dates = {
            date(2026, 1, 7),
            date(2026, 1, 8),
            date(2026, 1, 9),
            date(2026, 1, 10),
        }
        current, longest, today_done = calculate_streak(dates, today)
        assert current == 4
        assert longest == 4
        assert today_done is True

    def test_gap_in_middle(self):
        """{5,6,7,9,10}, today=10 → current 2, longest 3."""
        today = date(2026, 1, 10)
        dates = {
            date(2026, 1, 5),
            date(2026, 1, 6),
            date(2026, 1, 7),
            date(2026, 1, 9),
            date(2026, 1, 10),
        }
        current, longest, today_done = calculate_streak(dates, today)
        assert current == 2
        assert longest == 3
        assert today_done is True

    def test_gap_with_yesterday(self):
        """{9,11}, today=10 → current 2, longest 2."""
        # Note: 11 is in the future relative to today=10, so it should be filtered out
        # Actually, the test says {9,11}, today=10 → current 2, longest 2
        # This means 11 should be treated as 10 (clamped to today)
        # But our implementation filters out dates > today
        # Let me re-read the requirements...
        # "Даты больше today приводятся к today"
        # So we need to clamp dates > today to today
        today = date(2026, 1, 10)
        dates = {
            date(2026, 1, 9),
            date(2026, 1, 11),  # Should be clamped to 10
        }
        # After clamping: {9, 10}
        current, longest, today_done = calculate_streak(dates, today)
        assert current == 2
        assert longest == 2
        assert today_done is True

    def test_future_dates_clamped(self):
        """Future dates should be clamped to today."""
        today = date(2026, 1, 10)
        dates = {
            date(2026, 1, 8),
            date(2026, 1, 15),  # Future, should be clamped to 10
        }
        # After clamping: {8, 10}
        current, longest, today_done = calculate_streak(dates, today)
        # 8 is not consecutive with 10, so current should be 1 (just 10)
        # Actually, 9 is missing, so current = 1 (just today)
        assert current == 1
        assert longest == 1
        assert today_done is True

    def test_multiple_gaps(self):
        """Multiple gaps in dates."""
        today = date(2026, 1, 15)
        dates = {
            date(2026, 1, 1),
            date(2026, 1, 2),
            date(2026, 1, 3),
            date(2026, 1, 10),
            date(2026, 1, 11),
            date(2026, 1, 14),
            date(2026, 1, 15),
        }
        current, longest, today_done = calculate_streak(dates, today)
        assert current == 2  # 14, 15
        assert longest == 3  # 1, 2, 3
        assert today_done is True


class TestIsStreakAtRisk:
    """Tests for is_streak_at_risk function."""

    def test_at_risk(self):
        """Current > 0 and today not done should be at risk."""
        assert is_streak_at_risk(1, False) is True
        assert is_streak_at_risk(5, False) is True

    def test_not_at_risk_zero_streak(self):
        """Current = 0 should not be at risk."""
        assert is_streak_at_risk(0, False) is False

    def test_not_at_risk_today_done(self):
        """Today done should not be at risk."""
        assert is_streak_at_risk(1, True) is False
        assert is_streak_at_risk(5, True) is False
