"""Pydantic schemas for error responses and API contracts."""

from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserInfo,
)
from app.schemas.admin import (
    DictionaryImportInput,
    DictionaryInput,
    DictionaryReport,
    DryRunReport,
    ErrorDetail,
    ImportReport,
    WordInput,
)
from app.schemas.onboarding import (
    OnboardingRequest,
    OnboardingResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserInfo",
    # Admin
    "DictionaryImportInput",
    "DictionaryInput",
    "DictionaryReport",
    "DryRunReport",
    "ErrorDetail",
    "ImportReport",
    "WordInput",
    # Onboarding
    "OnboardingRequest",
    "OnboardingResponse",
]
