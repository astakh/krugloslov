#!/usr/bin/env python3
"""Test script for JSON fixing function."""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.llm.client import GigaChatClient


def test_json_fixing():
    """Test various JSON fixing scenarios."""
    client = GigaChatClient()
    
    test_cases = [
        # Test 1: Missing quotes around keys
        {
            "name": "Missing quotes around keys",
            "input": '{evaluations: [{lemma: "house", pos: "noun"}]}',
            "expected_valid": True,
        },
        # Test 2: Trailing commas
        {
            "name": "Trailing commas",
            "input": '{"evaluations": [{"lemma": "house", "pos": "noun",},]}',
            "expected_valid": True,
        },
        # Test 3: Single quotes
        {
            "name": "Single quotes",
            "input": "{'evaluations': [{'lemma': 'house', 'pos': 'noun'}]}",
            "expected_valid": True,
        },
        # Test 4: Missing colons
        {
            "name": "Missing colons",
            "input": '{"evaluations": [{"lemma" "house", "pos" "noun"}]}',
            "expected_valid": True,
        },
        # Test 5: Valid JSON (should not be changed)
        {
            "name": "Valid JSON",
            "input": '{"evaluations": [{"lemma": "house", "pos": "noun"}]}',
            "expected_valid": True,
        },
        # Test 6: Complex case with multiple issues
        {
            "name": "Multiple issues",
            "input": "{evaluations: [{'lemma': 'house', 'pos': 'noun',},]}",
            "expected_valid": True,
        },
    ]
    
    print("=" * 80)
    print("JSON Fixing Test Suite")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print(f"Input: {test_case['input']}")
        
        # Try to parse original
        try:
            json.loads(test_case['input'])
            print("✓ Original JSON is valid")
            passed += 1
            continue
        except json.JSONDecodeError as e:
            print(f"✗ Original JSON is invalid: {e}")
        
        # Try to fix
        fixed = client._fix_common_json_issues(test_case['input'])
        print(f"Fixed: {fixed}")
        
        # Try to parse fixed
        try:
            json.loads(fixed)
            print("✓ Fixed JSON is valid")
            if test_case['expected_valid']:
                passed += 1
            else:
                failed += 1
                print(f"✗ Expected invalid but got valid")
        except json.JSONDecodeError as e:
            print(f"✗ Fixed JSON is still invalid: {e}")
            if not test_case['expected_valid']:
                passed += 1
            else:
                failed += 1
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = test_json_fixing()
    sys.exit(0 if success else 1)
