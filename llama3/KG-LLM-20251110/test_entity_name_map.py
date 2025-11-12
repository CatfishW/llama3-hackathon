"""Test the entity name mapping functionality in KnowledgeGraph.

This script demonstrates how to use the comprehensive entity name mapping
to convert knowledge graphs to human-readable text.
"""

from webqsp_loader import WebQSPLoader
from knowledge_graph import KnowledgeGraph


def test_entity_name_mapping():
    """Test entity name mapping with sample data."""
    print("\n" + "="*70)
    print("Testing Entity Name Mapping in KnowledgeGraph")
    print("="*70)
    
    # Initialize WebQSP loader
    loader = WebQSPLoader()
    
    # Load a sample question
    print("\nLoading sample question from test set...")
    sample = loader.load_sample("data/webqsp/test_simple.json", 0)
    
    print(f"\nQuestion: {sample['question']}")
    print(f"Answers: {[ans['text'] for ans in sample['answers']]}")
    
    # Method 1: Using mapping from answers only (existing approach)
    print("\n" + "="*70)
    print("METHOD 1: Using entity names from answers only")
    print("="*70)
    
    entity_name_map_from_answers = {}
    for ans in sample.get('answers', []):
        if ans and ans.get('kb_id') and ans.get('text'):
            entity_name_map_from_answers[ans['kb_id']] = ans['text']
    
    kg1 = loader.sample_to_kg(sample, limit_size=50, entity_name_map=entity_name_map_from_answers)
    
    print(f"\nMapped entities: {len(kg1.entity_name_map)}")
    print(f"Total entities in KG: {len(kg1.entities)}")
    
    print("\nKnowledge Graph (with answer-based mapping):")
    print("-" * 70)
    text1 = kg1.to_text()
    print(text1[:1000] + "..." if len(text1) > 1000 else text1)
    
    # Method 2: Using comprehensive mapping from all datasets
    print("\n" + "="*70)
    print("METHOD 2: Using comprehensive entity name mapping")
    print("="*70)
    
    kg2 = loader.sample_to_kg(sample, limit_size=50)
    kg2.load_entity_name_map("data/webqsp/entity_name_map.json")
    
    print(f"\nMapped entities: {len(kg2.entity_name_map)}")
    print(f"Total entities in KG: {len(kg2.entities)}")
    
    print("\nKnowledge Graph (with comprehensive mapping):")
    print("-" * 70)
    text2 = kg2.to_text()
    print(text2[:1000] + "..." if len(text2) > 1000 else text2)
    
    # Compare the two approaches
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    
    # Count how many entities got mapped in each approach
    mapped_in_kg1 = sum(1 for e in kg1.entities.keys() if e in kg1.entity_name_map)
    mapped_in_kg2 = sum(1 for e in kg2.entities.keys() if e in kg2.entity_name_map)
    
    print(f"\nEntities with readable names:")
    print(f"  Method 1 (answers only):     {mapped_in_kg1}/{len(kg1.entities)} ({mapped_in_kg1/len(kg1.entities)*100:.1f}%)")
    print(f"  Method 2 (comprehensive):    {mapped_in_kg2}/{len(kg2.entities)} ({mapped_in_kg2/len(kg2.entities)*100:.1f}%)")
    print(f"  Improvement:                 +{mapped_in_kg2 - mapped_in_kg1} entities ({(mapped_in_kg2-mapped_in_kg1)/len(kg2.entities)*100:.1f}%)")
    
    # Show examples of newly mapped entities
    print("\n" + "="*70)
    print("EXAMPLES OF IMPROVED MAPPINGS")
    print("="*70)
    
    newly_mapped = []
    for entity_id in kg2.entities.keys():
        if entity_id in kg2.entity_name_map and entity_id not in kg1.entity_name_map:
            newly_mapped.append((entity_id, kg2.entity_name_map[entity_id]))
    
    print(f"\nFound {len(newly_mapped)} additional mapped entities")
    print("\nSample of newly mapped entities:")
    for i, (kb_id, text) in enumerate(newly_mapped[:10], 1):
        print(f"  {i}. {kb_id:15s} -> {text}")
    
    if len(newly_mapped) > 10:
        print(f"  ... and {len(newly_mapped) - 10} more")


def test_multiple_questions():
    """Test entity name mapping across multiple questions."""
    print("\n" + "="*70)
    print("Testing Entity Name Mapping Across Multiple Questions")
    print("="*70)
    
    loader = WebQSPLoader()
    
    # Load first 5 questions
    qa_dataset = loader.create_qa_dataset(
        "data/webqsp/test_simple.json",
        num_samples=5,
        max_kg_size=100
    )
    
    print(f"\nLoaded {len(qa_dataset)} questions")
    
    # Apply comprehensive mapping to each
    for i, qa_item in enumerate(qa_dataset, 1):
        kg = qa_item['kg']
        kg.load_entity_name_map()
        
        print(f"\nQuestion {i}: {qa_item['question'][:60]}...")
        print(f"  Entities: {len(kg.entities)}")
        print(f"  Sample relation:")
        
        if kg.relations:
            rel = kg.relations[0]
            head_name = kg.entities[rel.head].name
            tail_name = kg.entities[rel.tail].name
            print(f"    {head_name} --[{rel.relation}]--> {tail_name}")


if __name__ == "__main__":
    # Test basic functionality
    test_entity_name_mapping()
    
    # Test across multiple questions
    test_multiple_questions()
    
    print("\n" + "="*70)
    print("✓ Testing Complete!")
    print("="*70)
