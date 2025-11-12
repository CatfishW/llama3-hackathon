"""Test suite for EPERM system."""

from __future__ import annotations
import json
from eperm_system import EPERMSystem


def test_basic_questions():
    """Test EPERM with basic questions."""
    print("\n" + "="*70)
    print("EPERM System Test Suite")
    print("="*70)
    
    # Initialize system
    system = EPERMSystem()
    
    # Load sample knowledge graph
    system.load_knowledge_graph("data/sample_kg.json")
    
    # Test questions
    test_questions = [
        "Who founded Microsoft?",
        "Where is Microsoft headquartered?",
        "What did Microsoft develop?",
        "Who is the founder of Apple?",
        "What products did Apple create?",
        "Which university did Bill Gates attend?",
    ]
    
    results = []
    
    for question in test_questions:
        try:
            answer = system.answer_question(question)
            
            result = {
                "question": question,
                "answer": answer.answer,
                "confidence": answer.confidence,
                "num_evidence_paths": len(answer.supporting_paths)
            }
            results.append(result)
            
            print(f"\n{'='*70}")
            print(f"✓ SUCCESS")
            print(f"  Answer: {answer.answer}")
            print(f"  Confidence: {answer.confidence:.2f}")
            print(f"  Evidence paths: {len(answer.supporting_paths)}")
            
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"✗ FAILED: {e}")
            results.append({
                "question": question,
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*70}")
    print("Test Summary")
    print(f"{'='*70}")
    print(f"Total questions: {len(test_questions)}")
    print(f"Successful: {sum(1 for r in results if 'answer' in r)}")
    print(f"Failed: {sum(1 for r in results if 'error' in r)}")
    
    return results


def test_custom_kg():
    """Test with a custom knowledge graph."""
    print("\n" + "="*70)
    print("Testing with Custom Knowledge Graph")
    print("="*70)
    
    # Create custom KG about AI
    custom_kg = {
        "entities": [
            {"id": "e1", "name": "GPT-4", "type": "AI Model"},
            {"id": "e2", "name": "OpenAI", "type": "Company"},
            {"id": "e3", "name": "Sam Altman", "type": "Person"},
            {"id": "e4", "name": "ChatGPT", "type": "Product"},
            {"id": "e5", "name": "Large Language Model", "type": "Technology"},
        ],
        "relations": [
            {"head": "e2", "relation": "developed", "tail": "e1"},
            {"head": "e3", "relation": "is_CEO_of", "tail": "e2"},
            {"head": "e2", "relation": "created", "tail": "e4"},
            {"head": "e4", "relation": "uses", "tail": "e1"},
            {"head": "e1", "relation": "is_a", "tail": "e5"},
        ]
    }
    
    system = EPERMSystem()
    system.load_knowledge_graph_from_dict(custom_kg)
    
    questions = [
        "Who is the CEO of OpenAI?",
        "What did OpenAI develop?",
        "What technology does ChatGPT use?",
    ]
    
    for question in questions:
        answer = system.answer_question(question)
        print(f"\n  Q: {question}")
        print(f"  A: {answer.answer} (confidence: {answer.confidence:.2f})")


def test_detailed_output():
    """Test detailed output format."""
    print("\n" + "="*70)
    print("Testing Detailed Output")
    print("="*70)
    
    system = EPERMSystem()
    system.load_knowledge_graph("data/sample_kg.json")
    
    question = "Who founded Microsoft?"
    result = system.answer_question_detailed(question)
    
    print(f"\nDetailed Result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import sys
    
    try:
        # Run all tests
        test_basic_questions()
        test_custom_kg()
        test_detailed_output()
        
        print("\n" + "="*70)
        print("✓ All tests completed!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
