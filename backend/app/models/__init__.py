"""SQLAlchemy models package.

Import all models here so Alembic autogenerate can discover them.
"""

from app.models.base import Base
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.dictionary import Dictionary
from app.models.word import Word, VALID_POS, VALID_LEVELS
from app.models.dictionary_word import DictionaryWord
from app.models.learning_profile import LearningProfile
from app.models.user_word import UserWord, VALID_USER_WORD_STATUS, VALID_USER_WORD_SOURCE
from app.models.lesson import Lesson, VALID_LESSON_STATUS
from app.models.lesson_exercise import LessonExercise, VALID_EXERCISE_STATUS
from app.models.lesson_exercise_word import LessonExerciseWord, VALID_EXERCISE_WORD_RESULT
from app.models.lesson_exercise_suggestion import LessonExerciseSuggestion, VALID_SUGGESTION_STATE
from app.models.sentence_report import SentenceReport, VALID_REPORT_STATUS
from app.models.llm_call import LLMCall, VALID_LLM_PURPOSE, VALID_LLM_STATUS
from app.models.event import Event
from app.models.dictionary_import import DictionaryImport
from app.models.prompt import Prompt
from app.models.prompt_history import PromptHistory

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "Dictionary",
    "Word",
    "DictionaryWord",
    "LearningProfile",
    "UserWord",
    "Lesson",
    "LessonExercise",
    "LessonExerciseWord",
    "LessonExerciseSuggestion",
    "SentenceReport",
    "LLMCall",
    "Event",
    "DictionaryImport",
    "Prompt",
    "PromptHistory",
    "VALID_POS",
    "VALID_LEVELS",
    "VALID_USER_WORD_STATUS",
    "VALID_USER_WORD_SOURCE",
    "VALID_LESSON_STATUS",
    "VALID_EXERCISE_STATUS",
    "VALID_EXERCISE_WORD_RESULT",
    "VALID_SUGGESTION_STATE",
    "VALID_REPORT_STATUS",
    "VALID_LLM_PURPOSE",
    "VALID_LLM_STATUS",
]
