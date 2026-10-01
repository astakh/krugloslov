"""LLM response adapter for flexible JSON format handling."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.schemas.lesson_start import LlmGenerateResponse, LlmSentenceGroup, LlmSentenceWord

logger = logging.getLogger(__name__)


def adapt_llm_response(
    raw_response: Dict[str, Any],
    expected_groups: List[List[Dict[str, str]]]
) -> LlmGenerateResponse:
    """
    Adapt LLM response to expected format.
    
    LLM may return different JSON structures. This function normalizes them
    to the expected LlmGenerateResponse format.
    
    Args:
        raw_response: Raw JSON response from LLM
        expected_groups: List of word groups with lemma and pos
        
    Returns:
        Normalized LlmGenerateResponse
        
    Raises:
        ValueError: If response cannot be adapted
    """
    logger.debug(f"Adapting LLM response: {raw_response}")
    
    # Try to extract sentences/groups from response
    sentences_data = None
    
    # Case 1: {"sentences": [...]}
    if "sentences" in raw_response:
        sentences_data = raw_response["sentences"]
        logger.debug("Found 'sentences' key in response")
    
    # Case 2: {"groups": [...]} with simple format
    elif "groups" in raw_response:
        groups = raw_response["groups"]
        if groups and isinstance(groups[0], dict):
            # Check if it's simple format (english/russian) or full format
            if "english" in groups[0] or "russian" in groups[0]:
                sentences_data = groups
                logger.debug("Found 'groups' key with simple format")
            elif "sentence" in groups[0]:
                # Already in correct format
                logger.debug("Found 'groups' key with full format")
                return _validate_full_format(raw_response)
    
    # Case 3: Direct array
    elif isinstance(raw_response, list):
        sentences_data = raw_response
        logger.debug("Response is a direct array")
    
    # Cannot adapt
    if sentences_data is None:
        raise ValueError(
            f"Cannot adapt LLM response: unknown format. "
            f"Keys: {list(raw_response.keys())}"
        )
    
    # Convert simple format to full format
    return _convert_simple_to_full(sentences_data, expected_groups)


def _convert_simple_to_full(
    sentences_data: List[Dict[str, Any]],
    expected_groups: List[List[Dict[str, str]]]
) -> LlmGenerateResponse:
    """
    Convert simple sentence format to full format with word details.
    
    Simple format: {"english": "...", "russian": "..."}
    Full format: {
        "group_index": 0,
        "sentence": "...",
        "reference_translation": "...",
        "words": [{"lemma": "...", "pos": "...", "surface_form": "..."}]
    }
    """
    groups = []
    
    for idx, sentence_item in enumerate(sentences_data):
        # Extract sentence and translation
        sentence = None
        translation = None
        
        # Try different key names
        for key in ["sentence", "english"]:
            if key in sentence_item:
                sentence = sentence_item[key]
                break
        
        for key in ["reference_translation", "russian", "translation"]:
            if key in sentence_item:
                translation = sentence_item[key]
                break
        
        if sentence is None or translation is None:
            logger.warning(f"Cannot extract sentence/translation from item {idx}: {sentence_item}")
            continue
        
        # Create word entries from expected groups
        words = []
        if idx < len(expected_groups):
            for word_info in expected_groups[idx]:
                # Try to find surface form in sentence
                lemma = word_info.get("lemma", "")
                pos = word_info.get("pos", "")
                
                # Simple heuristic: use lemma as surface form
                # In production, we could use NLP to find actual surface form
                surface_form = _find_surface_form(sentence, lemma)
                
                words.append(LlmSentenceWord(
                    lemma=lemma,
                    pos=pos,
                    surface_form=surface_form
                ))
        
        groups.append(LlmSentenceGroup(
            group_index=idx,
            sentence=sentence,
            reference_translation=translation,
            words=words
        ))
    
    if not groups:
        raise ValueError("No valid groups could be extracted from LLM response")
    
    return LlmGenerateResponse(groups=groups)


def _find_surface_form(sentence: str, lemma: str) -> str:
    """
    Find surface form of a word in a sentence.
    
    Simple heuristic: look for word variations in sentence.
    """
    import re
    
    if not lemma:
        return lemma
    
    # Try to find exact match
    if lemma.lower() in sentence.lower():
        # Find the actual form in sentence
        pattern = re.compile(r'\b' + re.escape(lemma) + r'\b', re.IGNORECASE)
        match = pattern.search(sentence)
        if match:
            return match.group(0)
    
    # Try common variations
    variations = [
        lemma,
        lemma + "s",      # plural
        lemma + "ed",      # past tense
        lemma + "ing",     # gerund
        lemma + "er",      # comparative
        lemma + "est",     # superlative
    ]
    
    # For verbs, try common conjugations
    if lemma.endswith("e"):
        variations.extend([
            lemma[:-1] + "ing",  # running
            lemma + "d",          # liked
        ])
    
    for variant in variations:
        if variant.lower() in sentence.lower():
            pattern = re.compile(r'\b' + re.escape(variant) + r'\b', re.IGNORECASE)
            match = pattern.search(sentence)
            if match:
                return match.group(0)
    
    # Fallback to lemma
    return lemma


def _validate_full_format(raw_response: Dict[str, Any]) -> LlmGenerateResponse:
    """Validate response that's already in full format."""
    try:
        return LlmGenerateResponse(**raw_response)
    except Exception as e:
        raise ValueError(f"Invalid full format response: {e}")
