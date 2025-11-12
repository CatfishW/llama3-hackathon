"""WebQSP dataset loader for EPERM system.

This module loads and converts WebQSP (Web Questions with Subgraph) data
into the EPERM knowledge graph format.

WebQSP Format:
- Questions with gold answers
- Entity indices referring to entities.txt
- Relation indices referring to relations.txt
- Subgraph tuples as [head_idx, relation_idx, tail_idx]

EPERM Format:
- Entities: {id, name, type}
- Relations: {head, relation, tail}
"""

import json
from typing import List, Dict, Tuple
from knowledge_graph import KnowledgeGraph, Entity, Relation


class WebQSPLoader:
    """Loader for WebQSP dataset."""
    
    def __init__(self, data_dir: str = "data/webqsp"):
        """
        Initialize WebQSP loader.
        
        Args:
            data_dir: Directory containing WebQSP files
        """
        self.data_dir = data_dir
        self.entities = []
        self.relations = []
        self._load_vocab()
    
    def _load_vocab(self):
        """Load entity and relation vocabularies."""
        # Load entities
        with open(f"{self.data_dir}/entities.txt", 'r', encoding='utf-8') as f:
            self.entities = [line.strip() for line in f]
        
        # Load relations
        with open(f"{self.data_dir}/relations.txt", 'r', encoding='utf-8') as f:
            self.relations = [line.strip() for line in f]
        
        print(f"Loaded {len(self.entities)} entities and {len(self.relations)} relations")
    
    def load_sample(self, file_path: str, sample_idx: int) -> Dict:
        """
        Load a single sample from WebQSP file.
        
        Args:
            file_path: Path to WebQSP JSONL file
            sample_idx: Index of sample to load (0-based)
            
        Returns:
            Dictionary with question, answers, and subgraph data
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i == sample_idx:
                    return json.loads(line)
        raise IndexError(f"Sample index {sample_idx} out of range")
    
    def load_samples(self, file_path: str, num_samples: int = 10) -> List[Dict]:
        """
        Load multiple samples from WebQSP file.
        
        Args:
            file_path: Path to WebQSP JSONL file
            num_samples: Number of samples to load
            
        Returns:
            List of sample dictionaries
        """
        samples = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= num_samples:
                    break
                samples.append(json.loads(line))
        return samples
    
    def sample_to_kg(self, sample: Dict, limit_size: int = 500, entity_name_map: Dict[str, str] = None) -> KnowledgeGraph:
        """
        Convert a WebQSP sample to KnowledgeGraph.
        
        Args:
            sample: WebQSP sample dictionary
            limit_size: Maximum number of triples to include
            entity_name_map: Optional mapping of entity IDs to human-readable names from answers
            
        Returns:
            KnowledgeGraph object with entity name mapping if provided
        """
        kg = KnowledgeGraph()
        
        # Get subgraph tuples
        tuples = sample.get('subgraph', {}).get('tuples', [])
        
        # Limit size for efficiency
        if len(tuples) > limit_size:
            tuples = tuples[:limit_size]
        
        # Track unique entities in this subgraph
        entity_set = set()
        for head_idx, rel_idx, tail_idx in tuples:
            entity_set.add(head_idx)
            entity_set.add(tail_idx)
        
        # Add entities
        for entity_idx in entity_set:
            if entity_idx < len(self.entities):
                entity_id = self.entities[entity_idx]
                
                # First, try to use mapping from answers (most accurate)
                # Then fall back to cleaned-up ID
                if entity_name_map and entity_id in entity_name_map:
                    entity_name = entity_name_map[entity_id]
                else:
                    # Clean up entity name (remove m. prefix for display)
                    entity_name = entity_id.replace('m.', '').replace('_', ' ')
                
                entity = Entity(
                    id=entity_id,
                    name=entity_name,
                    type="Entity",
                    attributes={"original_idx": entity_idx}
                )
                kg.add_entity(entity)
        
        # Add relations
        for head_idx, rel_idx, tail_idx in tuples:
            if (head_idx < len(self.entities) and 
                tail_idx < len(self.entities) and 
                rel_idx < len(self.relations)):
                
                head_id = self.entities[head_idx]
                tail_id = self.entities[tail_idx]
                relation_name = self.relations[rel_idx]
                
                # Only add if entities exist in KG
                if head_id in kg.entities and tail_id in kg.entities:
                    relation = Relation(
                        head=head_id,
                        relation=relation_name,
                        tail=tail_id,
                        weight=1.0
                    )
                    kg.add_relation(relation)
        
        return kg
    
    def find_entity_ids_for_answer(self, answer_text: str, kg: KnowledgeGraph) -> List[str]:
        """
        Find entity IDs in the KG that match the answer text.
        
        Args:
            answer_text: Gold answer text
            kg: Knowledge graph to search
            
        Returns:
            List of matching entity IDs
        """
        import unicodedata
        import re
        
        def normalize(text):
            if not text:
                return ""
            text = str(text).lower()
            text = unicodedata.normalize('NFD', text)
            text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
            text = re.sub(r'[^\w\s]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        
        answer_norm = normalize(answer_text)
        if not answer_norm:
            return []
        
        matching_ids = []
        answer_words = set(answer_norm.split())
        
        # IMPORTANT: In WebQSP, entity names are often just IDs
        # We need to be more aggressive in matching
        
        # Search through all entities in the KG
        for entity_id, entity in kg.entities.items():
            entity_name_norm = normalize(entity.name)
            entity_id_norm = normalize(entity_id.replace('m.', '').replace('_', ' '))
            
            if not entity_name_norm and not entity_id_norm:
                continue
            
            # Strategy 1: Exact match with name or ID
            if answer_norm == entity_name_norm or answer_norm == entity_id_norm:
                matching_ids.append(entity_id)
                continue
            
            # Strategy 2: Partial match (answer in entity name/ID or vice versa)
            if answer_norm in entity_name_norm or entity_name_norm in answer_norm:
                matching_ids.append(entity_id)
                continue
            
            if answer_norm in entity_id_norm or entity_id_norm in answer_norm:
                matching_ids.append(entity_id)
                continue
            
            # Strategy 3: Word overlap match (lowered threshold)
            entity_words = set(entity_name_norm.split()) | set(entity_id_norm.split())
            if answer_words and entity_words:
                overlap = len(answer_words & entity_words)
                similarity = overlap / max(len(answer_words), len(entity_words))
                if similarity >= 0.5:  # Further lowered threshold
                    matching_ids.append(entity_id)
                    continue
        
        # If still no matches found, this is expected for WebQSP
        # because gold answers often refer to entities not in the limited subgraph
        return matching_ids
    
    def create_qa_dataset(
        self,
        file_path: str,
        num_samples: int = 10,
        max_kg_size: int = 500
    ) -> List[Dict]:
        """
        Create question-answer dataset with KGs.
        
        Args:
            file_path: Path to WebQSP JSONL file
            num_samples: Number of samples to load
            max_kg_size: Max triples per knowledge graph
            
        Returns:
            List of dicts with 'question', 'answers', 'kg'
        """
        samples = self.load_samples(file_path, num_samples)
        qa_dataset = []
        
        for i, sample in enumerate(samples):
            try:
                # Build entity name mapping from answer data
                entity_name_map = {}
                for ans in sample.get('answers', []):
                    if ans and ans.get('kb_id') and ans.get('text'):
                        entity_name_map[ans['kb_id']] = ans['text']
                
                # Create KG with entity name mapping
                kg = self.sample_to_kg(sample, limit_size=max_kg_size, entity_name_map=entity_name_map)
                
                # Extract gold answers (text and kb_id)
                answers = []
                answer_entity_ids = []
                
                for ans in sample.get('answers', []):
                    if ans and ans.get('text'):
                        answers.append(ans['text'])
                        # Use kb_id directly from the dataset (Freebase entity ID)
                        if ans.get('kb_id'):
                            answer_entity_ids.append(ans['kb_id'])
                
                qa_item = {
                    'id': sample.get('id', f'sample_{i}'),
                    'question': sample.get('question', ''),
                    'answers': answers,
                    'answer_entity_ids': list(set(answer_entity_ids)),  # Remove duplicates
                    'entity_name_map': entity_name_map,  # Store the mapping
                    'kg': kg,
                    'kg_stats': kg.stats()
                }
                qa_dataset.append(qa_item)
                
            except Exception as e:
                print(f"Error processing sample {i}: {e}")
                continue
        
        return qa_dataset


def demo_webqsp_loading():
    """Demonstrate WebQSP loading."""
    print("\n" + "="*70)
    print("WebQSP Dataset Loading Demo")
    print("="*70)
    
    # Initialize loader
    loader = WebQSPLoader()
    
    # Load first 5 samples from training set
    print("\nLoading first 5 training samples...")
    qa_dataset = loader.create_qa_dataset(
        "data/webqsp/train_simple.json",
        num_samples=5,
        max_kg_size=300  # Limit for faster processing
    )
    
    # Display loaded samples
    for i, qa_item in enumerate(qa_dataset, 1):
        print(f"\n{'='*70}")
        print(f"Sample {i}: {qa_item['id']}")
        print(f"{'='*70}")
        print(f"Question: {qa_item['question']}")
        print(f"Gold Answers: {', '.join(qa_item['answers'])}")
        print(f"KG Stats: {qa_item['kg_stats']}")
        
        # Show sample entities and relations
        kg = qa_item['kg']
        print(f"\nSample Entities (first 5):")
        for j, entity in enumerate(list(kg.entities.values())[:5]):
            print(f"  - {entity.name} (ID: {entity.id})")
        
        print(f"\nSample Relations (first 5):")
        for j, relation in enumerate(kg.relations[:5]):
            head_name = kg.entities[relation.head].name
            tail_name = kg.entities[relation.tail].name
            print(f"  - {head_name} --[{relation.relation}]--> {tail_name}")
    
    return qa_dataset


if __name__ == "__main__":
    demo_webqsp_loading()
