"""Schemas for lesson evaluation endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# === Evaluate Translation ===

class EvaluateRequest(BaseModel):
    """Request to evaluate user translation."""
    exercise_id: int
    user_translation: Optional[str] = None
    dont_know: Optional[bool] = False


class WordEvaluation(BaseModel):
    """Evaluation result for a single word."""
    word_id: int
    lemma: str
    pos: str
    surface_form: str
    result: Literal["correct", "typo", "incorrect"]
    user_fragment: Optional[str]
    translations: List[str]


class SuggestedWord(BaseModel):
    """Suggested new word from LLM."""
    word_id: int
    lemma: str
    pos: str
    translations: List[str]


class EvaluateResponse(BaseModel):
    """Response after evaluating translation."""
    exercise_id: int
    target_sentence: str
    reference_translation: str
    user_translation: Optional[str]
    dont_know: bool
    words: List[WordEvaluation]
    suggestions: List[SuggestedWord]
    lesson_completed: bool


# === Get Exercise Result ===

class ExerciseResultResponse(BaseModel):
    """Response for getting exercise result."""
    exercise_id: int
    target_sentence: str
    reference_translation: str
    user_translation: Optional[str]
    dont_know: bool
    words: List[WordEvaluation]
    suggestions: List[SuggestedWord]
    lesson_completed: bool


class TargetWordInfo(BaseModel):
    """Target word information for exercise."""
    word_id: int
    lemma: str
    pos: str


class ExerciseInfoResponse(BaseModel):
    """Response for getting exercise info."""
    exercise_id: int
    lesson_id: int
    order_index: int
    total_exercises: int
    target_sentence: str
    status: str  # pending or evaluated
    target_words: List[TargetWordInfo]  # Target words to translate


# === Handle Suggestion ===

class SuggestionActionRequest(BaseModel):
    """Request to add or ignore a suggested word."""
    action: Literal["add", "ignore"]


class SuggestionActionResponse(BaseModel):
    """Response after handling suggestion."""
    message: str


# === Report Exercise ===

class ReportRequest(BaseModel):
    """Request to report an exercise."""
    reason: Literal["bad_sentence", "wrong_translation", "grammar_error", "other"]
    comment: str = Field(..., max_length=500)


class ReportResponse(BaseModel):
    """Response after reporting exercise."""
    message: str
    report_id: int


# === LLM Response Schemas ===

class LlmWordEvaluation(BaseModel):
    """LLM evaluation for a word."""
    lemma: str
    pos: str
    result: Literal["correct", "typo", "incorrect"]
    user_fragment: Optional[str] = None


class LlmSuggestedWord(BaseModel):
    """LLM suggested new word."""
    lemma: str
    pos: str
    translations: List[str]


class LlmEvaluateResponse(BaseModel):
    """LLM response for translation evaluation."""
    evaluations: List[LlmWordEvaluation]
    new_suggested_words: List[LlmSuggestedWord] = []
