"""Pydantic schemas for LLM response validation."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class SentencePair(BaseModel):
    """English sentence with Russian translation."""
    english: str = Field(..., min_length=1, max_length=200)
    russian: str = Field(..., min_length=1, max_length=200)


class GenerateSentencesResponse(BaseModel):
    """Response schema for sentence generation."""
    sentences: List[SentencePair] = Field(..., min_length=1, max_length=10)


class WordEvaluation(BaseModel):
    """Evaluation result for a single word."""
    word: str = Field(..., min_length=1)
    status: Literal["correct", "incorrect", "partial"]
    feedback: str = Field(default="", max_length=200)


class EvaluateTranslationResponse(BaseModel):
    """Response schema for translation evaluation."""
    results: List[WordEvaluation] = Field(..., min_length=1)
    overall: Literal["correct", "incorrect", "partial"]
