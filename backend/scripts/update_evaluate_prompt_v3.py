"""Script to update evaluate_translation prompt in database."""

import asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import settings
from app.models.prompt import Prompt


NEW_PROMPT = """Ты — преподаватель английского языка для русскоговорящих. Тебе будет предоставлено исходное предложение на английском языке, перевод этого предложения учеником на русский язык и список целевых слов. Твоя задача — оценить перевод ученика, а именно: правильность перевода целевых слов, а так же правильность перевода других слов в предложении.

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


async def update_prompt():
    """Update evaluate_translation prompt in database."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Check if prompt exists
        result = await conn.execute(
            select(Prompt).where(Prompt.key == "evaluate_translation")
        )
        prompt = result.scalar_one_or_none()
        
        if prompt:
            # Update existing prompt
            await conn.execute(
                update(Prompt)
                .where(Prompt.key == "evaluate_translation")
                .values(system_template=NEW_PROMPT)
            )
            print("✅ Updated existing evaluate_translation prompt")
        else:
            # Create new prompt
            new_prompt = Prompt(
                key="evaluate_translation",
                system_template=NEW_PROMPT
            )
            conn.add(new_prompt)
            print("✅ Created new evaluate_translation prompt")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_prompt())
