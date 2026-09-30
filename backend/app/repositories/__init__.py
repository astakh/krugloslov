"""Repository layer for data access."""

from app.repositories.user_repo import UserRepository
from app.repositories.word_repo import WordRepository, DictionaryRepository, normalize_lemma
from app.repositories.lesson_repo import LessonRepository, UserWordRepository

__all__ = [
    "UserRepository",
    "WordRepository",
    "DictionaryRepository",
    "LessonRepository",
    "UserWordRepository",
    "normalize_lemma",
]
