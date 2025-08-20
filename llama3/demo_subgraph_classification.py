#!/usr/bin/env python3
"""
Knowledge Graph Subgraph Classification Demo

This script demonstrates how to use the subgraph classifiers with various examples
and provides a simple interface for exploring the knowledge graph.

Usage:
    python demo_subgraph_classification.py
"""

import sys
from pathlib import Path
from kg_loader import load_kg
from subgraph_classifier import SubgraphClassifier
from enhanced_subgraph_classifier import EnhancedSubgraphClassifier

def demo_basic_classification():
    """Demonstrate basic subgraph classification."""
    print("=== Basic Subgraph Classification Demo ===\n")
    
    # Load a sample of the knowledge graph
    print("Loading knowledge graph sample...")
    kg = load_kg("rogkg_triples.tsv.gz", "rogkg_alias_map.json", limit=5000)
    print(f"Loaded: {kg.summary()}\n")
    
    classifier = SubgraphClassifier(kg)
    
    # Find some entities to analyze
    print("Finding top entities by connection degree...")
    enhanced_classifier = EnhancedSubgraphClassifier(kg)
    top_entities = enhanced_classifier.get_top_entities_by_degree(5)
    
    print("Top 5 entities:")
    for i, (entity, degree) in enumerate(top_entities):
        print(f"  {i+1}. {entity} (degree: {degree})")
    
    # Analyze the first entity
    if top_entities:
        entity = top_entities[0][0]
        print(f"\n--- Analyzing: {entity} ---")
        
        classifications = classifier.classify_subgraphs(entity)
        
        for subgraph_type, triples in classifications.items():
            print(f"\n{subgraph_type.upper()} subgraph: {len(triples)} triples")
            
            if triples:
                print("Sample triples:")
                for i, (s, p, o) in enumerate(triples[:3]):
                    print(f"  {i+1}. {s} --[{p}]--> {o}")
                if len(triples) > 3:
                    print(f"  ... and {len(triples) - 3} more")

def demo_predicate_analysis():
    """Demonstrate predicate pattern analysis."""
    print("\n=== Predicate Analysis Demo ===\n")
    
    kg = load_kg("rogkg_triples.tsv.gz", "rogkg_alias_map.json", limit=3000)
    classifier = EnhancedSubgraphClassifier(kg)
    
    # Analyze predicate distribution
    predicate_stats = classifier.analyze_predicate_distribution()
    
    print(f"Total predicates in graph: {predicate_stats['total_predicates']}")
    print("\nPredicate type distribution:")
    for pred_type, count in predicate_stats['predicate_types'].items():
        percentage = (count / sum(predicate_stats['predicate_types'].values())) * 100
        print(f"  {pred_type}: {count} ({percentage:.1f}%)")
    
    print("\nMost frequent predicates:")
    sorted_predicates = sorted(predicate_stats['predicate_counts'].items(), 
                             key=lambda x: x[1], reverse=True)
    for i, (predicate, count) in enumerate(sorted_predicates[:10]):
        print(f"  {i+1}. {predicate}: {count} triples")

def demo_subgraph_comparison():
    """Demonstrate comparison of different entities' subgraph patterns."""
    print("\n=== Subgraph Pattern Comparison Demo ===\n")
    
    kg = load_kg("rogkg_triples.tsv.gz", "rogkg_alias_map.json", limit=4000)
    enhanced_classifier = EnhancedSubgraphClassifier(kg)
    
    # Get some entities with rich subgraphs
    rich_entities = enhanced_classifier.find_entities_with_rich_subgraphs(min_types=2)
    
    if len(rich_entities) >= 2:
        entity1, entity2 = rich_entities[0], rich_entities[1]
        print(f"Comparing subgraph patterns between:")
        print(f"  Entity 1: {entity1}")
        print(f"  Entity 2: {entity2}")
        
        for entity in [entity1, entity2]:
            classifications = enhanced_classifier.classify_subgraphs(entity)
            print(f"\n{entity}:")
            
            for subgraph_type, triples in classifications.items():
                if triples:
                    stats = enhanced_classifier.analyze_triple_patterns(triples)
                    print(f"  {subgraph_type}: {stats['total_triples']} triples, "
                          f"{stats['unique_predicates']} predicates, "
                          f"{stats['literal_objects']} literals")
        
        # Find similar entities
        similar = enhanced_classifier.find_similar_entities(entity1, similarity_threshold=0.3)
        if similar:
            print(f"\nEntities similar to {entity1}:")
            for entity, similarity in similar[:3]:
                print(f"  {similarity:.3f}: {entity}")
    else:
        print("Not enough entities with rich subgraphs found in this sample.")

