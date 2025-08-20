#!/usr/bin/env python3
"""
Test script to demonstrate the differences between one-hop and two-hop subgraphs
"""

from kg_loader import load_kg
from subgraph_classifier import SubgraphClassifier

def demonstrate_hop_differences():
    """Demonstrate the clear differences between one-hop and two-hop subgraphs."""
    
    print("Loading knowledge graph...")
    kg = load_kg("rogkg_triples.tsv.gz", "rogkg_alias_map.json", limit=2000)
    classifier = SubgraphClassifier(kg)
    
    entity = "'03 Bonnie & Clyde"
    print(f"\nAnalyzing entity: {entity}")
    print("=" * 60)
    
    # Get detailed classification
    detailed_results = classifier.classify_subgraphs_detailed(entity)
    
    one_hop = detailed_results['one_hop']
    two_hop_full = detailed_results['two_hop_full']
    second_hop_only = detailed_results['second_hop_only']
    
    print(f"One-hop subgraph: {len(one_hop)} triples")
    print(f"Two-hop subgraph (full): {len(two_hop_full)} triples")
    print(f"Second-hop only: {len(second_hop_only)} triples")
    print(f"Verification: {len(one_hop)} + {len(second_hop_only)} = {len(one_hop) + len(second_hop_only)} (should be close to {len(two_hop_full)})")
    
    # Convert to sets for analysis
    one_hop_set = set(one_hop)
    two_hop_set = set(two_hop_full)
    second_hop_set = set(second_hop_only)
    
    # Find triples that are in two-hop but not in one-hop
    additional_in_two_hop = two_hop_set - one_hop_set
    
    print(f"\nTriples in two-hop but not in one-hop: {len(additional_in_two_hop)}")
    print("\nSample additional triples in two-hop:")
    for i, (s, p, o) in enumerate(list(additional_in_two_hop)[:10]):
        print(f"  {i+1}. {s} -> {p} -> {o}")
        
    print(f"\nSecond-hop only triples (new entities 2 hops away):")
    for i, (s, p, o) in enumerate(second_hop_only[:10]):
        print(f"  {i+1}. {s} -> {p} -> {o}")
    
    # Analyze the entities in each hop
    print(f"\n--- Entity Analysis ---")
    
    # Entities in one-hop
    one_hop_entities = set()
    for s, p, o in one_hop:
        one_hop_entities.add(s)
        one_hop_entities.add(o)
    one_hop_entities.discard(entity)  # Remove the central entity
    
    # Entities in second-hop only
    second_hop_entities = set()
    for s, p, o in second_hop_only:
        second_hop_entities.add(s)
        second_hop_entities.add(o)
    
    print(f"Entities directly connected to '{entity}' (1st hop): {len(one_hop_entities)}")
    print(f"New entities found in 2nd hop: {len(second_hop_entities)}")
    
    print(f"\nSample 1st hop entities:")
    for i, ent in enumerate(list(one_hop_entities)[:5]):
        print(f"  {i+1}. {ent}")
        
    print(f"\nSample 2nd hop entities:")
    for i, ent in enumerate(list(second_hop_entities)[:5]):
        print(f"  {i+1}. {ent}")

if __name__ == "__main__":
    demonstrate_hop_differences()
