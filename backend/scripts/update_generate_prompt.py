"""
Script to update the generate_sentences prompt in the database.

This script updates the prompt to match the expected JSON schema format.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.models import Prompt


NEW_PROMPT = """You are an English language teacher. Generate English sentences for a student at {level} level.

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
- Return ONLY valid JSON, no markdown, no explanations"""


async def update_prompt():
    """Update the generate_sentences prompt in the database."""
    print("Connecting to database...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Check if prompt exists
            result = await conn.execute(
                select(Prompt).where(Prompt.key == "generate_sentences")
            )
            existing_prompt = result.scalar_one_or_none()
            
            if existing_prompt:
                print(f"✅ Found existing prompt 'generate_sentences'")
                print(f"   Current length: {len(existing_prompt.system_template)} chars")
                
                # Update the prompt
                await conn.execute(
                    update(Prompt)
                    .where(Prompt.key == "generate_sentences")
                    .values(system_template=NEW_PROMPT)
                )
                
                print(f"✅ Updated prompt 'generate_sentences'")
                print(f"   New length: {len(NEW_PROMPT)} chars")
            else:
                print(f"❌ Prompt 'generate_sentences' not found in database")
                print(f"   Please run migrations first: alembic upgrade head")
                return False
        
        print("\n✅ Prompt updated successfully!")
        print("\nNext steps:")
        print("1. Restart the backend server")
        print("2. Try starting a lesson again")
        return True
        
    except Exception as e:
        print(f"\n❌ Error updating prompt: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("="*60)
    print("Update generate_sentences prompt")
    print("="*60)
    print()
    
    success = asyncio.run(update_prompt())
    
    if not success:
        sys.exit(1)
