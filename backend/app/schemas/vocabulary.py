"""Schemas for vocabulary endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class VocabularyWordItem(BaseModel):
    """Item in vocabulary list."""
    word_id: int
    lemma: str
    pos: str
    translations: List[str]
    status: str
    stage: int
    due_in_lessons: int


class VocabularyListResponse(BaseModel):
    """Response for vocabulary list."""
    words: List[VocabularyWordItem]
    total: int
    page: int
    page_size: int


class ContextHistoryItem(BaseModel):
    """Item in context history."""
    sentence: str
    surface_form: Optional[str]
    result: Optional[str]
    date: datetime


class VocabularyWordDetail(BaseModel):
    """Detailed word information."""
    word_id: int
    lemma: str
    pos: str
    translations: List[str]
    status: str
    stage: int
    due_in_lessons: int
    context_history: List[ContextHistoryItem]


class ChangeStatusRequest(BaseModel):
    """Request to change word status."""
    status: str = Field(..., pattern="^(active|ignored)$")


class ChangeStatusResponse(BaseModel):
    """Response after status change."""
    message: str
    word_id: int
    new_status: str
