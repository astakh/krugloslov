#!/usr/bin/env python3
"""
Script to verify all models can be imported correctly.
This helps catch import errors before running migrations.
"""

import sys
import traceback

def check_model_imports():
    """Check if all models can be imported."""
    print("Checking model imports...")
    
    models_to_check = [
        'app.models.base',
        'app.models.user',
        'app.models.refresh_token',
        'app.models.dictionary',
        'app.models.word',
        'app.models.dictionary_word',
        'app.models.learning_profile',
        'app.models.user_word',
        'app.models.lesson',
        'app.models.lesson_exercise',
        'app.models.lesson_exercise_word',
        'app.models.lesson_exercise_suggestion',
        'app.models.sentence_report',
        'app.models.llm_call',
        'app.models.event',
        'app.models.dictionary_import',
        'app.models.prompt',
        'app.models.prompt_history',
    ]
    
    failed = []
    
    for model_path in models_to_check:
        try:
            __import__(model_path)
            print(f"✓ {model_path}")
        except Exception as e:
            print(f"✗ {model_path}: {e}")
            failed.append((model_path, e))
            traceback.print_exc()
    
    if failed:
        print(f"\n❌ Failed to import {len(failed)} model(s)")
        return False
    else:
        print(f"\n✅ All {len(models_to_check)} models imported successfully!")
        return True

def check_main_import():
    """Check if app.models can be imported."""
    print("\nChecking app.models import...")
    try:
        from app import models
        print("✓ app.models imported successfully")
        print(f"  Available models: {', '.join(models.__all__)}")
        return True
    except Exception as e:
        print(f"✗ Failed to import app.models: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = True
    
    if not check_model_imports():
        success = False
    
    if not check_main_import():
        success = False
    
    sys.exit(0 if success else 1)
