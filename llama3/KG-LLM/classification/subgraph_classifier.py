#!/usr/bin/env python3
"""
Knowledge Graph Subgraph Classifier

This script classifies subgraphs from a knowledge graph into four categories:
1. One-hop subgraph: Direct connections from a central entity
2. Two-hop subgraph: Connections within 2 hops from a central entity
3. Description subgraph: Subgraphs containing descriptive/literal information
4. Literal subgraph: Subgraphs with literal values (strings, numbers, dates)

Usage:
    python subgraph_classifier.py --triples rogkg_triples.tsv.gz --alias rogkg_alias_map.json --entity "Adventures by Disney"
"""

import argparse
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from kg_loader import KnowledgeGraph, load_kg, Triple
try:
    from question_retrieval import QuestionGraphRetriever
except ImportError:  # pragma: no cover
    QuestionGraphRetriever = None  # type: ignore

class SubgraphClassifier:
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        
        # Predicate patterns for classification
        self.description_predicates = {
            'description', 'summary', 'abstract', 'overview', 'note', 'comment',
            'caption', 'text', 'content', 'details', 'info', 'biography'
        }
        
        self.literal_predicates = {
            'name', 'title', 'label', 'alias', 'id', 'code', 'number', 'count',
            'date', 'time', 'year', 'age', 'height', 'weight', 'price', 'value',
            'amount', 'size', 'length', 'width', 'area', 'volume', 'temperature'
        }
        
        # Regular expressions for literal detection
        self.number_pattern = re.compile(r'^[\d\.,]+$')
        self.date_pattern = re.compile(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}')
        self.year_pattern = re.compile(r'^\d{4}$')
        self.url_pattern = re.compile(r'^https?://|^www\.|\.com$|\.org$|\.net$')
        
    def is_literal_value(self, value: str) -> bool:
        """Check if a value appears to be a literal (number, date, simple string)."""
        if not value or len(value.strip()) == 0:
            return False
            
        value = value.strip()
        
        # Check for numbers
        if self.number_pattern.match(value):
            return True
            
        # Check for dates
        if self.date_pattern.search(value):
            return True
            
        # Check for years
        if self.year_pattern.match(value):
            return True
            
        # Check for URLs
        if self.url_pattern.search(value.lower()):
            return True
            
        # Simple string literals (short, no complex structure)
        if len(value) < 50 and not any(char in value for char in '()[]{}'):
            return True
            
        return False
        
    def is_description_predicate(self, predicate: str) -> bool:
        """Check if predicate indicates descriptive content."""
        pred_lower = predicate.lower()
        return any(desc_pred in pred_lower for desc_pred in self.description_predicates)
        
    def is_literal_predicate(self, predicate: str) -> bool:
        """Check if predicate indicates literal content."""
        pred_lower = predicate.lower()
        return any(lit_pred in pred_lower for lit_pred in self.literal_predicates)
        
    def extract_one_hop_subgraph(self, entity: str) -> List[Triple]:
        """Extract all triples directly connected to the entity."""
        subgraph = []
        
        # Entity as subject
        for predicate, obj in self.kg.sp_index.get(entity, []):
            subgraph.append((entity, predicate, obj))
            
        # Entity as object
        for subj, predicate in self.kg.os_index.get(entity, []):
            subgraph.append((subj, predicate, entity))
            
        return subgraph
        
    def extract_two_hop_subgraph(self, entity: str, max_size: int = 100) -> List[Triple]:
        """Extract subgraph within 2 hops of the entity."""
        visited_entities = {entity}
        subgraph = []
        
        # First hop - get all directly connected entities
        first_hop_entities = set()
        
        # Entity as subject in first hop
        for predicate, obj in self.kg.sp_index.get(entity, []):
            subgraph.append((entity, predicate, obj))
            if obj != entity:  # Avoid self-loops
                first_hop_entities.add(obj)
                visited_entities.add(obj)
            
        # Entity as object in first hop
        for subj, predicate in self.kg.os_index.get(entity, []):
            subgraph.append((subj, predicate, entity))
            if subj != entity:  # Avoid self-loops
                first_hop_entities.add(subj)
                visited_entities.add(subj)
            
        # Second hop - explore from first hop entities
        second_hop_entities = set()
        for hop1_entity in first_hop_entities:
            if len(subgraph) >= max_size:
                break
                
            # From first hop entity as subject
            for predicate, obj in self.kg.sp_index.get(hop1_entity, []):
                # Include the triple if object is new or is our original entity
                if obj not in visited_entities or obj == entity:
                    subgraph.append((hop1_entity, predicate, obj))
                    if obj not in visited_entities:
                        second_hop_entities.add(obj)
                        visited_entities.add(obj)
                    if len(subgraph) >= max_size:
                        break
                        
            # From first hop entity as object  
            for subj, predicate in self.kg.os_index.get(hop1_entity, []):
                # Include the triple if subject is new or is our original entity
                if subj not in visited_entities or subj == entity:
                    subgraph.append((subj, predicate, hop1_entity))
                    if subj not in visited_entities:
                        second_hop_entities.add(subj)
                        visited_entities.add(subj)
                    if len(subgraph) >= max_size:
                        break
                        
        return subgraph
        
    def extract_second_hop_only_subgraph(self, entity: str, max_size: int = 100) -> List[Triple]:
        """Extract only the second hop triples (excluding first hop)."""
        visited_entities = {entity}
        second_hop_subgraph = []
        
        # First, identify first hop entities without adding their triples
        first_hop_entities = set()
        
        # Entity as subject in first hop
        for predicate, obj in self.kg.sp_index.get(entity, []):
            if obj != entity:  # Avoid self-loops
                first_hop_entities.add(obj)
                visited_entities.add(obj)
            
        # Entity as object in first hop
        for subj, predicate in self.kg.os_index.get(entity, []):
            if subj != entity:  # Avoid self-loops
                first_hop_entities.add(subj)
                visited_entities.add(subj)
            
        # Second hop - explore from first hop entities
        for hop1_entity in first_hop_entities:
            if len(second_hop_subgraph) >= max_size:
                break
                
            # From first hop entity as subject
            for predicate, obj in self.kg.sp_index.get(hop1_entity, []):
                # Only include if object is truly new (not entity or first hop entity)
                if obj not in visited_entities:
                    second_hop_subgraph.append((hop1_entity, predicate, obj))
                    visited_entities.add(obj)
                    if len(second_hop_subgraph) >= max_size:
                        break
                        
            # From first hop entity as object  
            for subj, predicate in self.kg.os_index.get(hop1_entity, []):
                # Only include if subject is truly new (not entity or first hop entity)
                if subj not in visited_entities:
                    second_hop_subgraph.append((subj, predicate, hop1_entity))
                    visited_entities.add(subj)
                    if len(second_hop_subgraph) >= max_size:
                        break
                        
        return second_hop_subgraph
        
    def extract_description_subgraph(self, entity: str) -> List[Triple]:
        """Extract triples that contain descriptive information about the entity."""
        subgraph = []
        
        # Look for description predicates where entity is subject
        for predicate, obj in self.kg.sp_index.get(entity, []):
            if self.is_description_predicate(predicate):
                subgraph.append((entity, predicate, obj))
                
        # Look for description predicates where entity is object
        for subj, predicate in self.kg.os_index.get(entity, []):
            if self.is_description_predicate(predicate):
                subgraph.append((subj, predicate, entity))
                
        return subgraph
        
    def extract_literal_subgraph(self, entity: str) -> List[Triple]:
        """Extract triples with literal values related to the entity."""
        subgraph = []
        
        # Look for literal predicates and values where entity is subject
        for predicate, obj in self.kg.sp_index.get(entity, []):
            if self.is_literal_predicate(predicate) or self.is_literal_value(obj):
                subgraph.append((entity, predicate, obj))
                
        # Look for literal predicates where entity is object
        for subj, predicate in self.kg.os_index.get(entity, []):
            if self.is_literal_predicate(predicate) or self.is_literal_value(subj):
                subgraph.append((subj, predicate, entity))
                
        return subgraph
        
    def classify_subgraphs(self, entity: str) -> Dict[str, List[Triple]]:
        """Classify all subgraphs for a given entity."""
        results = {
            'one_hop': self.extract_one_hop_subgraph(entity),
            'two_hop': self.extract_two_hop_subgraph(entity),
            'description': self.extract_description_subgraph(entity),
            'literal': self.extract_literal_subgraph(entity)
        }
        
        return results
        
    def classify_subgraphs_detailed(self, entity: str) -> Dict[str, List[Triple]]:
        """Classify subgraphs with more detailed categorization."""
        results = {
            'one_hop': self.extract_one_hop_subgraph(entity),
            'two_hop_full': self.extract_two_hop_subgraph(entity),
            'second_hop_only': self.extract_second_hop_only_subgraph(entity),
            'description': self.extract_description_subgraph(entity),
            'literal': self.extract_literal_subgraph(entity)
        }
        
        return results
        
    def analyze_triple_patterns(self, triples: List[Triple]) -> Dict[str, int]:
        """Analyze patterns in a list of triples."""
        stats = {
            'total_triples': len(triples),
            'unique_predicates': len(set(t[1] for t in triples)),
            'unique_subjects': len(set(t[0] for t in triples)),
            'unique_objects': len(set(t[2] for t in triples)),
            'literal_objects': sum(1 for t in triples if self.is_literal_value(t[2])),
            'description_predicates': sum(1 for t in triples if self.is_description_predicate(t[1])),
            'literal_predicates': sum(1 for t in triples if self.is_literal_predicate(t[1]))
        }
        return stats
        
    def print_subgraph_analysis(self, entity: str, max_display: int = 10):
        """Print detailed analysis of subgraphs for an entity."""
        print(f"\n=== Subgraph Analysis for Entity: {entity} ===\n")
        
        classifications = self.classify_subgraphs(entity)
        
        for subgraph_type, triples in classifications.items():
            print(f"--- {subgraph_type.upper()} SUBGRAPH ---")
            stats = self.analyze_triple_patterns(triples)
            
            print("Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
                
            print(f"\nSample triples (showing first {min(max_display, len(triples))}):")
            for i, (s, p, o) in enumerate(triples[:max_display]):
                print(f"  {i+1}. {s} -> {p} -> {o}")
                
            if len(triples) > max_display:
                print(f"  ... and {len(triples) - max_display} more")
                
            print()
            
    def find_entities_by_pattern(self, pattern: str, max_results: int = 20) -> List[str]:
        """Find entities matching a pattern for analysis."""
        return self.kg.search_subject_contains(pattern, max_results)
        
    def export_classification_results(self, entity: str, output_file: str):
        """Export classification results to JSON file."""
        classifications = self.classify_subgraphs(entity)
        
        # Convert to serializable format
        export_data = {
            'entity': entity,
            'timestamp': str(Path().resolve()),
            'classifications': {}
        }
        
        for subgraph_type, triples in classifications.items():
            export_data['classifications'][subgraph_type] = {
                'triples': [{'subject': s, 'predicate': p, 'object': o} for s, p, o in triples],
                'statistics': self.analyze_triple_patterns(triples)
            }
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
            
        print(f"Classification results exported to {output_file}")

    # ---- Question centric helper (bridges retrieval + subgraph classification) ----
    def related_subgraphs_for_question(self, question: str, retriever, top_seeds: int = 1) -> Dict[str, Dict[str, List[Triple]]]:
        """Given a natural language question, use QuestionGraphRetriever to locate candidate
        seed entities and then classify their local subgraphs.

        Parameters
        ----------
        question : str
            WebQSP-style natural language question.
        retriever : QuestionGraphRetriever
            Instance of the heuristic question→KG retriever.
        top_seeds : int
            Number of top candidate entities to expand (default 1 for speed).

        Returns
        -------
        dict
            Mapping seed entity → dict of subgraph categories produced by existing
            classification methods (one_hop, two_hop, description, literal).
        """
        if QuestionGraphRetriever is None:
            raise RuntimeError("QuestionGraphRetriever not available; ensure question_retrieval.py is present.")
        result = retriever.retrieve(question)
        out: Dict[str, Dict[str, List[Triple]]] = {}
        for cand in result.get('candidates', [])[:top_seeds]:
            entity = cand['name']
            out[entity] = self.classify_subgraphs(entity)
        return out

def main():
    parser = argparse.ArgumentParser(description='Classify knowledge graph subgraphs')
    parser.add_argument('--triples', required=True, help='Path to triples TSV.gz file')
    parser.add_argument('--alias', help='Path to alias JSON file')
    parser.add_argument('--entity', help='Specific entity to analyze')
    parser.add_argument('--search', help='Search pattern to find entities')
    parser.add_argument('--limit', type=int, help='Limit number of triples loaded')
    parser.add_argument('--max-display', type=int, default=10, help='Max triples to display per category')
    parser.add_argument('--export', help='Export results to JSON file')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode for exploring entities')
    
    args = parser.parse_args()
    
    print("Loading knowledge graph...")
    kg = load_kg(args.triples, args.alias, args.limit)
    print(f"Loaded knowledge graph: {kg.summary()}")
    
    classifier = SubgraphClassifier(kg)
    
    if args.search:
        print(f"\nSearching for entities matching '{args.search}':")
        entities = classifier.find_entities_by_pattern(args.search)
        for i, entity in enumerate(entities):
            print(f"  {i+1}. {entity}")
        
        if entities and not args.entity:
            args.entity = entities[0]
            print(f"\nUsing first match: {args.entity}")
    
    if args.entity:
        classifier.print_subgraph_analysis(args.entity, args.max_display)
        
        if args.export:
            classifier.export_classification_results(args.entity, args.export)
    
    if args.interactive:
        print("\n=== Interactive Mode ===")
        print("Commands:")
        print("  analyze <entity>   - Analyze subgraphs for entity")
        print("  search <pattern>   - Search for entities")
        print("  export <entity> <file> - Export analysis to file")
        print("  quit              - Exit")
        
        while True:
            try:
                cmd = input("\n> ").strip().split()
                if not cmd:
                    continue
                    
                if cmd[0] == 'quit':
                    break
                elif cmd[0] == 'analyze' and len(cmd) > 1:
                    entity = ' '.join(cmd[1:])
                    classifier.print_subgraph_analysis(entity, args.max_display)
                elif cmd[0] == 'search' and len(cmd) > 1:
                    pattern = ' '.join(cmd[1:])
                    entities = classifier.find_entities_by_pattern(pattern)
                    for i, entity in enumerate(entities):
                        print(f"  {i+1}. {entity}")
                elif cmd[0] == 'export' and len(cmd) > 2:
                    entity = ' '.join(cmd[1:-1])
                    filename = cmd[-1]
                    classifier.export_classification_results(entity, filename)
                else:
                    print("Invalid command")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    main()
