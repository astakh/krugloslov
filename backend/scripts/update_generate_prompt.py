"""Script to update generate_sentences prompt in database."""

import asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Prompt


NEW_PROMPT = """You are an English language teacher. Generate English sentences for a student at {level} level.

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
- Return ONLY valid JSON, no markdown, no explanations"""


async def update_prompt():
    """Update generate_sentences prompt in database."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Check if prompt exists
        result = await conn.execute(
            select(Prompt).where(Prompt.key == "generate_sentences")
        )
        prompt = result.scalar_one_or_none()
        
        if prompt:
            # Update existing prompt
            await conn.execute(
                update(Prompt)
                .where(Prompt.key == "generate_sentences")
                .values(system_template=NEW_PROMPT)
            )
            print("✅ Updated existing prompt 'generate_sentences'")
        else:
            # Create new prompt
            from app.models import Prompt as PromptModel
            new_prompt = PromptModel(
                key="generate_sentences",
                system_template=NEW_PROMPT,
                updated_by=None
            )
            conn.add(new_prompt)
            print("✅ Created new prompt 'generate_sentences'")
    
    await engine.dispose()
    print("✅ Prompt update completed")


if __name__ == "__main__":
    asyncio.run(update_prompt())
