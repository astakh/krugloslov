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
    "generate_sentences": """You are an English language teacher. Generate {count} English sentences for a student at {level} level.

Requirements:
- Each sentence must contain the target word: {word}
- Sentences should be natural and contextually appropriate
- Use vocabulary appropriate for {level} level
- Each sentence should be 5-15 words long
- Provide a Russian translation for each sentence

Return JSON format:
{{
  "sentences": [
    {{
      "english": "English sentence with target word",
      "russian": "Russian translation"
    }}
  ]
}}""",
    
    "evaluate_translation": """You are an English language teacher evaluating a student's translation.

Compare the user's translation with the reference translation and determine if the target words were translated correctly.

Rules:
- Focus on the target words, not the entire sentence
- Accept synonyms and grammatically correct variations
- Mark as "correct" if meaning is preserved
- Mark as "incorrect" if meaning is lost or wrong
- Mark as "partial" if some target words are correct

Return JSON format:
{{
  "results": [
    {{
      "word": "target word",
      "status": "correct|incorrect|partial",
      "feedback": "brief explanation"
    }}
  ],
  "overall": "correct|incorrect|partial"
}}"""
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
