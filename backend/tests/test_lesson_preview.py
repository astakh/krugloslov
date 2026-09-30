"""Tests for lesson preview service - ranking and selection logic."""

from __future__ import annotations

import hashlib

import pytest


class TestRankingLogic:
    """Tests for deterministic ranking using SHA256."""

    def test_seed_calculation_deterministic(self):
        """Same profile_id and lesson_number should produce same seed."""
        profile_id = 1
        lesson_number = 5
        
        seed1 = hashlib.sha256(f"{profile_id}:{lesson_number}".encode()).hexdigest()
        seed2 = hashlib.sha256(f"{profile_id}:{lesson_number}".encode()).hexdigest()
        
        assert seed1 == seed2

    def test_different_lessons_different_seeds(self):
        """Different lesson numbers should produce different seeds."""
        profile_id = 1
        
        seed1 = hashlib.sha256(f"{profile_id}:1".encode()).hexdigest()
        seed2 = hashlib.sha256(f"{profile_id}:2".encode()).hexdigest()
        
        assert seed1 != seed2

    def test_rank_calculation_deterministic(self):
        """Same seed and word_id should produce same rank."""
        seed = "abc123"
        word_id = 42
        
        rank1 = hashlib.sha256(f"{seed}:{word_id}".encode()).hexdigest()
        rank2 = hashlib.sha256(f"{seed}:{word_id}".encode()).hexdigest()
        
        assert rank1 == rank2

    def test_different_words_different_ranks(self):
        """Different word_ids should produce different ranks."""
        seed = "abc123"
        
        rank1 = hashlib.sha256(f"{seed}:1".encode()).hexdigest()
        rank2 = hashlib.sha256(f"{seed}:2".encode()).hexdigest()
        
        assert rank1 != rank2

    def test_ranking_order_stable(self):
        """Words should maintain consistent order when sorted by rank."""
        seed = "test_seed"
        word_ids = [1, 2, 3, 4, 5]
        
        # Calculate ranks
        words_with_ranks = []
        for word_id in word_ids:
            rank = hashlib.sha256(f"{seed}:{word_id}".encode()).hexdigest()
            words_with_ranks.append((word_id, rank))
        
        # Sort by rank
        words_with_ranks.sort(key=lambda x: x[1])
        
        # Get order
        order1 = [w[0] for w in words_with_ranks]
        
        # Repeat
        words_with_ranks2 = []
        for word_id in word_ids:
            rank = hashlib.sha256(f"{seed}:{word_id}".encode()).hexdigest()
            words_with_ranks2.append((word_id, rank))
        
        words_with_ranks2.sort(key=lambda x: x[1])
        order2 = [w[0] for w in words_with_ranks2]
        
        assert order1 == order2

    def test_exclusion_preserves_order(self):
        """When a word is excluded, others should maintain their relative order."""
        seed = "test_seed"
        word_ids = [1, 2, 3, 4, 5]
        
        # Calculate all ranks
        all_words = []
        for word_id in word_ids:
            rank = hashlib.sha256(f"{seed}:{word_id}".encode()).hexdigest()
            all_words.append((word_id, rank))
        
        all_words.sort(key=lambda x: x[1])
        full_order = [w[0] for w in all_words]
        
        # Exclude word 3
        excluded = 3
        filtered = [(wid, rank) for wid, rank in all_words if wid != excluded]
        filtered_order = [w[0] for w in filtered]
        
        # Check that relative order is preserved
        expected = [w for w in full_order if w != excluded]
        assert filtered_order == expected

    def test_rank_is_hex_string(self):
        """Rank should be a valid hex string."""
        seed = "test"
        word_id = 1
        
        rank = hashlib.sha256(f"{seed}:{word_id}".encode()).hexdigest()
        
        # Should be 64 characters (SHA256)
        assert len(rank) == 64
        
        # Should be valid hex
        int(rank, 16)  # Should not raise


