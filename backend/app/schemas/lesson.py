"""Lesson preview and decline schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class WordInfo(BaseModel):
    """Basic word information."""
    word_id: int
    lemma: str
    pos: str


class WordInfoWithTranslations(WordInfo):
    """Word information with translations."""
    translations: List[str]


class ResumeState(BaseModel):
    """Response when there's an in-progress lesson."""
    state: Literal["resume"]
    lesson_id: int
    exercises_done: int
    exercises_total: int


class LimitReachedState(BaseModel):
    """Response when daily limit is reached."""
    state: Literal["limit_reached"]
    resets_at: datetime


class ReadyState(BaseModel):
    """Response when lesson is ready to start."""
    state: Literal["ready"]
    lesson_number: int
    due_words: List[WordInfo]
    new_words: List[WordInfoWithTranslations]
    dictionary_exhausted: bool


class NoWordsState(BaseModel):
    """Response when no words are available."""
    state: Literal["no_words"]


LessonPreviewResponse = ResumeState | LimitReachedState | ReadyState | NoWordsState


class DeclineWordRequest(BaseModel):
    """Request to decline a new word."""
    word_id: int


class DeclineWordResponse(BaseModel):
    """Response after declining a word."""
    message: str = "Слово успешно отклонено"
    preview: LessonPreviewResponse
