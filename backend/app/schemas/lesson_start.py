"""Lesson start schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class LessonStartRequest(BaseModel):
    """Request to start a lesson."""
    word_ids: List[int] = Field(..., min_length=1)


class ExerciseWordInfo(BaseModel):
    """Word info within an exercise."""
    word_id: int
    lemma: str
    pos: str
    surface_form: str
    is_new: bool


class CurrentExercise(BaseModel):
    """Current exercise info returned to client (without reference translation)."""
    exercise_id: int
    order_index: int
    sentence: str
    words: List[dict]  # word_id, lemma, pos, surface_form, is_new


class LessonStartResponse(BaseModel):
    """Response after successful lesson creation."""
    lesson_id: int
    lesson_number: int
    exercises_total: int
    current_exercise: CurrentExercise


class LlmSentenceGroup(BaseModel):
    """LLM response for a single word group."""
    group_index: int
    sentence: str
    reference_translation: str
    words: List["LlmSentenceWord"]


class LlmSentenceWord(BaseModel):
    """Word placement in LLM-generated sentence."""
    lemma: str
    pos: str
    surface_form: str


class LlmGenerateResponse(BaseModel):
    """Full LLM response for sentence generation."""
    groups: List[LlmSentenceGroup]


# Rebuild models for forward references
LlmSentenceGroup.model_rebuild()
LlmGenerateResponse.model_rebuild()
