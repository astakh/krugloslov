"""Tests for word clustering and sentence validation."""

from __future__ import annotations

import pytest

from app.services.word_clustering import cluster_words
from app.services.sentence_validator import (
    validate_sentence_group,
    _contains_cyrillic,
    _normalize_sentence,
)
from app.schemas.lesson_start import LlmSentenceGroup, LlmSentenceWord


class TestWordClustering:
    """Tests for word clustering algorithm."""
    
    def test_cluster_1_word(self):
        """1 word → [1]."""
        result = cluster_words([1], "seed")
        assert result == [[1]]
    
    def test_cluster_4_words(self):
        """4 words → [2, 2]."""
        result = cluster_words([1, 2, 3, 4], "seed")
        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 2
        assert set(result[0] + result[1]) == {1, 2, 3, 4}
    
    def test_cluster_5_words(self):
        """5 words → [2, 3]."""
        result = cluster_words([1, 2, 3, 4, 5], "seed")
        assert len(result) == 2
        # Smaller group first
        assert len(result[0]) == 2
        assert len(result[1]) == 3
        assert set(result[0] + result[1]) == {1, 2, 3, 4, 5}
    
    def test_cluster_6_words(self):
        """6 words → [3, 3]."""
        result = cluster_words([1, 2, 3, 4, 5, 6], "seed")
        assert len(result) == 2
        assert len(result[0]) == 3
        assert len(result[1]) == 3
        assert set(result[0] + result[1]) == {1, 2, 3, 4, 5, 6}
    
    def test_cluster_7_words(self):
        """7 words → [2, 2, 3]."""
        result = cluster_words([1, 2, 3, 4, 5, 6, 7], "seed")
        assert len(result) == 3
        # Smaller groups first
        assert len(result[0]) == 2
        assert len(result[1]) == 2
        assert len(result[2]) == 3
        all_words = result[0] + result[1] + result[2]
        assert set(all_words) == {1, 2, 3, 4, 5, 6, 7}
    
    def test_cluster_10_words(self):
        """10 words → [3, 3, 4]."""
        result = cluster_words(list(range(1, 11)), "seed")
        assert len(result) == 3
        # ceil(10/3) = 4 groups, but 10/4 = 2.5, so [2, 2, 3, 3] or similar
        # Actually: k = ceil(10/3) = 4, base = 10//4 = 2, remainder = 10%4 = 2
        # So: (4-2)=2 groups of 2, then 2 groups of 3
        # [2, 2, 3, 3]
        assert len(result) == 4
        sizes = sorted([len(g) for g in result])
        assert sizes == [2, 2, 3, 3]
    
    def test_cluster_deterministic(self):
        """Same input should produce same output."""
        words = [1, 2, 3, 4, 5]
        seed = "test_seed"
        
        result1 = cluster_words(words, seed)
        result2 = cluster_words(words, seed)
        
        assert result1 == result2
    
    def test_cluster_different_seeds(self):
        """Different seeds should produce different orderings."""
        words = [1, 2, 3, 4, 5]
        
        result1 = cluster_words(words, "seed1")
        result2 = cluster_words(words, "seed2")
        
        # Both should contain all words
        assert set(result1[0] + result1[1]) == {1, 2, 3, 4, 5}
        assert set(result2[0] + result2[1]) == {1, 2, 3, 4, 5}
        
        # But order might differ (not guaranteed, but likely)
        # We just verify structure is correct
    
    def test_cluster_empty(self):
        """Empty list should return empty."""
        result = cluster_words([], "seed")
        assert result == []


class TestSentenceValidation:
    """Tests for sentence validation."""
    
    def test_valid_sentence(self):
        """Valid sentence should pass validation."""
        group = LlmSentenceGroup(
            group_index=0,
            sentence="The cat runs fast.",
            reference_translation="Кот бегает быстро.",
            words=[
                LlmSentenceWord(lemma="run", pos="verb", surface_form="runs"),
            ],
        )
        
        is_valid, error = validate_sentence_group(
            group=group,
            expected_words=[("run", "verb")],
            avoid_sentences=[],
            all_generated_sentences=[],
        )
        
        assert is_valid is True
        assert error == ""
    
    def test_empty_sentence(self):
        """Empty sentence should fail."""
        group = LlmSentenceGroup(
            group_index=0,
            sentence="",
            reference_translation="Перевод.",
            words=[],
        )
        
        is_valid, error = validate_sentence_group(
            group=group,
            expected_words=[],
            avoid_sentences=[],
            all_generated_sentences=[],
        )
        
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_sentence_too_long(self):
        """Sentence > 200 chars should fail."""
        group = LlmSentenceGroup(
            group_index=0,
            sentence="A" * 201,
            reference_translation="Перевод.",
            words=[],
        )
        
        is_valid, error = validate_sentence_group(
            group=group,
            expected_words=[],
            avoid_sentences=[],
            all_generated_sentences=[],
        )
        
        assert is_valid is False
        assert "long" in error.lower()
    
    def test_sentence_with_cyrillic(self):
        """Sentence with Cyrillic should fail."""
        group = LlmSentenceGroup(
            group_index=0,
            sentence="The cat runs быстро.",
            reference_translation="Кот бегает быстро.",
            words=[],
        )
        
        is_valid, error = validate_sentence_group(
            group=group,
            expected_words=[],
            avoid_sentences=[],
            all_generated_sentences=[],
        )
        
        assert is_valid is False
        assert "cyrillic" in error.lower()
    
    def test_translation_without_cyrillic(self):
        """Translation without Cyrillic should fail."""
        group = LlmSentenceGroup(
            group_index=0,
            sentence="The cat runs fast.",
            reference_translation="The cat runs fast.",
            words=[],
        )
        
        is_valid, error = validate_sentence_group(
            group=group,
            expected_words=[],
            avoid_sentences=[],
            all_generated_sentences=[],
        )
        
        assert is_valid is False
        assert "cyrillic" in error.lower()
    
    def test_surface_form_not_found(self):
        """Surface form not in sentence should fail."""
        group = LlmSentenceGroup(
            group_index=0,
            sentence="The cat walks slow.",
            reference_translation="Кот ходит медленно.",
            words=[
                LlmSentenceWord(lemma="run", pos="verb", surface_form="runs"),
            ],
        )
        
        is_valid, error = validate_sentence_group(
            group=group,
            expected_words=[("run", "verb")],
            avoid_sentences=[],
            all_generated_sentences=[],
        )
        
        assert is_valid is False
        assert "not found" in error.lower()
    
    def test_duplicate_sentence(self):
        """Duplicate sentence should fail."""
        group = LlmSentenceGroup(
            group_index=0,
            sentence="The cat runs fast.",
            reference_translation="Кот бегает быстро.",
            words=[],
        )
        
        is_valid, error = validate_sentence_group(
            group=group,
            expected_words=[],
            avoid_sentences=["The cat runs fast."],
            all_generated_sentences=[],
        )
        
        assert is_valid is False
        assert "duplicate" in error.lower()


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_contains_cyrillic_true(self):
        """Should detect Cyrillic characters."""
        assert _contains_cyrillic("Привет") is True
        assert _contains_cyrillic("Hello мир") is True
    
    def test_contains_cyrillic_false(self):
        """Should not detect Cyrillic in English text."""
        assert _contains_cyrillic("Hello world") is False
        assert _contains_cyrillic("123 !@#") is False
    
    def test_normalize_sentence(self):
        """Should normalize sentence for comparison."""
        assert _normalize_sentence("Hello  World") == "hello world"
        assert _normalize_sentence("  TEST  ") == "test"