def demo_export_capabilities():
    """Demonstrate export and reporting capabilities."""
    print("\n=== Export and Reporting Demo ===\n")
    
    kg = load_kg("rogkg_triples.tsv.gz", "rogkg_alias_map.json", limit=2000)
    enhanced_classifier = EnhancedSubgraphClassifier(kg)
    
    # Get top entities for analysis
    top_entities = enhanced_classifier.get_top_entities_by_degree(5)
    entities = [entity for entity, _ in top_entities]
    
    print(f"Generating reports for {len(entities)} entities...")
    
    # Generate comprehensive report
    report_file = "subgraph_analysis_report.json"
    enhanced_classifier.generate_subgraph_report(entities, report_file)
    
    # Generate CSV export
    csv_file = "subgraph_analysis.csv"
    enhanced_classifier.export_to_csv(entities, csv_file)
    
    print(f"\nFiles generated:")
    print(f"  - {report_file}: Comprehensive JSON report")
    print(f"  - {csv_file}: CSV data for spreadsheet analysis")

def interactive_explorer():
    """Interactive exploration of the knowledge graph."""
    print("\n=== Interactive Knowledge Graph Explorer ===\n")
    
    kg = load_kg("rogkg_triples.tsv.gz", "rogkg_alias_map.json", limit=5000)
    classifier = SubgraphClassifier(kg)
    enhanced_classifier = EnhancedSubgraphClassifier(kg)
    
    print("Commands:")
    print("  search <pattern>     - Search for entities")
    print("  analyze <entity>     - Analyze entity subgraphs")
    print("  top [n]             - Show top entities by degree")
    print("  similar <entity>     - Find similar entities")
    print("  help                - Show this help")
    print("  quit                - Exit")
    
    while True:
        try:
            cmd = input("\nkg> ").strip().split()
            if not cmd:
                continue
                
            if cmd[0] == 'quit':
                break
            elif cmd[0] == 'help':
                print("Commands:")
                print("  search <pattern>     - Search for entities")
                print("  analyze <entity>     - Analyze entity subgraphs")
                print("  top [n]             - Show top entities by degree")
                print("  similar <entity>     - Find similar entities")
                print("  help                - Show this help")
                print("  quit                - Exit")
            elif cmd[0] == 'search' and len(cmd) > 1:
                pattern = ' '.join(cmd[1:])
                entities = classifier.find_entities_by_pattern(pattern, max_results=10)
                if entities:
                    print(f"Found {len(entities)} entities matching '{pattern}':")
                    for i, entity in enumerate(entities):
                        print(f"  {i+1}. {entity}")
                else:
                    print(f"No entities found matching '{pattern}'")
            elif cmd[0] == 'analyze' and len(cmd) > 1:
                entity = ' '.join(cmd[1:])
                print(f"\nAnalyzing: {entity}")
                classifier.print_subgraph_analysis(entity, max_display=5)
            elif cmd[0] == 'top':
                n = int(cmd[1]) if len(cmd) > 1 else 10
                top_entities = enhanced_classifier.get_top_entities_by_degree(n)
                print(f"Top {n} entities by degree:")
                for i, (entity, degree) in enumerate(top_entities):
                    print(f"  {i+1}. {entity} (degree: {degree})")
            elif cmd[0] == 'similar' and len(cmd) > 1:
                entity = ' '.join(cmd[1:])
                similar = enhanced_classifier.find_similar_entities(entity)
                if similar:
                    print(f"Entities similar to '{entity}':")
                    for ent, similarity in similar:
                        print(f"  {similarity:.3f}: {ent}")
                else:
                    print(f"No similar entities found for '{entity}'")
            else:
                print("Invalid command. Type 'help' for available commands.")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Run all demonstrations."""
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        interactive_explorer()
        return
    
    print("Knowledge Graph Subgraph Classification Demonstration")
    print("=" * 60)
    
    try:
        demo_basic_classification()
        demo_predicate_analysis()
        demo_subgraph_comparison()
        demo_export_capabilities()
        
        print("\n" + "=" * 60)
        print("Demo completed! To explore interactively, run:")
        print("  python demo_subgraph_classification.py interactive")
        
    except FileNotFoundError as e:
        print(f"Error: Could not find required files. Make sure you have:")
        print("  - rogkg_triples.tsv.gz")
        print("  - rogkg_alias_map.json")
        print("  - kg_loader.py")
        print("  - subgraph_classifier.py")
        print("  - enhanced_subgraph_classifier.py")
        print(f"\nSpecific error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
