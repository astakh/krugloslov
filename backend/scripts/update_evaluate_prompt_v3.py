"""Script to update evaluate_translation prompt in database."""

import asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import settings
from app.models.prompt import Prompt


NEW_PROMPT = """You are an English language teacher evaluating a student's translation.

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
