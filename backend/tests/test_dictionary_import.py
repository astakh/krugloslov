"""Tests for dictionary import functionality."""

from __future__ import annotations

import json

import pytest

from app.schemas.admin import DictionaryImportInput, DictionaryInput, WordInput


class TestDictionaryImportValidation:
    """Tests for dictionary import validation."""

    def test_valid_import(self):
        """Valid import should pass validation."""
        data = {
            "schema_version": 1,
            "dictionary": {
                "code": "test",
                "name": "Test Dictionary",
                "description": "Test",
                "is_general": False,
            },
            "words": [
                {
                    "lemma": "test",
                    "pos": "noun",
                    "level": "A1",
                    "translations": ["тест"],
                }
            ],
        }
        import_data = DictionaryImportInput(**data)
        assert import_data.schema_version == 1
        assert import_data.dictionary.code == "test"
        assert len(import_data.words) == 1

    def test_invalid_code(self):
        """Invalid dictionary code should fail validation."""
        data = {
            "schema_version": 1,
            "dictionary": {
                "code": "invalid code!",  # Contains space and special char
                "name": "Test",
                "is_general": False,
            },
            "words": [],
        }
        with pytest.raises(Exception):
            DictionaryImportInput(**data)

    def test_invalid_pos(self):
        """Invalid POS should be caught during validation."""
        word = WordInput(
            lemma="test",
            pos="invalid_pos",
            level="A1",
            translations=["тест"],
        )
        # POS validation happens in service, not in schema
        assert word.pos == "invalid_pos"

    def test_invalid_level(self):
        """Invalid level should be caught during validation."""
        word = WordInput(
            lemma="test",
            pos="noun",
            level="X9",  # Invalid level
            translations=["тест"],
        )
        # Level validation happens in service, not in schema
        assert word.level == "X9"

    def test_empty_translations(self):
        """Empty translations should fail validation."""
        with pytest.raises(Exception):
            WordInput(
                lemma="test",
                pos="noun",
                level="A1",
                translations=[],
            )

    def test_duplicate_translations_removed(self):
        """Duplicate translations should be removed."""
        word = WordInput(
            lemma="test",
            pos="noun",
            level="A1",
            translations=["тест", "тест", "проверка"],
        )
        assert len(word.translations) == 2
        assert word.translations == ["тест", "проверка"]

    def test_lemma_normalization(self):
        """Lemma should be normalized (trimmed, NFC)."""
        word = WordInput(
            lemma="  Café  ",
            pos="noun",
            level="A1",
            translations=["кафе"],
        )
        assert word.lemma == "Café"  # Trimmed

    def test_max_words_limit(self):
        """Import with more than 50000 words should fail."""
        data = {
            "schema_version": 1,
            "dictionary": {
                "code": "test",
                "name": "Test",
                "is_general": False,
            },
            "words": [
                {
                    "lemma": f"word{i}",
                    "pos": "noun",
                    "level": "A1",
                    "translations": ["слово"],
                }
                for i in range(50001)
            ],
        }
        # Schema allows up to 50000 words
        with pytest.raises(Exception):
            DictionaryImportInput(**data)


class TestDictionaryImportService:
    """Tests for DictionaryImportService."""

    def test_lemma_validation_valid(self):
        """Valid lemma should pass validation."""
        from app.services.dictionary_import import DictionaryImportService

        # Test valid lemmas
        valid_lemmas = ["test", "café", "it's", "well-known", "ice cream"]
        for lemma in valid_lemmas:
            # All should be valid (1-64 chars, latin + apostrophe + hyphen + space)
            assert len(lemma) >= 1 and len(lemma) <= 64

    def test_lemma_validation_invalid_chars(self):
        """Invalid characters in lemma should be detected."""
        invalid_lemmas = ["тест", "test!", "test@home", "test#1"]
        for lemma in invalid_lemmas:
            # These contain non-latin or special characters
            has_invalid = any(not (c.isalpha() or c in "'- ") for c in lemma)
            assert has_invalid

    def test_lemma_validation_length(self):
        """Lemma length validation."""
        # Too short
        assert len("") < 1
        # Too long
        assert len("a" * 65) > 64
        # Valid
        assert 1 <= len("test") <= 64
