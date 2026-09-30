"""Word clustering service for lesson exercises."""

from __future__ import annotations

import hashlib
from typing import List, Tuple


def cluster_words(word_ids: List[int], seed: str) -> List[List[int]]:
    """
    Cluster words into groups for exercises.
    
    Rules:
    - k = ceil(N / 3) groups
    - Group sizes differ by at most 1
    - Smaller groups come first
    - Distribution is deterministic based on seed
    - Single word in group only allowed when N = 1
    
    Args:
        word_ids: List of word IDs to cluster
        seed: Seed for deterministic shuffling
    
    Returns:
        List of groups, each group is a list of word IDs
    
    Examples:
        1 → [[1]]
        4 → [[1, 2], [3, 4]]
        5 → [[1, 2], [3, 4, 5]]
        6 → [[1, 2, 3], [4, 5, 6]]
        7 → [[1, 2], [3, 4], [5, 6, 7]]
    """
    n = len(word_ids)
    
    if n == 0:
        return []
    
    if n == 1:
        return [word_ids]
    
    # Calculate number of groups: k = ceil(N / 3)
    k = (n + 2) // 3  # ceil(n / 3)
    
    # Calculate base size and remainder
    base_size = n // k
    remainder = n % k
    
    # Create groups: smaller groups first
    groups = []
    idx = 0
    
    # First (k - remainder) groups have size base_size
    for _ in range(k - remainder):
        groups.append(word_ids[idx:idx + base_size])
        idx += base_size
    
    # Last remainder groups have size base_size + 1
    for _ in range(remainder):
        groups.append(word_ids[idx:idx + base_size + 1])
        idx += base_size + 1
    
    # Deterministic shuffle within each group based on seed
    shuffled_groups = []
    for group_idx, group in enumerate(groups):
        # Create deterministic seed for this group
        group_seed = f"{seed}:group:{group_idx}"
        shuffled = _deterministic_shuffle(group, group_seed)
        shuffled_groups.append(shuffled)
    
    return shuffled_groups


def _deterministic_shuffle(items: List[int], seed: str) -> List[int]:
    """
    Deterministically shuffle a list based on seed.
    
    Uses SHA256 hash to generate permutation.
    """
    if len(items) <= 1:
        return items.copy()
    
    # Generate hash-based permutation
    result = items.copy()
    n = len(result)
    
    for i in range(n - 1, 0, -1):
        # Generate deterministic random number for this position
        hash_input = f"{seed}:{i}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        j = hash_value % (i + 1)
        
        # Swap
        result[i], result[j] = result[j], result[i]
    
    return result


def get_avoid_sentences(
    word_ids: List[int],
    max_sentences: int = 4,
    max_per_group: int = 2
) -> List[str]:
    """
    Get recent sentences containing these words to avoid repetition.
    
    Args:
        word_ids: Word IDs to check
        max_sentences: Maximum total sentences to return
        max_per_group: Maximum sentences per word group
    
    Returns:
        List of sentences to avoid
    """
    # This will be implemented in lesson_start_service
    # Placeholder for interface
    return []
