"""LLM response adapter for evaluation responses."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.schemas.lesson_evaluate import (
    LlmEvaluateResponse,
    LlmWordEvaluation,
    LlmSuggestedWord,
)

logger = logging.getLogger(__name__)


def adapt_evaluation_response(
    raw_response: Dict[str, Any],
    expected_words: List[Dict[str, str]]
) -> LlmEvaluateResponse:
    """
    Adapt LLM evaluation response to expected format.
    
    LLM may return different JSON structures. This function normalizes them
    to the expected LlmEvaluateResponse format.
    
    Args:
        raw_response: Raw JSON response from LLM
        expected_words: List of expected words with lemma and pos
        
    Returns:
        Normalized LlmEvaluateResponse
        
    Raises:
        ValueError: If response cannot be adapted
    """
    logger.debug(f"Adapting evaluation response: {raw_response}")
    
    # Try to extract evaluations from response
    evaluations_data = None
    
    # Case 1: {"evaluations": [...]}
    if "evaluations" in raw_response:
        evaluations_data = raw_response["evaluations"]
        logger.debug("Found 'evaluations' key in response")
    
    # Case 2: {"results": [...]}
    elif "results" in raw_response:
        evaluations_data = raw_response["results"]
        logger.debug("Found 'results' key in response")
    
    # Case 3: Direct array
    elif isinstance(raw_response, list):
        evaluations_data = raw_response
        logger.debug("Response is a direct array")
    
    # Cannot adapt
    if evaluations_data is None:
        raise ValueError(
            f"Cannot adapt LLM evaluation response: unknown format. "
            f"Keys: {list(raw_response.keys())}"
        )
    
    # Convert to LlmWordEvaluation objects
    evaluations = []
    for eval_item in evaluations_data:
        # Extract word info
        lemma = None
        pos = None
        
        # Try different key names
        for key in ["lemma", "word"]:
            if key in eval_item:
                lemma = eval_item[key]
                break
        
        for key in ["pos", "part_of_speech"]:
            if key in eval_item:
                pos = eval_item[key]
                break
        
        # Extract result
        result = eval_item.get("result", eval_item.get("status", "incorrect"))
        
        # Extract feedback
        feedback = eval_item.get("feedback", eval_item.get("comment", ""))
        
        # Extract user_fragment
        user_fragment = eval_item.get("user_fragment", eval_item.get("fragment"))
        
        if lemma is None:
            logger.warning(f"Cannot extract lemma from evaluation item: {eval_item}")
            continue
        
        evaluations.append(LlmWordEvaluation(
            lemma=lemma,
            pos=pos or "unknown",
            result=result,
            feedback=feedback,
            user_fragment=user_fragment
        ))
    
    # Extract suggested words if present
    suggested_words = []
    if "new_suggested_words" in raw_response:
        for sugg_item in raw_response["new_suggested_words"]:
            lemma = sugg_item.get("lemma")
            pos = sugg_item.get("pos", "unknown")
            translations = sugg_item.get("translations", [])
            
            if lemma:
                suggested_words.append(LlmSuggestedWord(
                    lemma=lemma,
                    pos=pos,
                    translations=translations
                ))
    
    if not evaluations:
        raise ValueError("No valid evaluations could be extracted from LLM response")
    
    return LlmEvaluateResponse(
        evaluations=evaluations,
        new_suggested_words=suggested_words
    )
