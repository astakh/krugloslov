"""LLM integration module."""

from app.llm.client import GigaChatClient, gigachat_client
from app.llm.exceptions import (
    LlmError,
    LlmInvalidResponse,
    LlmQuotaExceeded,
    LlmRefused,
    LlmUnavailable,
)
from app.llm.schemas import (
    EvaluateTranslationResponse,
    GenerateSentencesResponse,
    SentencePair,
    WordEvaluation,
)

__all__ = [
    # Client
    "GigaChatClient",
    "gigachat_client",
    # Exceptions
    "LlmError",
    "LlmInvalidResponse",
    "LlmQuotaExceeded",
    "LlmRefused",
    "LlmUnavailable",
    # Schemas
    "EvaluateTranslationResponse",
    "GenerateSentencesResponse",
    "SentencePair",
    "WordEvaluation",
]
