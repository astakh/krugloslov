"""LLM-related exceptions."""

from __future__ import annotations


class LlmError(Exception):
    """Base exception for LLM errors."""
    
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class LlmUnavailable(LlmError):
    """LLM service is unavailable (network error, 400, 5xx after retries)."""
    pass


class LlmQuotaExceeded(LlmError):
    """LLM quota exceeded (402 or token limit)."""
    pass


class LlmInvalidResponse(LlmError):
    """LLM returned invalid response (JSON parse error, schema validation failed)."""
    pass


class LlmRefused(LlmError):
    """LLM refused to generate content (blacklist, content policy)."""
    pass
