"""Dashboard schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class DictionaryInfo(BaseModel):
    """Dictionary information for dashboard."""
    id: int
    name: str


class ProfileInfo(BaseModel):
    """Profile information for dashboard."""
    level: str
    dictionary: DictionaryInfo


class ResumeInfo(BaseModel):
    """Resume information for in-progress lesson."""
    lesson_id: int
    exercises_done: int
    exercises_total: int


class WordsSummary(BaseModel):
    """Words count summary."""
    active: int
    mastered: int
    ignored: int


class StreakInfo(BaseModel):
    """Streak information."""
    current: int
    longest: int
    today_done: bool


class DashboardSummary(BaseModel):
    """Dashboard summary response."""
    profile: ProfileInfo
    today: date
    lessons_today: int
    daily_lesson_limit: int
    resets_at: datetime
    cta: Literal["start", "resume", "limit_reached"]
    resume: Optional[ResumeInfo]
    words: WordsSummary
    streak: StreakInfo
