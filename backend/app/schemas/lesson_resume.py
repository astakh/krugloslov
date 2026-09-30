"""Schemas for lesson resume and summary endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CurrentExerciseResponse(BaseModel):
    """Response for GET /lesson/{id}/current."""
    exercise_id: int
    sentence: str
    order_index: int
    exercises_done: int
    exercises_total: int


class AbandonResponse(BaseModel):
    """Response for POST /lesson/{id}/abandon."""
    message: str


class StreakSummary(BaseModel):
    """Streak information for lesson summary."""
    current: int
    longest: int
    today_done: bool
    extended_today: bool


class LessonSummaryResponse(BaseModel):
    """Response for GET /lesson/{id}/summary."""
    lesson_number: int
    words_total: int
    reviewed: int
    new_words: int
    correct: int
    typo: int
    incorrect: int
    without_errors: int
    suggestions_added: int
    streak: StreakSummary
