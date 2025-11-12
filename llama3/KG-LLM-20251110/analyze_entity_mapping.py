"""Script to analyze why gold_entity_ids are empty and improve matching."""

from webqsp_loader import WebQSPLoader
from knowledge_graph import KnowledgeGraph
import json


def analyze_entity_mapping_issues():
    """Analyze why entity ID mapping might be failing."""
    print("\n" + "="*70)
    print("Analyzing Entity ID Mapping Issues")
    print("="*70)
    
    loader = WebQSPLoader()
    
    # Load first 10 samples
    print("\nLoading 10 samples from test set...")
    samples = loader.load_samples("data/webqsp/test_simple.json", num_samples=10)
    
    issues_found = 0
    matches_found = 0
    
    for i, sample in enumerate(samples, 1):
        print(f"\n{'='*70}")
        print(f"Sample {i}: {sample.get('id', 'unknown')}")
        print(f"{'='*70}")
        
        question = sample.get('question', '')
        answers = [ans.get('text') if ans else None for ans in sample.get('answers', [])]
        
        # Filter None values
        answers = [a for a in answers if a is not None]
        
        print(f"Question: {question}")
        print(f"Gold Answers: {answers}")
        
        if not answers:
            print("  ⚠ No valid answers in sample")
            issues_found += 1
            continue
        
        # Build KG
        kg = loader.sample_to_kg(sample, limit_size=200)
        print(f"KG Size: {len(kg.entities)} entities, {len(kg.relations)} relations")
        
        # Show sample entities
        print(f"\nSample entities (first 10):")
        for j, (entity_id, entity) in enumerate(list(kg.entities.items())[:10]):
            print(f"  {j+1}. {entity_id}: {entity.name}")
        
        # Try to map each answer
        print(f"\nMapping gold answers to entity IDs:")
        for answer_text in answers:
            entity_ids = loader.find_entity_ids_for_answer(answer_text, kg)
            
            if entity_ids:
                print(f"  ✓ '{answer_text}' → {len(entity_ids)} match(es)")
                for entity_id in entity_ids[:3]:
                    entity = kg.entities.get(entity_id)
                    if entity:
                        print(f"      - {entity_id}: {entity.name}")
                matches_found += 1
            else:
                print(f"  ✗ '{answer_text}' → No matches found")
                print(f"      Possible reasons:")
                print(f"      - Answer entity not in subgraph")
                print(f"      - Entity name format mismatch")
                print(f"      - Subgraph too small (only {len(kg.entities)} entities)")
                issues_found += 1
    
    print(f"\n{'='*70}")
    print("Analysis Summary")
    print(f"{'='*70}")
    print(f"Total samples analyzed: {len(samples)}")
    print(f"Matches found: {matches_found}")
    print(f"Issues found: {issues_found}")
    print(f"\nCommon issues:")
    print("  1. Answer entities not in limited subgraph (max 150-200 triples)")
    print("  2. Entity name format differences (m.0xyz vs full name)")
    print("  3. None values in gold answers")
    print(f"{'='*70}")


def test_improved_matching():
    """Test improved entity matching strategies."""
    print("\n" + "="*70)
    print("Testing Improved Matching Strategies")
    print("="*70)
    
    loader = WebQSPLoader()
    sample = loader.load_sample("data/webqsp/test_simple.json", 0)
    
    print(f"\nSample ID: {sample.get('id')}")
    print(f"Question: {sample.get('question')}")
    
    answers = [ans.get('text') if ans else None for ans in sample.get('answers', [])]
    answers = [a for a in answers if a is not None]
    print(f"Gold Answers: {answers}")
    
    # Try with different subgraph sizes
    sizes = [100, 200, 300, 500]
    
    print(f"\nTesting different subgraph sizes:")
    for size in sizes:
        kg = loader.sample_to_kg(sample, limit_size=size)
        print(f"\n  Size {size}:")
        print(f"    Entities: {len(kg.entities)}, Relations: {len(kg.relations)}")
        
        for answer_text in answers:
            entity_ids = loader.find_entity_ids_for_answer(answer_text, kg)
            if entity_ids:
                print(f"    ✓ '{answer_text}' → {len(entity_ids)} match(es)")
            else:
                print(f"    ✗ '{answer_text}' → No matches")


if __name__ == "__main__":
    import sys
    
    try:
        analyze_entity_mapping_issues()
        print("\n")
        test_improved_matching()
        
    except Exception as e:
        print(f"\n✗ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