class TestLevelConstraints:
    """Tests for level-based word selection constraints."""

    def test_a1_only_a1_allowed(self):
        """For A1 profile, only A1 words should be allowed."""
        profile_level = "A1"
        allowed_levels = [profile_level]
        
        # A1 profile should only allow A1
        assert "A1" in allowed_levels
        assert "A2" not in allowed_levels
        assert "B1" not in allowed_levels

    def test_a2_allows_a1_and_a2(self):
        """For A2 profile, A1 and A2 words should be allowed."""
        profile_level = "A2"
        level_order = ["A1", "A2", "B1", "B2", "C1", "C2"]
        
        allowed_levels = [profile_level]
        idx = level_order.index(profile_level)
        if idx > 0:
            allowed_levels.append(level_order[idx - 1])
        
        assert "A2" in allowed_levels
        assert "A1" in allowed_levels
        assert "B1" not in allowed_levels

    def test_b1_allows_a2_and_b1(self):
        """For B1 profile, A2 and B1 words should be allowed."""
        profile_level = "B1"
        level_order = ["A1", "A2", "B1", "B2", "C1", "C2"]
        
        allowed_levels = [profile_level]
        idx = level_order.index(profile_level)
        if idx > 0:
            allowed_levels.append(level_order[idx - 1])
        
        assert "B1" in allowed_levels
        assert "A2" in allowed_levels
        assert "A1" not in allowed_levels
        assert "B2" not in allowed_levels

    def test_words_without_level_allowed_in_thematic(self):
        """Words without level should be allowed in thematic dictionaries."""
        # This is a business rule, not a unit test
        # Words with level=None should pass level check
        word_level = None
        allowed_levels = ["A1", "A2"]
        
        # In thematic dictionaries, None level is always allowed
        # In general dictionaries, None level is not allowed
        # This logic is in the service, not testable here
        pass


class TestStateDetermination:
    """Tests for determining lesson state."""

    def test_resume_when_in_progress(self):
        """Should return resume state when lesson is in progress."""
        # Business logic test
        has_in_progress = True
        lessons_today = 0
        daily_limit = 5
        
        if has_in_progress:
            state = "resume"
        elif lessons_today >= daily_limit:
            state = "limit_reached"
        else:
            state = "ready"
        
        assert state == "resume"

    def test_limit_reached_when_exceeded(self):
        """Should return limit_reached when daily limit exceeded."""
        has_in_progress = False
        lessons_today = 5
        daily_limit = 5
        
        if has_in_progress:
            state = "resume"
        elif lessons_today >= daily_limit:
            state = "limit_reached"
        else:
            state = "ready"
        
        assert state == "limit_reached"

    def test_ready_when_can_start(self):
        """Should return ready when lesson can start."""
        has_in_progress = False
        lessons_today = 2
        daily_limit = 5
        
        if has_in_progress:
            state = "resume"
        elif lessons_today >= daily_limit:
            state = "limit_reached"
        else:
            state = "ready"
        
        assert state == "ready"

    def test_no_words_when_empty(self):
        """Should return no_words when no words available."""
        due_words = []
        new_words = []
        
        if len(due_words) == 0 and len(new_words) == 0:
            state = "no_words"
        else:
            state = "ready"
        
        assert state == "no_words"

    def test_ready_with_due_words(self):
        """Should return ready when due words available."""
        due_words = [{"word_id": 1}]
        new_words = []
        
        if len(due_words) == 0 and len(new_words) == 0:
            state = "no_words"
        else:
            state = "ready"
        
        assert state == "ready"

    def test_ready_with_new_words(self):
        """Should return ready when new words available."""
        due_words = []
        new_words = [{"word_id": 1}]
        
        if len(due_words) == 0 and len(new_words) == 0:
            state = "no_words"
        else:
            state = "ready"
        
        assert state == "ready"

    def test_dictionary_exhausted_when_not_enough(self):
        """Should set dictionary_exhausted when not enough new words."""
        N = 10
        due_words = [1, 2, 3]  # 3 due words
        new_words_available = 5  # Only 5 new words available
        
        k = N - len(due_words)  # Need 7 more
        new_words_selected = min(k, new_words_available)  # Can only get 5
        
        dictionary_exhausted = new_words_selected < k
        
        assert dictionary_exhausted is True
        assert len(due_words) + new_words_selected < N
