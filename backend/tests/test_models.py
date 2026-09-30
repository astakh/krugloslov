"""Unit tests for models and normalization logic (no database required)."""

from __future__ import annotations

import pytest

from app.repositories.word_repo import normalize_lemma
from app.models.word import VALID_POS, VALID_LEVELS
from app.models.user_word import VALID_USER_WORD_STATUS, VALID_USER_WORD_SOURCE
from app.models.lesson import VALID_LESSON_STATUS
from app.models.lesson_exercise import VALID_EXERCISE_STATUS
from app.models.lesson_exercise_word import VALID_EXERCISE_WORD_RESULT
from app.models.lesson_exercise_suggestion import VALID_SUGGESTION_STATE
from app.models.sentence_report import VALID_REPORT_STATUS
from app.models.llm_call import VALID_LLM_PURPOSE, VALID_LLM_STATUS
from app.constants import NATIVE_LANGUAGE, TARGET_LANGUAGE


class TestNormalizeLemma:
    """Tests for lemma normalization function."""

    def test_basic_casefold(self):
        assert normalize_lemma("Hello") == "hello"

    def test_trim_whitespace(self):
        assert normalize_lemma("  word  ") == "word"

    def test_nfc_normalization(self):
        # é as combining character (e + combining acute) vs precomposed é
        combining = "e\u0301"  # e + combining acute accent
        precomposed = "\u00e9"  # precomposed é
        assert normalize_lemma(combining) == normalize_lemma(precomposed)

    def test_combined_operations(self):
        assert normalize_lemma("  Café  ") == "café"

    def test_empty_after_trim(self):
        assert normalize_lemma("   ") == ""


class TestConstants:
    """Tests for application constants."""

    def test_native_language(self):
        assert NATIVE_LANGUAGE == "ru"

    def test_target_language(self):
        assert TARGET_LANGUAGE == "en"


class TestValidEnums:
    """Tests that enum tuples contain expected values."""

    def test_pos_values(self):
        expected = {"noun", "verb", "adj", "adv", "pron", "prep", "conj", "num", "det", "intj"}
        assert set(VALID_POS) == expected

    def test_level_values(self):
        expected = {"A1", "A2", "B1", "B2", "C1", "C2"}
        assert set(VALID_LEVELS) == expected

    def test_user_word_status_values(self):
        expected = {"active", "mastered", "ignored"}
        assert set(VALID_USER_WORD_STATUS) == expected

    def test_user_word_source_values(self):
        expected = {"dictionary", "suggestion", "decline"}
        assert set(VALID_USER_WORD_SOURCE) == expected

    def test_lesson_status_values(self):
        expected = {"in_progress", "completed", "abandoned"}
        assert set(VALID_LESSON_STATUS) == expected

    def test_exercise_status_values(self):
        expected = {"pending", "evaluated"}
        assert set(VALID_EXERCISE_STATUS) == expected

    def test_exercise_word_result_values(self):
        expected = {"correct", "typo", "incorrect"}
        assert set(VALID_EXERCISE_WORD_RESULT) == expected

    def test_suggestion_state_values(self):
        expected = {"suggested", "added", "ignored"}
        assert set(VALID_SUGGESTION_STATE) == expected

    def test_report_status_values(self):
        expected = {"new", "processed"}
        assert set(VALID_REPORT_STATUS) == expected

    def test_llm_purpose_values(self):
        expected = {"generate", "evaluate"}
        assert set(VALID_LLM_PURPOSE) == expected

    def test_llm_status_values(self):
        expected = {"ok", "http_error", "timeout", "invalid_json", "invalid_schema", "validation_failed"}
        assert set(VALID_LLM_STATUS) == expected
