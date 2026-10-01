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
    
    "evaluate_translation": """Ты — преподаватель английского языка. Твоя задача — оценить перевод ученика.

Оцени ТОЛЬКО те слова, которые перечислены в разделе «Целевые слова для оценки».

Для каждого целевого слова:
1. Найди, как ученик перевёл его в своём переводе
2. Сравни с эталонным переводом
3. Определи, правильный ли перевод

Правила оценки:
- "correct" — слово переведено точно (допускаются синонимы и грамматические варианты)
- "typo" — небольшая орфографическая ошибка, но смысл понятен
- "incorrect" — неправильный перевод или слово пропущено

ВАЖНО:
- Оценивай ТОЛЬКО слова из списка «Целевые слова для оценки»
- Используй ТОЧНЫЕ lemma и pos из списка (не изменяй их)
- Для каждого слова — одна оценка (без дубликатов и лишних слов)
- user_fragment — точная фраза из перевода ученика для этого слова (или null, если не найдена)
- feedback — краткое объяснение, почему перевод верный/неверный

Верни результат в формате JSON:
{{
  "evaluations": [
    {{
      "lemma": "точная lemma из списка целевых слов",
      "pos": "точная pos из списка целевых слов",
      "result": "correct|typo|incorrect",
      "user_fragment": "фраза из перевода ученика или null",
      "feedback": "краткое объяснение"
    }}
  ]
}}

КРИТИЧЕСКИ ВАЖНО:
- Количество оценок ДОЛЖНО равняться количеству целевых слов
- Каждая оценка должна точно соответствовать lemma и pos целевого слова
- НЕ предлагай новые слова
- НЕ оценивай слова, которых нет в списке целевых
- Верни ТОЛЬКО валидный JSON, без markdown и пояснений"""
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
