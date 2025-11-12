"""Quick test to verify entity ID mapping works correctly."""

from webqsp_loader import WebQSPLoader
from knowledge_graph import KnowledgeGraph
import json


def test_entity_id_mapping():
    """Test entity ID mapping functionality."""
    print("\n" + "="*70)
    print("Testing Entity ID Mapping")
    print("="*70)
    
    # Initialize loader
    loader = WebQSPLoader()
    
    # Load a few samples
    print("\nLoading 5 samples from training set...")
    samples = loader.load_samples("data/webqsp/train_simple.json", num_samples=5)
    
    print(f"\nProcessing {len(samples)} samples...\n")
    
    for i, sample in enumerate(samples, 1):
        print(f"{'='*70}")
        print(f"Sample {i}: {sample.get('id', 'unknown')}")
        print(f"{'='*70}")
        
        # Build KG
        kg = loader.sample_to_kg(sample, limit_size=200)
        
        # Get gold answers
        answers = [ans['text'] for ans in sample.get('answers', [])]
        question = sample.get('question', '')
        
        print(f"Question: {question}")
        print(f"Gold Answers: {answers}")
        print(f"KG Size: {len(kg.entities)} entities, {len(kg.relations)} relations")
        
        # Test entity ID mapping
        print(f"\nMapping gold answers to entity IDs:")
        
        for answer_text in answers:
            entity_ids = loader.find_entity_ids_for_answer(answer_text, kg)
            
            if entity_ids:
                print(f"  ✓ '{answer_text}' → {len(entity_ids)} entity ID(s)")
                for entity_id in entity_ids[:3]:  # Show first 3
                    entity = kg.entities.get(entity_id)
                    if entity:
                        print(f"      - {entity_id}: {entity.name}")
            else:
                print(f"  ✗ '{answer_text}' → No matching entities found")
        
        print()
    
    print("="*70)
    print("✓ Entity ID mapping test completed!")
    print("="*70)


def test_flexible_matching():
    """Test flexible matching with entity IDs."""
    print("\n" + "="*70)
    print("Testing Flexible Matching")
    print("="*70)
    
    from test_webqsp_eperm_optimized import _flexible_match
    
    # Test cases
    test_cases = [
        {
            'name': 'Direct entity ID match',
            'predicted': '0gyh',
            'gold_answers': ['Mobile'],
            'gold_entity_ids': ['0gyh'],
            'expected': True
        },
        {
            'name': 'Text match (no entity ID)',
            'predicted': 'Mobile',
            'gold_answers': ['Mobile'],
            'gold_entity_ids': [],
            'expected': True
        },
        {
            'name': 'Partial text match',
            'predicted': 'Mobile Alabama',
            'gold_answers': ['Mobile'],
            'gold_entity_ids': [],
            'expected': True
        },
        {
            'name': 'No match',
            'predicted': 'New York',
            'gold_answers': ['Mobile'],
            'gold_entity_ids': ['0gyh'],
            'expected': False
        }
    ]
    
    print("\nRunning test cases:\n")
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = _flexible_match(
            test['predicted'],
            test['gold_answers'],
            gold_entity_ids=test['gold_entity_ids']
        )
        
        status = "✓" if result == test['expected'] else "✗"
        if result == test['expected']:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {test['name']}")
        print(f"    Predicted: {test['predicted']}")
        print(f"    Gold: {test['gold_answers']} (IDs: {test['gold_entity_ids']})")
        print(f"    Result: {result}, Expected: {test['expected']}")
        print()
    
    print("="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70)


def test_qa_dataset_creation():
    """Test QA dataset creation with entity ID mapping."""
    print("\n" + "="*70)
    print("Testing QA Dataset Creation")
    print("="*70)
    
    loader = WebQSPLoader()
    
    print("\nCreating QA dataset with 3 samples...")
    qa_dataset = loader.create_qa_dataset(
        "data/webqsp/train_simple.json",
        num_samples=3,
        max_kg_size=200
    )
    
    print(f"\nCreated {len(qa_dataset)} QA items\n")
    
    for i, qa_item in enumerate(qa_dataset, 1):
        print(f"{'='*70}")
        print(f"QA Item {i}")
        print(f"{'='*70}")
        print(f"Question: {qa_item['question']}")
        print(f"Gold Answers: {qa_item['answers']}")
        print(f"Gold Entity IDs: {qa_item.get('answer_entity_ids', [])}")
        print(f"KG Stats: {qa_item['kg_stats']}")
        print()
    
    # Verify all QA items have answer_entity_ids field
    all_have_ids = all('answer_entity_ids' in qa for qa in qa_dataset)
    
    if all_have_ids:
        print("✓ All QA items have answer_entity_ids field")
    else:
        print("✗ Some QA items missing answer_entity_ids field")
    
    print("="*70)


if __name__ == "__main__":
    import sys
    
    try:
        print("\n" + "="*70)
        print("Entity ID Mapping - Verification Tests")
        print("="*70)
        
        # Test 1: Entity ID mapping
        test_entity_id_mapping()
        
        # Test 2: Flexible matching
        test_flexible_matching()
        
        # Test 3: QA dataset creation
        test_qa_dataset_creation()
        
        print("\n" + "="*70)
        print("✓ All verification tests completed!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
