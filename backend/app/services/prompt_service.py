"""Prompt service for managing LLM prompts from database."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import Prompt

logger = logging.getLogger(__name__)

# Fallback prompts if not found in database
FALLBACK_PROMPTS = {
    "generate_sentences": """You are an English language teacher. Generate English sentences for a student at {level} level.

For each word group provided, create ONE natural English sentence that:
- Contains all the target words from that group
- Uses vocabulary appropriate for {level} level
- Is 5-15 words long
- Is contextually appropriate and natural

For each sentence, also provide:
- The exact surface form of each target word as used in the sentence
- A Russian translation of the complete sentence

Return JSON format EXACTLY as shown:
{{
  "groups": [
    {{
      "group_index": 0,
      "sentence": "English sentence with target words",
      "reference_translation": "Russian translation of the sentence",
      "words": [
        {{
          "lemma": "target_word_lemma",
          "pos": "noun|verb|adj|adv",
          "surface_form": "exact form used in sentence"
        }}
      ]
    }}
  ]
}}

IMPORTANT: 
- Use "groups" as the root key, NOT "sentences"
- Each group must have: group_index, sentence, reference_translation, words
- words array must contain all target words for that group with their surface forms
- Return ONLY valid JSON, no markdown, no explanations""",
    
    "evaluate_translation": """You are an English language teacher evaluating a student's translation.

Your task: Evaluate ONLY the target words listed in "Target words to evaluate" section.

For each target word:
1. Find how the user translated it in their translation
2. Compare with the reference translation
3. Determine if the translation is correct

Evaluation rules:
- "correct": The word is translated accurately (synonyms and grammatical variations are acceptable)
- "typo": Minor spelling mistake but meaning is clear
- "incorrect": Wrong translation or missing word

IMPORTANT:
- Evaluate ONLY the words from the "Target words to evaluate" list
- Use the EXACT lemma and pos from the list (do not change them)
- Provide one evaluation per target word (no duplicates, no extra words)
- user_fragment: the exact phrase from user's translation for this word (or null if not found)
- feedback: brief explanation of why it's correct/incorrect

Return JSON format:
{{
  "evaluations": [
    {{
      "lemma": "exact lemma from target words list",
      "pos": "exact pos from target words list",
      "result": "correct|typo|incorrect",
      "user_fragment": "phrase from user translation or null",
      "feedback": "brief explanation"
    }}
  ]
}}

CRITICAL:
- Number of evaluations MUST equal number of target words
- Each evaluation must match a target word's lemma and pos exactly
- Do NOT suggest new words
- Do NOT evaluate words not in the target list
- Return ONLY valid JSON"""
}


class PromptService:
    """Service for retrieving and managing LLM prompts."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_prompt(self, key: str) -> str:
        """
        Get prompt text by key.
        
        Args:
            key: Prompt key (e.g., 'generate_sentences')
        
        Returns:
            Prompt template text
        
        Note:
            Logs critical error if prompt not found in database and uses fallback.
        """
        result = await self.session.execute(
            select(Prompt).where(Prompt.key == key)
        )
        prompt = result.scalar_one_or_none()
        
        if prompt is None:
            logger.critical(
                f"prompt_missing: Prompt '{key}' not found in database, using fallback"
            )
            if key not in FALLBACK_PROMPTS:
                raise ValueError(f"No fallback prompt available for key: {key}")
            return FALLBACK_PROMPTS[key]
        
        return prompt.system_template
    
    def format_prompt(self, template: str, **kwargs) -> str:
        """
        Format prompt template with variables.
        
        Args:
            template: Prompt template with {placeholders}
            **kwargs: Variables to substitute
        
        Returns:
            Formatted prompt text
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing placeholder in prompt: {e}")
            raise ValueError(f"Missing required placeholder: {e}")
