"""
Script to seed the general dictionary from fixtures.

Usage:
    cd backend
    python scripts/seed_general_dictionary.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.dictionary import Dictionary
from app.models.word import Word
from app.models.dictionary_word import DictionaryWord
from app.repositories.word_repo import normalize_lemma


async def seed_general_dictionary():
    """Seed the general dictionary with words from fixtures."""
    
    # Load fixture file
    fixture_path = Path(__file__).parent.parent / "fixtures" / "general_dictionary.json"
    
    if not fixture_path.exists():
        print(f"❌ Fixture file not found: {fixture_path}")
        return False
    
    print(f"📖 Loading fixture from {fixture_path}...")
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    dictionary_data = data["dictionary"]
    words_data = data["words"]
    
    print(f"✅ Loaded {len(words_data)} words for dictionary '{dictionary_data['code']}'")
    
    # Create async engine and session factory
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Check if general dictionary already exists
            result = await session.execute(
                select(Dictionary).where(Dictionary.is_general == True)
            )
            existing_dict = result.scalar_one_or_none()
            
            if existing_dict:
                print(f"⚠️  General dictionary already exists (id={existing_dict.id}, code={existing_dict.code})")
                print(f"   Skipping creation. Use admin panel to manage dictionaries.")
                return False
            
            # Create general dictionary
            print(f"📚 Creating general dictionary '{dictionary_data['code']}'...")
            
            dictionary = Dictionary(
                code=dictionary_data["code"],
                name=dictionary_data["name"],
                description=dictionary_data.get("description", ""),
                is_general=True,
            )
            session.add(dictionary)
            await session.flush()
            
            print(f"✅ Dictionary created (id={dictionary.id})")
            
            # Process words
            added_count = 0
            linked_count = 0
            skipped_count = 0
            
            print(f"📝 Processing {len(words_data)} words...")
            
            for idx, word_data in enumerate(words_data, 1):
                lemma = word_data["lemma"].strip()
                lemma_key = normalize_lemma(lemma)
                pos = word_data["pos"]
                level = word_data.get("level")
                translations = word_data.get("translations", [])
                
                # Check if word already exists
                result = await session.execute(
                    select(Word).where(
                        Word.lemma_key == lemma_key,
                        Word.pos == pos
                    )
                )
                existing_word = result.scalar_one_or_none()
                
                if existing_word:
                    word = existing_word
                    if idx % 10 == 0:
                        print(f"   ⏭️  Word '{lemma}' already exists (id={word.id})")
                else:
                    # Create new word
                    word = Word(
                        lemma=lemma,
                        lemma_key=lemma_key,
                        pos=pos,
                        level=level,
                        translations=translations,
                    )
                    session.add(word)
                    await session.flush()
                    added_count += 1
                    
                    if idx % 10 == 0:
                        print(f"   ✅ Added word '{lemma}' (id={word.id})")
                
                # Check if link already exists
                result = await session.execute(
                    select(DictionaryWord).where(
                        DictionaryWord.dictionary_id == dictionary.id,
                        DictionaryWord.word_id == word.id
                    )
                )
                existing_link = result.scalar_one_or_none()
                
                if existing_link:
                    skipped_count += 1
                else:
                    # Link word to dictionary
                    dict_word = DictionaryWord(
                        dictionary_id=dictionary.id,
                        word_id=word.id,
                    )
                    session.add(dict_word)
                    linked_count += 1
            
            await session.commit()
            
            print("\n" + "="*60)
            print("✅ General dictionary seeded successfully!")
            print("="*60)
            print(f"📊 Statistics:")
            print(f"   - Words added: {added_count}")
            print(f"   - Words linked: {linked_count}")
            print(f"   - Words skipped (already linked): {skipped_count}")
            print(f"   - Total words in dictionary: {added_count + skipped_count}")
            print("="*60)
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error seeding dictionary: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def check_database_connection():
    """Check if database connection is working."""
    print("🔌 Checking database connection...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()  # scalar() is NOT async in SQLAlchemy 2.0
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Please check your DATABASE_URL in .env file")
        print(f"   Current value: {settings.DATABASE_URL[:50]}...")
        return False
    finally:
        await engine.dispose()


async def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("🌱 Krugoslov - Seed General Dictionary")
    print("="*60 + "\n")
    
    # Check database connection
    if not await check_database_connection():
        sys.exit(1)
    
    print()
    
    # Seed dictionary
    success = await seed_general_dictionary()
    
    if success:
        print("\n🎉 You can now complete onboarding in the web interface!")
        print("   Open http://localhost:3000 and login\n")
    else:
        print("\n⚠️  Seeding was not completed. See errors above.\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
