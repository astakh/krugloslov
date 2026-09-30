"""Spaced Repetition System (SRS) calculation."""

from __future__ import annotations

from typing import Literal, NamedTuple

# SRS intervals for each stage transition
INTERVALS = [1, 2, 3, 7, 11, 30]
MAX_STAGE = 6


class SrsResult(NamedTuple):
    """Result of SRS calculation."""
    new_stage: int
    due_lesson_number: int | None
    status: Literal["active", "mastered"]


def calculate_srs(
    stage: int,
    result: Literal["correct", "typo", "incorrect"],
    lesson_number: int,
) -> SrsResult:
    """
    Calculate new SRS state after reviewing a word.
    
    Args:
        stage: Current stage (0-6)
        result: Review result (correct/typo/incorrect)
        lesson_number: Current lesson number
    
    Returns:
        SrsResult with new_stage, due_lesson_number, status
    
    Rules:
        - success = result in (correct, typo)
        - interval(s) = INTERVALS[max(s - 1, 0)]
        - If success and stage == 6: return (6, NULL, 'mastered')
        - If success: new_stage = stage + 1
        - If error: new_stage = max(stage - 1, 0)
        - Return (new_stage, lesson_number + interval(new_stage), 'active')
    """
    if stage < 0 or stage > MAX_STAGE:
        raise ValueError(f"Stage must be 0-{MAX_STAGE}, got {stage}")
    
    success = result in ("correct", "typo")
    
    if success:
        if stage == MAX_STAGE:
            # Already mastered
            return SrsResult(
                new_stage=MAX_STAGE,
                due_lesson_number=None,
                status="mastered"
            )
        else:
            # Progress to next stage
            new_stage = stage + 1
    else:
        # Error: go back one stage (min 0)
        new_stage = max(stage - 1, 0)
    
    # Calculate next due lesson
    interval = INTERVALS[max(new_stage - 1, 0)]
    due_lesson_number = lesson_number + interval
    
    return SrsResult(
        new_stage=new_stage,
        due_lesson_number=due_lesson_number,
        status="active"
    )


def get_interval_for_stage(stage: int) -> int:
    """Get the interval for a given stage."""
    if stage < 0 or stage > MAX_STAGE:
        raise ValueError(f"Stage must be 0-{MAX_STAGE}, got {stage}")
    return INTERVALS[max(stage - 1, 0)]
