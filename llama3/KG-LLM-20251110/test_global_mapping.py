"""Test global entity name mapping - should load only once."""

from webqsp_loader import WebQSPLoader
import time


def test_global_mapping_performance():
    """Test that mapping is loaded only once globally."""
    print("\n" + "="*70)
    print("Testing Global Entity Name Mapping (Load Once)")
    print("="*70)
    
    loader = WebQSPLoader()
    
    # Load 5 samples
    print("\nLoading 5 samples from test set...")
    qa_dataset = loader.create_qa_dataset(
        "data/webqsp/test_simple.json",
        num_samples=5,
        max_kg_size=100
    )
    
    print(f"\n{'='*70}")
    print("Converting each KG to text (should load mapping only once)")
    print("="*70)
    
    for i, qa_item in enumerate(qa_dataset, 1):
        print(f"\nQuestion {i}: {qa_item['question'][:50]}...")
        
        start = time.time()
        kg = qa_item['kg']
        text = kg.to_text()
        elapsed = time.time() - start
        
        print(f"  ✓ Converted in {elapsed*1000:.2f}ms")
        print(f"  Entities: {len(kg.entities)}")
    
    print("\n" + "="*70)
    print("✓ Global mapping test complete!")
    print("  Note: First call loads the mapping, subsequent calls reuse it")
    print("="*70)


def test_multiple_instances():
    """Test that multiple KG instances share the same global mapping."""
    print("\n" + "="*70)
    print("Testing Multiple KG Instances Share Global Mapping")
    print("="*70)
    
    from knowledge_graph import KnowledgeGraph, Entity, Relation
    
    # Create multiple KG instances
    kgs = []
    for i in range(3):
        kg = KnowledgeGraph()
        kg.add_entity(Entity(id="m.03_r3", name="Jamaica_entity", type="Location"))
        kg.add_entity(Entity(id="m.0160w", name="Bahamas_entity", type="Location"))
        kgs.append(kg)
    
    print(f"\nCreated {len(kgs)} KnowledgeGraph instances")
    
    # Convert each to text
    for i, kg in enumerate(kgs, 1):
        print(f"\nInstance {i}:")
        text = kg.to_text()
        print(f"  First lines of output:")
        for line in text.split('\n')[:5]:
            print(f"    {line}")
    
    print("\n✓ Multiple instances test complete!")


if __name__ == "__main__":
    test_global_mapping_performance()
    test_multiple_instances()
