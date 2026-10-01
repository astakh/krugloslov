"""Test script for LLM response adapter."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.llm_response_adapter import adapt_llm_response


def test_simple_sentences_format():
    """Test adaptation of simple sentences format."""
    print("Test 1: Simple sentences format")
    
    raw_response = {
        "sentences": [
            {"english": "The cat runs fast.", "russian": "Кот бегает быстро."},
            {"english": "The dog sleeps well.", "russian": "Собака хорошо спит."}
        ]
    }
    
    expected_groups = [
        [{"lemma": "run", "pos": "verb"}, {"lemma": "fast", "pos": "adverb"}],
        [{"lemma": "sleep", "pos": "verb"}, {"lemma": "well", "pos": "adverb"}]
    ]
    
    try:
        result = adapt_llm_response(raw_response, expected_groups)
        print(f"✅ Success! Adapted {len(result.groups)} groups")
        for group in result.groups:
            print(f"   Group {group.group_index}: {group.sentence}")
            print(f"   Translation: {group.reference_translation}")
            print(f"   Words: {len(group.words)}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_simple_groups_format():
    """Test adaptation of simple groups format."""
    print("\nTest 2: Simple groups format")
    
    raw_response = {
        "groups": [
            {"english": "The cat runs fast.", "russian": "Кот бегает быстро."},
            {"english": "The dog sleeps well.", "russian": "Собака хорошо спит."}
        ]
    }
    
    expected_groups = [
        [{"lemma": "run", "pos": "verb"}, {"lemma": "fast", "pos": "adverb"}],
        [{"lemma": "sleep", "pos": "verb"}, {"lemma": "well", "pos": "adverb"}]
    ]
    
    try:
        result = adapt_llm_response(raw_response, expected_groups)
        print(f"✅ Success! Adapted {len(result.groups)} groups")
        for group in result.groups:
            print(f"   Group {group.group_index}: {group.sentence}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_full_format():
    """Test that full format passes through unchanged."""
    print("\nTest 3: Full format (should pass through)")
    
    raw_response = {
        "groups": [
            {
                "group_index": 0,
                "sentence": "The cat runs fast.",
                "reference_translation": "Кот бегает быстро.",
                "words": [
                    {"lemma": "run", "pos": "verb", "surface_form": "runs"},
                    {"lemma": "fast", "pos": "adverb", "surface_form": "fast"}
                ]
            }
        ]
    }
    
    expected_groups = [
        [{"lemma": "run", "pos": "verb"}, {"lemma": "fast", "pos": "adverb"}]
    ]
    
    try:
        result = adapt_llm_response(raw_response, expected_groups)
        print(f"✅ Success! Validated {len(result.groups)} groups")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_direct_array():
    """Test adaptation of direct array format."""
    print("\nTest 4: Direct array format")
    
    raw_response = [
        {"english": "The cat runs fast.", "russian": "Кот бегает быстро."},
        {"english": "The dog sleeps well.", "russian": "Собака хорошо спит."}
    ]
    
    expected_groups = [
        [{"lemma": "run", "pos": "verb"}, {"lemma": "fast", "pos": "adverb"}],
        [{"lemma": "sleep", "pos": "verb"}, {"lemma": "well", "pos": "adverb"}]
    ]
    
    try:
        result = adapt_llm_response(raw_response, expected_groups)
        print(f"✅ Success! Adapted {len(result.groups)} groups")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("LLM Response Adapter Tests")
    print("="*60)
    
    results = []
    results.append(test_simple_sentences_format())
    results.append(test_simple_groups_format())
    results.append(test_full_format())
    results.append(test_direct_array())
    
    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*60)
    
    if all(results):
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
