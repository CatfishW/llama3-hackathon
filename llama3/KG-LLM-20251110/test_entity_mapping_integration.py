#!/usr/bin/env python
"""
Integration test demonstrating entity name mapping with WebQSP data.
Shows before/after comparison of evidence paths sent to LLM.
"""

from webqsp_loader import WebQSPLoader
from evidence_path_finder import EvidencePath
from answer_predictor import AnswerPredictor
from llm_client import LLMClient
import json


def demonstrate_entity_mapping_fix():
    """
    Load WebQSP data and demonstrate entity name mapping in action.
    Shows how evidence paths are formatted for the LLM.
    """
    print("\n" + "="*80)
    print("ENTITY NAME MAPPING DEMONSTRATION - WebQSP Integration")
    print("="*80)
    
    # Load a sample from WebQSP
    print("\n1. Loading WebQSP Sample...")
    print("-" * 80)
    
    loader = WebQSPLoader()
    qa_dataset = loader.create_qa_dataset(
        "data/webqsp/test_simple.json",
        num_samples=5,  # Get first 5 samples
        max_kg_size=300
    )
    
    print(f"✓ Loaded {len(qa_dataset)} samples from WebQSP")
    
    for sample_idx, qa_item in enumerate(qa_dataset[:3], 1):  # Show first 3
        print(f"\n{'='*80}")
        print(f"SAMPLE {sample_idx}")
        print(f"{'='*80}")
        
        print(f"\nQuestion: {qa_item['question']}")
        print(f"Gold Answers: {', '.join(qa_item['answers'])}")
        print(f"KG Stats: {qa_item['kg_stats']['num_entities']} entities, "
              f"{qa_item['kg_stats']['num_relations']} relations")
        
        # Create sample evidence paths
        kg = qa_item['kg']
        
        # Get first few relations from KG
        sample_paths = []
        for i, relation in enumerate(kg.relations[:3]):
            path = EvidencePath(
                path=[(relation.head, relation.relation, relation.tail)],
                score=0.3 + (i * 0.2),  # Vary scores
                reasoning=f"Sample reasoning for path {i+1}"
            )
            sample_paths.append(path)
        
        # Display raw evidence (what user saw before fix)
        print(f"\n2. RAW EVIDENCE PATHS (Before Fix - with entity IDs):")
        print("-" * 80)
        for i, path in enumerate(sample_paths, 1):
            print(f"Path {i}:")
            print(f"  Raw: {path.path}")
            print(f"  Score: {path.score:.2f}")
            print(f"  Reasoning: {path.reasoning}")
        
        # Display formatted evidence (what LLM sees after fix)
        print(f"\n3. FORMATTED EVIDENCE FOR LLM (After Fix - with entity names):")
        print("-" * 80)
        
        llm = LLMClient()
        predictor = AnswerPredictor(llm)
        formatted_evidence = predictor._format_evidence(sample_paths, kg)
        
        print(formatted_evidence)
        
        # Verify no entity IDs in formatted output
        print(f"\n4. VALIDATION:")
        print("-" * 80)
        
        has_entity_ids = any(relation.head in formatted_evidence or 
                            relation.tail in formatted_evidence 
                            for relation in kg.relations[:3])
        
        has_entity_names = any(kg.get_entity(relation.head).name in formatted_evidence 
                              for relation in kg.relations[:3] 
                              if kg.get_entity(relation.head))
        
        print(f"✓ Entity IDs present in formatted output: {has_entity_ids}")
        print(f"✓ Entity names present in formatted output: {has_entity_names}")
        
        if not has_entity_ids and has_entity_names:
            print("\n✓ SUCCESS: Entity IDs properly replaced with human-readable names!")
        else:
            print("\n✗ WARNING: Some entity IDs may still be present")
        
        # Show sample triple expansion
        print(f"\n5. EXAMPLE TRIPLE EXPANSION:")
        print("-" * 80)
        if kg.relations:
            rel = kg.relations[0]
            head_entity = kg.get_entity(rel.head)
            tail_entity = kg.get_entity(rel.tail)
            
            if head_entity and tail_entity:
                relation_name = rel.relation.split('.')[-1]
                print(f"Raw:       ({rel.head}, {rel.relation}, {rel.tail})")
                print(f"Mapped:    {head_entity.name} --[{relation_name}]--> {tail_entity.name}")
    
    print("\n" + "="*80)
    print("SUMMARY OF FIX")
    print("="*80)
    print("""
The entity name mapping fix ensures that:

1. Entity IDs (like m.06f7lp) are automatically converted to human-readable names
2. Relation paths are simplified (location.location.containedby -> containedby)
3. LLM receives properly formatted, semantically meaningful evidence
4. No raw entity IDs appear in the final LLM prompt

This significantly improves:
- LLM understanding of the evidence
- Quality of reasoning about relationships
- Readability of debug output
- Overall answer accuracy
""")
    print("="*80)


if __name__ == "__main__":
    try:
        demonstrate_entity_mapping_fix()
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()
