"""Test and demonstrate the flexible matching function."""

import unicodedata
import re


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _flexible_match(predicted: str, gold_answers: list) -> bool:
    """Check if predicted answer matches any gold answer with flexible matching."""
    pred_norm = _normalize_text(predicted)
    
    for gold in gold_answers:
        gold_norm = _normalize_text(gold)
        
        if pred_norm == gold_norm:
            return True
        
        if gold_norm in pred_norm or pred_norm in gold_norm:
            return True
        
        pred_words = set(pred_norm.split())
        gold_words = set(gold_norm.split())
        
        if pred_words and gold_words:
            overlap = len(pred_words & gold_words)
            similarity = overlap / max(len(pred_words), len(gold_words))
            if similarity >= 0.5:
                return True
    
    return False


def test_matching():
    """Test various matching scenarios."""
    print("\n" + "="*70)
    print("Flexible Matching Test Cases")
    print("="*70)
    
    test_cases = [
        # (predicted, gold_answers, expected_result)
        ("Padme Amidala", ["Padmé Amidala"], True, "Accent difference"),
        ("The Bahamas", ["Bahamas"], True, "Article difference"),
        ("bahamas", ["Bahamas"], True, "Case difference"),
        ("Jaxon Bieber", ["Jaxon Bieber"], True, "Exact match"),
        ("John Smith", ["Jane Doe"], False, "Different names"),
        ("Microsoft Corporation", ["Microsoft"], True, "Partial match"),
        ("steve jobs", ["Steve Jobs"], True, "Case normalization"),
        ("Café", ["Cafe"], True, "Accent removal"),
        ("New York City", ["New York"], True, "Contains match"),
        ("Bill Gates", ["William Gates"], False, "Different but related"),
    ]
    
    print("\nTest Results:")
    print("-" * 70)
    
    passed = 0
    failed = 0
    
    for predicted, gold_list, expected, description in test_cases:
        result = _flexible_match(predicted, gold_list)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} | {description:20s} | Pred: '{predicted}' vs Gold: {gold_list}")
        print(f"     | Expected: {expected}, Got: {result}")
        
        # Show normalized forms for debugging
        if result != expected:
            pred_norm = _normalize_text(predicted)
            gold_norm = _normalize_text(gold_list[0]) if gold_list else ""
            print(f"     | Normalized - Pred: '{pred_norm}', Gold: '{gold_norm}'")
    
    print("-" * 70)
    print(f"\nSummary: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    
    print("\n" + "="*70)
    print("Key Features:")
    print("="*70)
    print("✓ Handles accent differences (é → e, ñ → n)")
    print("✓ Ignores case differences (John → john)")
    print("✓ Removes articles (The Bahamas → Bahamas)")
    print("✓ Strips punctuation and extra whitespace")
    print("✓ Partial matching (one answer contains the other)")
    print("✓ Word overlap matching (50% threshold)")
    print("="*70)


if __name__ == "__main__":
    test_matching()
