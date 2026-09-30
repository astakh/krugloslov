"""Tests for SRS calculation."""

from __future__ import annotations

import pytest

from app.services.srs_service import calculate_srs, get_interval_for_stage


class TestSrsCalculation:
    """Test SRS calculation with all required cases."""
    
    def test_stage_0_correct(self):
        """stage 0, correct → stage 1, due 11, active"""
        result = calculate_srs(stage=0, result="correct", lesson_number=10)
        assert result.new_stage == 1
        assert result.due_lesson_number == 11
        assert result.status == "active"
    
    def test_stage_0_typo(self):
        """stage 0, typo → stage 1, due 11, active"""
        result = calculate_srs(stage=0, result="typo", lesson_number=10)
        assert result.new_stage == 1
        assert result.due_lesson_number == 11
        assert result.status == "active"
    
    def test_stage_0_incorrect(self):
        """stage 0, incorrect → stage 0, due 11, active"""
        result = calculate_srs(stage=0, result="incorrect", lesson_number=10)
        assert result.new_stage == 0
        assert result.due_lesson_number == 11
        assert result.status == "active"
    
    def test_stage_1_correct(self):
        """stage 1, correct → stage 2, due 12, active"""
        result = calculate_srs(stage=1, result="correct", lesson_number=10)
        assert result.new_stage == 2
        assert result.due_lesson_number == 12
        assert result.status == "active"
    
    def test_stage_2_correct(self):
        """stage 2, correct → stage 3, due 13, active"""
        result = calculate_srs(stage=2, result="correct", lesson_number=10)
        assert result.new_stage == 3
        assert result.due_lesson_number == 13
        assert result.status == "active"
    
    def test_stage_3_correct(self):
        """stage 3, correct → stage 4, due 17, active"""
        result = calculate_srs(stage=3, result="correct", lesson_number=10)
        assert result.new_stage == 4
        assert result.due_lesson_number == 17
        assert result.status == "active"
    
    def test_stage_4_correct(self):
        """stage 4, correct → stage 5, due 21, active"""
        result = calculate_srs(stage=4, result="correct", lesson_number=10)
        assert result.new_stage == 5
        assert result.due_lesson_number == 21
        assert result.status == "active"
    
    def test_stage_5_correct(self):
        """stage 5, correct → stage 6, due 40, active"""
        result = calculate_srs(stage=5, result="correct", lesson_number=10)
        assert result.new_stage == 6
        assert result.due_lesson_number == 40
        assert result.status == "active"
    
    def test_stage_6_correct(self):
        """stage 6, correct → stage 6, due NULL, mastered"""
        result = calculate_srs(stage=6, result="correct", lesson_number=10)
        assert result.new_stage == 6
        assert result.due_lesson_number is None
        assert result.status == "mastered"
    
    def test_stage_6_incorrect(self):
        """stage 6, incorrect → stage 5, due 21, active"""
        result = calculate_srs(stage=6, result="incorrect", lesson_number=10)
        assert result.new_stage == 5
        assert result.due_lesson_number == 21
        assert result.status == "active"
    
    def test_stage_3_incorrect(self):
        """stage 3, incorrect → stage 2, due 12, active"""
        result = calculate_srs(stage=3, result="incorrect", lesson_number=10)
        assert result.new_stage == 2
        assert result.due_lesson_number == 12
        assert result.status == "active"
    
    def test_stage_1_incorrect(self):
        """stage 1, incorrect → stage 0, due 11, active"""
        result = calculate_srs(stage=1, result="incorrect", lesson_number=10)
        assert result.new_stage == 0
        assert result.due_lesson_number == 11
        assert result.status == "active"
    
    def test_invalid_stage_negative(self):
        """Negative stage should raise ValueError"""
        with pytest.raises(ValueError):
            calculate_srs(stage=-1, result="correct", lesson_number=10)
    
    def test_invalid_stage_too_high(self):
        """Stage > 6 should raise ValueError"""
        with pytest.raises(ValueError):
            calculate_srs(stage=7, result="correct", lesson_number=10)
    
    def test_different_lesson_numbers(self):
        """Test with different lesson numbers"""
        # Lesson 5
        result = calculate_srs(stage=0, result="correct", lesson_number=5)
        assert result.due_lesson_number == 6
        
        # Lesson 100
        result = calculate_srs(stage=3, result="correct", lesson_number=100)
        assert result.due_lesson_number == 107


class TestGetIntervalForStage:
    """Test interval calculation for each stage."""
    
    def test_stage_0(self):
        """Stage 0 interval"""
        assert get_interval_for_stage(0) == 1
    
    def test_stage_1(self):
        """Stage 1 interval"""
        assert get_interval_for_stage(1) == 1
    
    def test_stage_2(self):
        """Stage 2 interval"""
        assert get_interval_for_stage(2) == 2
    
    def test_stage_3(self):
        """Stage 3 interval"""
        assert get_interval_for_stage(3) == 3
    
    def test_stage_4(self):
        """Stage 4 interval"""
        assert get_interval_for_stage(4) == 7
    
    def test_stage_5(self):
        """Stage 5 interval"""
        assert get_interval_for_stage(5) == 11
    
    def test_stage_6(self):
        """Stage 6 interval"""
        assert get_interval_for_stage(6) == 30
    
    def test_invalid_stage(self):
        """Invalid stage should raise ValueError"""
        with pytest.raises(ValueError):
            get_interval_for_stage(-1)
        with pytest.raises(ValueError):
            get_interval_for_stage(7)
