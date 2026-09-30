"""Streak calculation service."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Set, Tuple


def calculate_streak(
    completed_dates: Set[date],
    today: date,
) -> Tuple[int, int, bool]:
    """
    Calculate current streak, longest streak, and today_done status.
    
    Args:
        completed_dates: Set of dates when lessons were completed
        today: Current date in user's timezone
    
    Returns:
        Tuple of (current_streak, longest_streak, today_done)
    
    Algorithm:
        1. Clamp dates > today to today
        2. Determine anchor:
           - If today in dates: anchor = today
           - Else if today-1 in dates: anchor = today-1
           - Else: current = 0
        3. current = length of continuous chain ending at anchor
        4. longest = max continuous chain in all dates
        5. today_done = today in dates
    """
    # Clamp future dates to today
    valid_dates = {min(d, today) for d in completed_dates}
    
    if not valid_dates:
        return 0, 0, False
    
    today_done = today in valid_dates
    
    # Determine anchor
    if today_done:
        anchor = today
    elif (today - timedelta(days=1)) in valid_dates:
        anchor = today - timedelta(days=1)
    else:
        # No anchor, current streak is 0
        # But we still need to calculate longest
        current = 0
        longest = _calculate_longest_streak(valid_dates)
        return current, longest, today_done
    
    # Calculate current streak (continuous chain ending at anchor)
    current = 0
    check_date = anchor
    while check_date in valid_dates:
        current += 1
        check_date -= timedelta(days=1)
    
    # Calculate longest streak
    longest = _calculate_longest_streak(valid_dates)
    
    return current, longest, today_done


def _calculate_longest_streak(dates: Set[date]) -> int:
    """
    Calculate the longest continuous streak in a set of dates.
    
    Args:
        dates: Set of dates
    
    Returns:
        Length of longest continuous streak
    """
    if not dates:
        return 0
    
    sorted_dates = sorted(dates)
    longest = 1
    current = 1
    
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] == sorted_dates[i-1] + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    
    return longest


def is_streak_at_risk(current: int, today_done: bool) -> bool:
    """
    Check if streak is at risk (current > 0 but today not done).
    
    Args:
        current: Current streak length
        today_done: Whether today is in completed dates
    
    Returns:
        True if streak is at risk
    """
    return current > 0 and not today_done
