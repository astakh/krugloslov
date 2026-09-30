"""Pydantic schemas for error responses and API contracts."""

from app.schemas.admin import (
    DictionaryImportInput,
    DictionaryInput,
    DictionaryReport,
    DryRunReport,
    ErrorDetail,
    ImportReport,
    WordInput,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserInfo,
)
from app.schemas.dashboard import (
    DashboardSummary,
    DictionaryInfo,
    ProfileInfo,
    ResumeInfo,
    StreakInfo,
    WordsSummary,
)
from app.schemas.lesson import (
    DeclineWordRequest,
    DeclineWordResponse,
    LimitReachedState,
    NoWordsState,
    ReadyState,
    ResumeState,
    WordInfo,
    WordInfoWithTranslations,
)
from app.schemas.lesson_evaluate import (
    EvaluateRequest,
    EvaluateResponse,
    ExerciseResultResponse,
    ReportRequest,
    ReportResponse,
    SuggestionActionRequest,
    SuggestionActionResponse,
    WordEvaluation,
    SuggestedWord,
)
from app.schemas.lesson_resume import (
    AbandonResponse,
    CurrentExerciseResponse,
    LessonSummaryResponse,
    StreakSummary,
)
from app.schemas.lesson_start import (
    LessonStartRequest,
    LessonStartResponse,
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
    # Dashboard
    "DashboardSummary",
    "DictionaryInfo",
    "ProfileInfo",
    "ResumeInfo",
    "StreakInfo",
    "WordsSummary",
    # Lesson
    "DeclineWordRequest",
    "DeclineWordResponse",
    "LimitReachedState",
    "NoWordsState",
    "ReadyState",
    "ResumeState",
    "WordInfo",
    "WordInfoWithTranslations",
    "LessonStartRequest",
    "LessonStartResponse",
    # Lesson Evaluate
    "EvaluateRequest",
    "EvaluateResponse",
    "ExerciseResultResponse",
    "ReportRequest",
    "ReportResponse",
    "SuggestionActionRequest",
    "SuggestionActionResponse",
    "WordEvaluation",
    "SuggestedWord",
    # Lesson Resume
    "AbandonResponse",
    "CurrentExerciseResponse",
    "LessonSummaryResponse",
    "StreakSummary",
]
