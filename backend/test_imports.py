"""Test script to verify all models can be imported."""

import sys

def test_imports():
    """Test that all models can be imported without errors."""
    try:
        from app.models import (
            Base,
            User,
            RefreshToken,
            Dictionary,
            Word,
            DictionaryWord,
            LearningProfile,
            UserWord,
            Lesson,
            LessonExercise,
            LessonExerciseWord,
            LessonExerciseSuggestion,
            SentenceReport,
            LLMCall,
            Event,
            DictionaryImport,
            Prompt,
            PromptHistory,
        )
        print("✅ All models imported successfully!")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
