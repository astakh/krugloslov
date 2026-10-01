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

CRITICAL REQUIREMENT: For each word group, you MUST create ONE sentence that contains ALL the target words from that group. Every single word in the group must appear in the sentence.

For each word group provided, create ONE natural English sentence that:
- Contains ALL the target words from that group (this is mandatory - do not skip any words)
- Uses vocabulary appropriate for {level} level
- Is 5-15 words long
- Is contextually appropriate and natural

For each sentence, also provide:
- The exact surface form of each target word as used in the sentence (the actual word form, not the lemma)
- A Russian translation of the complete sentence

Return JSON format EXACTLY as shown:
{{
  "groups": [
    {{
      "group_index": 0,
      "sentence": "English sentence with ALL target words",
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

CRITICAL RULES:
- Use "groups" as the root key, NOT "sentences"
- Each group must have: group_index, sentence, reference_translation, words
- The sentence MUST contain ALL words from the group - no exceptions
- words array must contain ALL target words for that group with their surface forms
- The number of words in the words array must match the number of target words provided
- Return ONLY valid JSON, no markdown, no explanations""",
    
    "evaluate_translation": """Ты — преподаватель английского языка для русскоговорящих. Тебе будет предоставлено исходное предложение на английском языке, перевод этого предложения учеником на русский язык и список целевых слов. Твоя задача — оценить перевод ученика, а именно: правильность перевода целевых слов, а так же правильность перевода других слов в предложении.

Для каждого целевого слова:
1. Найди, как ученик перевёл его в своём переводе
2. Определи, правильный ли перевод

Правила оценки:
- "correct" — слово переведено точно (допускаются синонимы и грамматические варианты)
- "typo" — небольшая орфографическая ошибка, но смысл понятен
- "incorrect" — неправильный перевод или слово пропущено

ВАЖНО:
- Обязательно оцени слова из списка «Целевые слова для оценки»
- Используй ТОЧНЫЕ lemma и pos из списка (не изменяй их) - но не будь строг при оценке правильности перевода (допускай синонимы и грамматические формы)
- Для каждого слова — одна оценка (без дубликатов и лишних слов)
- user_fragment — точное слово (или фраза) из перевода ученика для этого слова (или null, если не найдена)

Верни результат в формате JSON:
{{
  "evaluations": [
    {{
      "lemma": "точная lemma из списка целевых слов",
      "pos": "точная pos из списка целевых слов",
      "result": "correct|typo|incorrect",
      "user_fragment": "фраза из перевода ученика или null"
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
