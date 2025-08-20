#!/usr/bin/env python3
"""
Enhanced Knowledge Graph Subgraph Classifier with Batch Processing

This script provides advanced subgraph classification capabilities including:
- Batch processing of multiple entities
- Statistical analysis across different subgraph types
- Visualization of subgraph characteristics
- Export capabilities in multiple formats

Usage examples:
    # Analyze a specific entity
    python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --entity "Berlin"
    
    # Batch analyze top entities
    python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --batch-top 10
    
    # Analyze by predicate type
    python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --predicate-analysis
"""

import argparse
import json
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from kg_loader import KnowledgeGraph, load_kg, Triple
from subgraph_classifier import SubgraphClassifier

class EnhancedSubgraphClassifier(SubgraphClassifier):
    def __init__(self, kg: KnowledgeGraph):
        super().__init__(kg)
        
    def get_top_entities_by_degree(self, top_n: int = 20) -> List[Tuple[str, int]]:
        """Get top entities by their degree (number of connections)."""
        entity_degrees = []
        
        # Calculate degrees for all entities
        all_entities = set(self.kg.sp_index.keys()) | set(self.kg.os_index.keys())
        
        for entity in all_entities:
            degree = self.kg.degree(entity)
            entity_degrees.append((entity, degree))
            
        # Sort by degree descending
        entity_degrees.sort(key=lambda x: x[1], reverse=True)
        return entity_degrees[:top_n]
        
    def batch_classify_entities(self, entities: List[str]) -> Dict[str, Dict[str, List[Triple]]]:
        """Classify subgraphs for multiple entities."""
        results = {}
        
        for i, entity in enumerate(entities):
            if i % 10 == 0:
                print(f"Processing entity {i+1}/{len(entities)}: {entity}")
                
            results[entity] = self.classify_subgraphs(entity)
            
        return results
        
    def analyze_predicate_distribution(self) -> Dict[str, Dict[str, int]]:
        """Analyze the distribution of predicates across the knowledge graph."""
        stats = {
            'total_predicates': len(self.kg.predicates()),
            'predicate_counts': {},
            'predicate_types': {
                'description': 0,
                'literal': 0,
                'relation': 0
            }
        }
        
        for predicate in self.kg.predicates():
            count = len(self.kg.triples_with_predicate(predicate))
            stats['predicate_counts'][predicate] = count
            
            if self.is_description_predicate(predicate):
                stats['predicate_types']['description'] += count
            elif self.is_literal_predicate(predicate):
                stats['predicate_types']['literal'] += count
            else:
                stats['predicate_types']['relation'] += count
                
        return stats
        
    def find_entities_with_rich_subgraphs(self, min_types: int = 3) -> List[str]:
        """Find entities that have rich subgraphs (multiple types of connections)."""
        rich_entities = []
        
        top_entities = self.get_top_entities_by_degree(100)
        
        for entity, degree in top_entities:
            if degree < 5:  # Skip entities with very few connections
                continue
                
            classifications = self.classify_subgraphs(entity)
            
            # Count non-empty subgraph types
            non_empty_types = sum(1 for triples in classifications.values() if triples)
            
            if non_empty_types >= min_types:
                rich_entities.append(entity)
                
        return rich_entities
        
    def generate_subgraph_report(self, entities: List[str], output_file: str):
        """Generate a comprehensive report for multiple entities."""
        batch_results = self.batch_classify_entities(entities)
        
        # Aggregate statistics
        report = {
            'summary': {
                'total_entities_analyzed': len(entities),
                'total_unique_predicates': len(self.kg.predicates()),
                'total_triples': len(self.kg.triples)
            },
            'entity_analysis': {},
            'global_statistics': {
                'subgraph_type_distribution': {
                    'one_hop': {'total_triples': 0, 'entities_with_data': 0},
                    'two_hop': {'total_triples': 0, 'entities_with_data': 0},
                    'description': {'total_triples': 0, 'entities_with_data': 0},
                    'literal': {'total_triples': 0, 'entities_with_data': 0}
                }
            }
        }
        
        # Analyze each entity
        for entity, classifications in batch_results.items():
            entity_stats = {}
            
            for subgraph_type, triples in classifications.items():
                stats = self.analyze_triple_patterns(triples)
                entity_stats[subgraph_type] = stats
                
                # Update global statistics
                global_stats = report['global_statistics']['subgraph_type_distribution'][subgraph_type]
                global_stats['total_triples'] += len(triples)
                if triples:
                    global_stats['entities_with_data'] += 1
                    
            report['entity_analysis'][entity] = entity_stats
            
        # Add predicate analysis
        report['predicate_analysis'] = self.analyze_predicate_distribution()
        
        # Save report
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"Comprehensive report saved to {output_file}")
        return report
        
    def export_to_csv(self, entities: List[str], output_file: str):
        """Export subgraph statistics to CSV format."""
        batch_results = self.batch_classify_entities(entities)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'entity', 'subgraph_type', 'total_triples', 'unique_predicates',
                'unique_subjects', 'unique_objects', 'literal_objects',
                'description_predicates', 'literal_predicates'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for entity, classifications in batch_results.items():
                for subgraph_type, triples in classifications.items():
                    stats = self.analyze_triple_patterns(triples)
                    row = {'entity': entity, 'subgraph_type': subgraph_type}
                    row.update(stats)
                    writer.writerow(row)
                    
        print(f"CSV export saved to {output_file}")
        
    def find_similar_entities(self, target_entity: str, similarity_threshold: float = 0.5) -> List[Tuple[str, float]]:
        """Find entities with similar subgraph patterns."""
        target_classifications = self.classify_subgraphs(target_entity)
        target_signature = self._get_entity_signature(target_classifications)
        
        similar_entities = []
        top_entities = self.get_top_entities_by_degree(200)
        
        for entity, _ in top_entities:
            if entity == target_entity:
                continue
                
            entity_classifications = self.classify_subgraphs(entity)
            entity_signature = self._get_entity_signature(entity_classifications)
            
            similarity = self._calculate_signature_similarity(target_signature, entity_signature)
            
            if similarity >= similarity_threshold:
                similar_entities.append((entity, similarity))
                
        similar_entities.sort(key=lambda x: x[1], reverse=True)
        return similar_entities[:10]
        
    def _get_entity_signature(self, classifications: Dict[str, List[Triple]]) -> Dict[str, float]:
        """Get a signature vector for an entity based on its subgraph characteristics."""
        signature = {}
        
        total_triples = sum(len(triples) for triples in classifications.values())
        if total_triples == 0:
            return {}
            
        for subgraph_type, triples in classifications.items():
            stats = self.analyze_triple_patterns(triples)
            
            # Normalize by total triples to get proportions
            signature[f'{subgraph_type}_ratio'] = len(triples) / total_triples
            signature[f'{subgraph_type}_predicate_diversity'] = stats['unique_predicates'] / max(1, len(triples))
            signature[f'{subgraph_type}_literal_ratio'] = stats['literal_objects'] / max(1, len(triples))
            
        return signature
        
    def _calculate_signature_similarity(self, sig1: Dict[str, float], sig2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two entity signatures."""
        if not sig1 or not sig2:
            return 0.0
            
        # Get common keys
        common_keys = set(sig1.keys()) & set(sig2.keys())
        if not common_keys:
            return 0.0
            
        # Calculate dot product and norms
        dot_product = sum(sig1[key] * sig2[key] for key in common_keys)
        norm1 = sum(sig1[key] ** 2 for key in common_keys) ** 0.5
        norm2 = sum(sig2[key] ** 2 for key in common_keys) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)

def main():
    parser = argparse.ArgumentParser(description='Enhanced knowledge graph subgraph classifier')
    parser.add_argument('--triples', required=True, help='Path to triples TSV.gz file')
    parser.add_argument('--alias', help='Path to alias JSON file')
    parser.add_argument('--entity', help='Specific entity to analyze')
    parser.add_argument('--limit', type=int, help='Limit number of triples loaded')
    
    # Batch processing options
    parser.add_argument('--batch-top', type=int, help='Analyze top N entities by degree')
    parser.add_argument('--batch-entities', nargs='+', help='List of specific entities to analyze')
    parser.add_argument('--rich-subgraphs', action='store_true', help='Find entities with rich subgraphs')
    
    # Analysis options
    parser.add_argument('--predicate-analysis', action='store_true', help='Analyze predicate distribution')
    parser.add_argument('--similarity', help='Find entities similar to specified entity')
    
    # Output options
    parser.add_argument('--report', help='Generate comprehensive JSON report')
    parser.add_argument('--csv', help='Export to CSV file')
    parser.add_argument('--max-display', type=int, default=10, help='Max items to display')
    
    args = parser.parse_args()
    
    print("Loading knowledge graph...")
    kg = load_kg(args.triples, args.alias, args.limit)
    print(f"Loaded knowledge graph: {kg.summary()}")
    
    classifier = EnhancedSubgraphClassifier(kg)
    
    # Single entity analysis
    if args.entity:
        classifier.print_subgraph_analysis(args.entity, args.max_display)
        
        if args.similarity:
            print(f"\nFinding entities similar to '{args.entity}':")
            similar = classifier.find_similar_entities(args.entity)
            for entity, similarity in similar:
                print(f"  {similarity:.3f}: {entity}")
    
    # Batch processing
    entities_to_process = []
    
    if args.batch_top:
        print(f"\nTop {args.batch_top} entities by degree:")
        top_entities = classifier.get_top_entities_by_degree(args.batch_top)
        for i, (entity, degree) in enumerate(top_entities):
            print(f"  {i+1}. {entity} (degree: {degree})")
        entities_to_process = [entity for entity, _ in top_entities]
        
    if args.batch_entities:
        entities_to_process.extend(args.batch_entities)
        
    if args.rich_subgraphs:
        print("\nFinding entities with rich subgraphs...")
        rich_entities = classifier.find_entities_with_rich_subgraphs()
        print(f"Found {len(rich_entities)} entities with rich subgraphs:")
        for entity in rich_entities[:args.max_display]:
            print(f"  - {entity}")
        entities_to_process = rich_entities
    
    # Generate outputs
    if entities_to_process:
        if args.report:
            classifier.generate_subgraph_report(entities_to_process, args.report)
            
        if args.csv:
            classifier.export_to_csv(entities_to_process, args.csv)
    
    # Predicate analysis
    if args.predicate_analysis:
        print("\n=== Predicate Analysis ===")
        predicate_stats = classifier.analyze_predicate_distribution()
        
        print(f"Total predicates: {predicate_stats['total_predicates']}")
        print("\nPredicate type distribution:")
        for pred_type, count in predicate_stats['predicate_types'].items():
            print(f"  {pred_type}: {count}")
            
        print(f"\nTop {args.max_display} most frequent predicates:")
        sorted_predicates = sorted(predicate_stats['predicate_counts'].items(), 
                                 key=lambda x: x[1], reverse=True)
        for predicate, count in sorted_predicates[:args.max_display]:
            print(f"  {count}: {predicate}")

if __name__ == '__main__':
    main()
