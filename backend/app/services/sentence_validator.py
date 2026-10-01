"""Sentence validation service for LLM-generated content."""

from __future__ import annotations

import re
import unicodedata
from typing import List, Set, Tuple

from app.schemas.lesson_start import LlmSentenceGroup


def validate_sentence_group(
    group: LlmSentenceGroup,
    expected_words: List[Tuple[str, str]],  # [(lemma, pos), ...]
    avoid_sentences: List[str],
    all_generated_sentences: List[str],
) -> Tuple[bool, str]:
    """
    Validate a single sentence group from LLM response.
    
    Rules:
    1. surface_form found in sentence as whole word (Unicode boundaries)
    2. Forms don't overlap by position
    3. sentence not empty and ≤ 200 chars
    4. reference_translation not empty and ≤ 300 chars
    5. sentence doesn't contain Cyrillic
    6. reference_translation contains Cyrillic
    7. sentence doesn't match (after normalization) other sentences or avoid_sentences
    
    Args:
        group: LLM-generated sentence group
        expected_words: Expected (lemma, pos) pairs
        avoid_sentences: Sentences to avoid repeating
        all_generated_sentences: Other sentences already generated
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    sentence = group.sentence
    translation = group.reference_translation
    
    logger.info(f"Validating group {group.group_index}:")
    logger.info(f"  Sentence: {sentence}")
    logger.info(f"  Translation: {translation}")
    logger.info(f"  Expected words: {expected_words}")
    logger.info(f"  Actual words: {[(w.lemma, w.pos, w.surface_form) for w in group.words]}")
    
    # Rule 3: sentence not empty and ≤ 200 chars
    if not sentence or len(sentence.strip()) == 0:
        logger.warning(f"  ✗ Sentence is empty")
        return False, "Sentence is empty"
    
    if len(sentence) > 200:
        logger.warning(f"  ✗ Sentence too long: {len(sentence)} > 200")
        return False, f"Sentence too long: {len(sentence)} > 200"
    
    # Rule 4: translation not empty and ≤ 300 chars
    if not translation or len(translation.strip()) == 0:
        logger.warning(f"  ✗ Translation is empty")
        return False, "Translation is empty"
    
    if len(translation) > 300:
        logger.warning(f"  ✗ Translation too long: {len(translation)} > 300")
        return False, f"Translation too long: {len(translation)} > 300"
    
    # Rule 7: sentence doesn't contain Cyrillic
    if _contains_cyrillic(sentence):
        logger.warning(f"  ✗ Sentence contains Cyrillic characters")
        return False, "Sentence contains Cyrillic characters"
    
    # Rule 8: translation contains Cyrillic
    if not _contains_cyrillic(translation):
        logger.warning(f"  ✗ Translation doesn't contain Cyrillic characters")
        return False, "Translation doesn't contain Cyrillic characters"
    
    # Rule 9: sentence doesn't match other sentences
    normalized_sentence = _normalize_sentence(sentence)
    
    for other in all_generated_sentences:
        if _normalize_sentence(other) == normalized_sentence:
            logger.warning(f"  ✗ Sentence duplicates another generated sentence")
            return False, "Sentence duplicates another generated sentence"
    
    for avoid in avoid_sentences:
        if _normalize_sentence(avoid) == normalized_sentence:
            logger.warning(f"  ✗ Sentence duplicates an avoided sentence")
            return False, "Sentence duplicates an avoided sentence"
    
    # Rule 1: surface_form found in sentence as whole word
    word_positions = []  # Track positions to check for overlap
    
    for word in group.words:
        surface_form = word.surface_form
        
        # Find surface_form in sentence with Unicode word boundaries
        pattern = r'\b' + re.escape(surface_form) + r'\b'
        match = re.search(pattern, sentence, re.IGNORECASE | re.UNICODE)
        
        if not match:
            logger.warning(f"  ✗ Surface form '{surface_form}' not found in sentence '{sentence}'")
            return False, f"Surface form '{surface_form}' not found in sentence"
        
        # Track position for overlap check
        word_positions.append((match.start(), match.end()))
    
    # Rule 2: Forms don't overlap by position
    word_positions.sort()
    for i in range(len(word_positions) - 1):
        if word_positions[i][1] > word_positions[i + 1][0]:
            logger.warning(f"  ✗ Word forms overlap in sentence")
            return False, "Word forms overlap in sentence"
    
    # Check that expected words are present
    expected_set = set(expected_words)
    actual_set = {(w.lemma, w.pos) for w in group.words}
    
    logger.info(f"  Expected set: {expected_set}")
    logger.info(f"  Actual set: {actual_set}")
    
    if expected_set != actual_set:
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        return False, f"Word mismatch. Missing: {missing}, Extra: {extra}"
    
    return True, ""


def _contains_cyrillic(text: str) -> bool:
    """Check if text contains Cyrillic characters."""
    for char in text:
        if '\u0400' <= char <= '\u04FF':
            return True
    return False


def _normalize_sentence(sentence: str) -> str:
    """
    Normalize sentence for comparison.
    
    - Lowercase
    - NFC normalization
    - Remove extra whitespace
    """
    sentence = sentence.lower()
    sentence = unicodedata.normalize("NFC", sentence)
    sentence = re.sub(r'\s+', ' ', sentence).strip()
    return sentence


def validate_all_groups(
    groups: List[LlmSentenceGroup],
    expected_groups: List[List[Tuple[str, str]]],  # [[(lemma, pos), ...], ...]
    avoid_sentences: List[str],
) -> Tuple[List[int], List[int]]:
    """
    Validate all groups and separate valid from invalid.
    
    Args:
        groups: LLM-generated groups
        expected_groups: Expected words for each group
        avoid_sentences: Sentences to avoid
    
    Returns:
        Tuple of (valid_indices, invalid_indices)
    """
    valid_indices = []
    invalid_indices = []
    
    all_sentences = [g.sentence for g in groups]
    
    for idx, group in enumerate(groups):
        if idx >= len(expected_groups):
            invalid_indices.append(idx)
            continue
        
        expected_words = expected_groups[idx]
        
        is_valid, _ = validate_sentence_group(
            group=group,
            expected_words=expected_words,
            avoid_sentences=avoid_sentences,
            all_generated_sentences=[s for i, s in enumerate(all_sentences) if i != idx],
        )
        
        if is_valid:
            valid_indices.append(idx)
        else:
            invalid_indices.append(idx)
    
    return valid_indices, invalid_indices
