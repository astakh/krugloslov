"""Admin and dictionary import Pydantic schemas."""

from __future__ import annotations

import re
import unicodedata
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.word import VALID_LEVELS, VALID_POS

# Allowed characters in lemma: latin letters, apostrophe, hyphen, space
LEMMA_PATTERN = re.compile(r"^[a-zA-Z'\-\s]+$")


class DictionaryImportInput(BaseModel):
    """Schema for the dictionary import JSON file."""
    schema_version: int = Field(..., ge=1)
    dictionary: DictionaryInput
    words: List[WordInput] = Field(..., max_length=50000)


class DictionaryInput(BaseModel):
    """Dictionary metadata from import file."""
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=100)
    description: str = Field(default="")
    is_general: bool = Field(default=False)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate dictionary code: latin, digits, hyphen only."""
        if not re.match(r"^[a-zA-Z0-9\-]+$", v):
            raise ValueError("Code must contain only latin letters, digits, and hyphens")
        return v


class WordInput(BaseModel):
    """Single word entry from import file."""
    lemma: str = Field(..., min_length=1)
    pos: str
    level: Optional[str] = None
    translations: List[str]

    @field_validator("lemma")
    @classmethod
    def validate_lemma(cls, v: str) -> str:
        """Validate and normalize lemma."""
        v = v.strip()
        # NFC normalize
        v = unicodedata.normalize("NFC", v)
        return v

    @field_validator("translations")
    @classmethod
    def validate_translations(cls, v: List[str]) -> List[str]:
        """Validate translations: 1-5 non-empty strings, each up to 100 chars."""
        if not v:
            raise ValueError("At least one translation required")
        # Filter empty and deduplicate
        seen = set()
        result = []
        for t in v:
            t = t.strip()
            if t and t not in seen and len(t) <= 100:
                seen.add(t)
                result.append(t)
        if not result:
            raise ValueError("At least one valid translation required")
        if len(result) > 5:
            result = result[:5]
        return result


class DictionaryReport(BaseModel):
    """Dictionary info in import report."""
    code: str
    name: str
    created: bool


class ErrorDetail(BaseModel):
    """Single error detail in import report."""
    index: int  # 0-based word index in file
    lemma: Optional[str] = None
    pos: Optional[str] = None
    code: str  # error code
    message: str


class ImportReport(BaseModel):
    """Full import report."""
    dictionary: DictionaryReport
    added: int = 0
    linked: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: List[ErrorDetail] = Field(default_factory=list)


class DryRunReport(BaseModel):
    """Report for dry_run mode."""
    dictionary: DictionaryReport
    total_words: int
    valid_words: int
    skipped: int
    errors: int
    error_details: List[ErrorDetail] = Field(default_factory=list)
