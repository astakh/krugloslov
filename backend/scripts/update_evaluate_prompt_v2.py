#!/usr/bin/env python3
"""
Script to update the evaluate_translation prompt in the database.
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


NEW_PROMPT = """You are an English language teacher evaluating a student's translation.

Compare the user's translation with the reference translation and determine if the target words were translated correctly.

Rules:
- Focus on the target words, not the entire sentence
- Accept synonyms and grammatically correct variations
- Mark as "correct" if the translation is accurate
- Mark as "typo" if there's a minor spelling mistake but meaning is clear
- Mark as "incorrect" if the translation is wrong or missing
- For each word, provide the lemma (base form) and part of speech (noun/verb/adj/adv)

Return JSON format:
{{
  "evaluations": [
    {{
      "lemma": "base form of the word",
      "pos": "noun|verb|adj|adv",
      "result": "correct|typo|incorrect",
      "feedback": "brief explanation",
      "user_fragment": "the exact phrase the user used for this word"
    }}
  ]
}}

IMPORTANT:
- Use "evaluations" as the root key
- Each evaluation must have: lemma, pos, result
- pos must be one of: noun, verb, adj, adv
- result must be one of: correct, typo, incorrect (NOT partial)
- user_fragment is optional but helpful
- Return ONLY valid JSON, no markdown, no explanations"""


async def update_prompt():
    """Update the evaluate_translation prompt in the database."""
    print("Connecting to database...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        from sqlalchemy.ext.asyncio import async_sessionmaker
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Check if prompt exists
            result = await session.execute(
                select(Prompt).where(Prompt.key == "evaluate_translation")
            )
            existing_prompt = result.scalar_one_or_none()
            
            if existing_prompt:
                print(f"✅ Found existing prompt 'evaluate_translation'")
                print(f"   Current length: {len(existing_prompt.system_template)} chars")
                
                # Update the prompt
                existing_prompt.system_template = NEW_PROMPT
                await session.commit()
                
                print(f"✅ Updated prompt 'evaluate_translation'")
                print(f"   New length: {len(NEW_PROMPT)} chars")
            else:
                print(f"❌ Prompt 'evaluate_translation' not found in database")
                print(f"   Please run migrations first: alembic upgrade head")
                return False
        
        print("\n✅ Prompt updated successfully!")
        print("\nNext steps:")
        print("1. Restart the backend server")
        print("2. Try evaluating a translation again")
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
    print("Update evaluate_translation prompt")
    print("="*60)
    print()
    
    success = asyncio.run(update_prompt())
    
    if not success:
        sys.exit(1)
