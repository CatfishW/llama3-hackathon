#!/usr/bin/env python
"""Test entity name mapping in evidence paths."""

from evidence_path_finder import EvidencePath
from knowledge_graph import KnowledgeGraph, Entity, Relation
import json


def create_test_kg():
    """Create a test knowledge graph with some entities and relations."""
    kg = KnowledgeGraph()
    
    # Add entities with IDs and names
    entities = [
        Entity(id="m.06f7lp", name="Jamaica", type="location"),
        Entity(id="m.03_r3", name="Caribbean", type="region"),
        Entity(id="m.0k8nhx5", name="Person_1", type="person"),
        Entity(id="m.02x3yvv", name="Hurricane", type="weather"),
        Entity(id="m.01nty", name="Atlantic", type="location"),
    ]
    
    for entity in entities:
        kg.add_entity(entity)
    
    # Add relations
    relations = [
        Relation(head="m.06f7lp", relation="location.location.containedby", tail="m.03_r3"),
        Relation(head="m.0k8nhx5", relation="people.person.nationality", tail="m.03_r3"),
        Relation(head="m.02x3yvv", relation="meteorology.tropical_cyclone.affected_areas", tail="m.01nty"),
    ]
    
    for relation in relations:
        kg.add_relation(relation)
    
    return kg


def test_entity_mapping():
    """Test that entity names are properly mapped in evidence paths."""
    print("\n" + "="*70)
    print("ENTITY NAME MAPPING TEST")
    print("="*70)
    
    # Create test KG
    kg = create_test_kg()
    
    print("\n1. Knowledge Graph Entities:")
    print("-" * 70)
    for entity_id, entity in kg.entities.items():
        print(f"   {entity_id} -> {entity.name} ({entity.type})")
    
    print("\n2. Test Evidence Paths:")
    print("-" * 70)
    
    # Test Case 1: Location containment
    path1 = EvidencePath(
        path=[("m.06f7lp", "location.location.containedby", "m.03_r3")],
        score=0.3,
        reasoning="This path shows a geographical relationship"
    )
    
    text1 = path1.to_text(kg)
    print(f"\n   Path 1 (Geographic containment):")
    print(f"   Raw: {path1.path}")
    print(f"   Mapped: {text1}")
    
    # Verify entity IDs are replaced with names
    assert "m.06f7lp" not in text1, "Entity ID m.06f7lp should be replaced with Jamaica"
    assert "m.03_r3" not in text1, "Entity ID m.03_r3 should be replaced with Caribbean"
    assert "Jamaica" in text1, "Jamaica name should appear"
    assert "Caribbean" in text1, "Caribbean name should appear"
    assert "containedby" in text1, "Relation name should be simplified"
    assert "location.location" not in text1, "Full relation path should not appear"
    print("   ✓ PASS: Entity IDs properly mapped to names")
    
    # Test Case 2: Person-nationality relationship
    path2 = EvidencePath(
        path=[("m.0k8nhx5", "people.person.nationality", "m.03_r3")],
        score=0.4,
        reasoning="This shows nationality relationship"
    )
    
    text2 = path2.to_text(kg)
    print(f"\n   Path 2 (Nationality relationship):")
    print(f"   Raw: {path2.path}")
    print(f"   Mapped: {text2}")
    
    assert "m.0k8nhx5" not in text2, "Entity ID m.0k8nhx5 should be replaced"
    assert "Person_1" in text2, "Person_1 name should appear"
    assert "nationality" in text2, "Relation name should be simplified"
    print("   ✓ PASS: Relation path properly simplified")
    
    # Test Case 3: Multi-hop path
    path3 = EvidencePath(
        path=[
            ("m.06f7lp", "location.location.containedby", "m.03_r3"),
            ("m.03_r3", "base.lightweight.profession.specialization_of", "m.0k8nhx5")
        ],
        score=0.5,
        reasoning="Multi-hop reasoning path"
    )
    
    text3 = path3.to_text(kg)
    print(f"\n   Path 3 (Multi-hop):")
    print(f"   Raw: {path3.path}")
    print(f"   Mapped: {text3}")
    
    assert "m.06f7lp" not in text3, "All entity IDs should be mapped"
    assert "m.03_r3" not in text3, "All entity IDs should be mapped"
    assert "m.0k8nhx5" not in text3, "All entity IDs should be mapped"
    assert "Jamaica" in text3, "Jamaica should appear"
    assert "Caribbean" in text3, "Caribbean should appear"
    assert "Person_1" in text3, "Person_1 should appear"
    assert "→" in text3, "Multi-hop indicator should be present"
    print("   ✓ PASS: Multi-hop paths properly mapped")
    
    # Test Case 4: Missing entities (fallback to ID)
    path4 = EvidencePath(
        path=[("m.06f7lp", "location.location.contains", "m.unknown_id")],
        score=0.2,
        reasoning="Path with unknown entity"
    )
    
    text4 = path4.to_text(kg)
    print(f"\n   Path 4 (Unknown entity - fallback):")
    print(f"   Raw: {path4.path}")
    print(f"   Mapped: {text4}")
    
    assert "Jamaica" in text4, "Known entity should be mapped"
    assert "m.unknown_id" in text4, "Unknown entity ID should appear as fallback"
    print("   ✓ PASS: Unknown entities fall back to ID")
    
    print("\n" + "="*70)
    print("3. Formatted Evidence for LLM:")
    print("="*70)
    
    from answer_predictor import AnswerPredictor
    from llm_client import LLMClient
    
    # Create a dummy predictor to test formatting
    llm = LLMClient()  # Dummy client
    predictor = AnswerPredictor(llm)
    
    evidence_paths = [path1, path2, path3]
    formatted = predictor._format_evidence(evidence_paths, kg)
    
    print("\nFormatted evidence for LLM prompt:")
    print("-" * 70)
    print(formatted)
    
    # Verify no entity IDs appear in final formatting
    assert "m.06f7lp" not in formatted, "Entity IDs should not appear in final formatting"
    assert "m.03_r3" not in formatted, "Entity IDs should not appear in final formatting"
    assert "m.0k8nhx5" not in formatted, "Entity IDs should not appear in final formatting"
    assert "location.location" not in formatted, "Full relation paths should not appear"
    print("\n   ✓ PASS: No entity IDs in final formatted evidence")
    
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED!")
    print("="*70)
    print("\nSummary:")
    print("- Entity IDs are properly mapped to human-readable names")
    print("- Relation paths are simplified (e.g., location.location.containedby -> containedby)")
    print("- Multi-hop paths are formatted clearly with → separator")
    print("- Unknown entities fall back to ID gracefully")
    print("- Final formatted evidence contains NO entity IDs (only names)")


if __name__ == "__main__":
    test_entity_mapping()
