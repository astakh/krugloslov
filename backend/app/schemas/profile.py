"""Schemas for profile and statistics endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class HeatmapDay(BaseModel):
    """Single day in heatmap."""
    date: date
    count: int


class ProfileStatsResponse(BaseModel):
    """Response for GET /profile/stats."""
    current_streak: int
    longest_streak: int
    accuracy_30_days: Optional[float]
    accuracy_all_time: Optional[float]
    words_active: int
    words_mastered: int
    words_ignored: int
    lessons_completed: int
    heatmap: List[HeatmapDay]


class WordsByStatus(BaseModel):
    """Words count by status."""
    active: int
    mastered: int
    ignored: int


class LearningStats(BaseModel):
    """Learning statistics."""
    words: WordsByStatus
    accuracy_30_days: Optional[float]
    accuracy_all_time: Optional[float]
    lessons_completed: int


class LearningProfileResponse(BaseModel):
    """Response for GET /learning-profile."""
    level: str
    dictionary_id: int
    dictionary_name: str
    daily_lesson_limit: int
    daily_lesson_limit_max: int
    words_per_lesson: int
    words_per_lesson_max: int
    stats: LearningStats


class LearningProfileUpdateRequest(BaseModel):
    """Request for PATCH /learning-profile."""
    level: Optional[str] = None
    dictionary_id: Optional[int] = None
    daily_lesson_limit: Optional[int] = None
    words_per_lesson: Optional[int] = None


class LearningProfileUpdateResponse(BaseModel):
    """Response for PATCH /learning-profile."""
    message: str
    level: str
    dictionary_id: int
    daily_lesson_limit: int
    words_per_lesson: int


class DictionaryListItem(BaseModel):
    """Item in dictionaries list."""
    id: int
    code: str
    name: str
    description: str
    is_general: bool
    words_total: int


class DictionariesListResponse(BaseModel):
    """Response for GET /dictionaries."""
    dictionaries: List[DictionaryListItem]
