"""Services package."""

from app.services.auth import AuthService
from app.services.dashboard_service import DashboardService
from app.services.dictionary_import import DictionaryImportService
from app.services.events import record_event
from app.services.evaluate_translation_service import EvaluateTranslationService
from app.services.lesson_exercise_service import LessonExerciseService
from app.services.lesson_preview_service import LessonPreviewService
from app.services.lesson_resume_service import LessonResumeService
from app.services.lesson_start_service import LessonStartService
from app.services.lesson_summary_service import LessonSummaryService
from app.services.llm_logger import LlmLogger
from app.services.onboarding import OnboardingService
from app.services.prompt_service import PromptService
from app.services.report_service import ReportService
from app.services.sentence_validator import validate_sentence_group, validate_all_groups
from app.services.srs_service import calculate_srs, get_interval_for_stage
from app.services.streak_service import calculate_streak, is_streak_at_risk
from app.services.suggestion_service import SuggestionService
from app.services.word_clustering import cluster_words

__all__ = [
    "record_event",
    "AuthService",
    "DashboardService",
    "DictionaryImportService",
    "EvaluateTranslationService",
    "LessonExerciseService",
    "LessonPreviewService",
    "LessonResumeService",
    "LessonStartService",
    "LessonSummaryService",
    "LlmLogger",
    "OnboardingService",
    "PromptService",
    "ReportService",
    "SuggestionService",
    "calculate_streak",
    "is_streak_at_risk",
    "calculate_srs",
    "get_interval_for_stage",
    "cluster_words",
    "validate_sentence_group",
    "validate_all_groups",
]
