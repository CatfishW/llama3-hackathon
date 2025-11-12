"""Knowledge graph data structure and operations."""

from __future__ import annotations
import json
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import networkx as nx
from pathlib import Path


# Global entity name mapping cache (loaded once, shared across all instances)
_GLOBAL_ENTITY_NAME_MAP: Optional[Dict[str, str]] = None
_GLOBAL_MAP_LOADED = False


def get_global_entity_name_map() -> Dict[str, str]:
    """Load and cache the global entity name mapping."""
    global _GLOBAL_ENTITY_NAME_MAP, _GLOBAL_MAP_LOADED
    
    if not _GLOBAL_MAP_LOADED:
        _GLOBAL_MAP_LOADED = True
        mapping_file = "data/webqsp/entity_name_map.json"
        mapping_path = Path(mapping_file)
        
        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    _GLOBAL_ENTITY_NAME_MAP = json.load(f)
                print(f"✓ Loaded {len(_GLOBAL_ENTITY_NAME_MAP)} entity name mappings globally")
            except Exception as e:
                print(f"Warning: Failed to load entity name mapping: {e}")
                _GLOBAL_ENTITY_NAME_MAP = {}
        else:
            _GLOBAL_ENTITY_NAME_MAP = {}
    
    return _GLOBAL_ENTITY_NAME_MAP if _GLOBAL_ENTITY_NAME_MAP is not None else {}


@dataclass
class Entity:
    """Knowledge graph entity."""
    id: str
    name: str
    type: str
    attributes: Dict[str, any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass
class Relation:
    """Knowledge graph relation (edge)."""
    head: str  # Head entity ID
    relation: str  # Relation type
    tail: str  # Tail entity ID
    weight: float = 1.0
    attributes: Dict[str, any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
    
    def as_triple(self) -> Tuple[str, str, str]:
        """Return as (head, relation, tail) triple."""
        return (self.head, self.relation, self.tail)


class KnowledgeGraph:
    """Knowledge graph with entity and relation management."""
    
    def __init__(self):
        """Initialize empty knowledge graph."""
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.graph = nx.MultiDiGraph()  # Directed multigraph
        self.entity_name_map: Dict[str, str] = {}  # kb_id -> human-readable name mapping
        
    def add_entity(self, entity: Entity):
        """Add entity to knowledge graph."""
        self.entities[entity.id] = entity
        self.graph.add_node(entity.id, name=entity.name, type=entity.type)
        
    def add_relation(self, relation: Relation):
        """Add relation to knowledge graph."""
        self.relations.append(relation)
        self.graph.add_edge(
            relation.head,
            relation.tail,
            key=relation.relation,
            relation=relation.relation,
            weight=relation.weight
        )
        
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self.entities.get(entity_id)
    
    def get_entity_by_name(self, name: str) -> List[Entity]:
        """Find entities by name (case-insensitive partial match)."""
        name_lower = name.lower()
        matches = []
        for entity in self.entities.values():
            if name_lower in entity.name.lower():
                matches.append(entity)
        return matches
    
    def get_neighbors(self, entity_id: str, direction: str = "both") -> List[str]:
        """
        Get neighboring entity IDs.
        
        Args:
            entity_id: Source entity ID
            direction: "out" (outgoing), "in" (incoming), "both"
            
        Returns:
            List of neighbor entity IDs
        """
        if entity_id not in self.graph:
            return []
            
        neighbors = set()
        if direction in ["out", "both"]:
            neighbors.update(self.graph.successors(entity_id))
        if direction in ["in", "both"]:
            neighbors.update(self.graph.predecessors(entity_id))
        return list(neighbors)
    
    def get_relations_between(self, head_id: str, tail_id: str) -> List[str]:
        """Get all relation types between two entities."""
        if not self.graph.has_edge(head_id, tail_id):
            return []
        edges = self.graph[head_id][tail_id]
        return [edges[key]["relation"] for key in edges]
    
    def get_k_hop_subgraph(
        self, 
        seed_entities: List[str], 
        k: int = 2,
        max_nodes: int = 50
    ) -> KnowledgeGraph:
        """
        Extract k-hop subgraph around seed entities.
        
        Args:
            seed_entities: Starting entity IDs
            k: Number of hops
            max_nodes: Maximum nodes in subgraph
            
        Returns:
            Subgraph as new KnowledgeGraph
        """
        subgraph_nodes = set(seed_entities)
        frontier = set(seed_entities)
        
        # BFS expansion
        for hop in range(k):
            if len(subgraph_nodes) >= max_nodes:
                break
            next_frontier = set()
            for node in frontier:
                neighbors = self.get_neighbors(node)
                for neighbor in neighbors:
                    if neighbor not in subgraph_nodes:
                        next_frontier.add(neighbor)
                        if len(subgraph_nodes) + len(next_frontier) >= max_nodes:
                            break
                if len(subgraph_nodes) + len(next_frontier) >= max_nodes:
                    break
            subgraph_nodes.update(next_frontier)
            frontier = next_frontier
        
        # Create subgraph
        subgraph = KnowledgeGraph()
        for node_id in subgraph_nodes:
            if node_id in self.entities:
                subgraph.add_entity(self.entities[node_id])
        
        for relation in self.relations:
            if relation.head in subgraph_nodes and relation.tail in subgraph_nodes:
                subgraph.add_relation(relation)
        
        return subgraph
    
    def find_paths(
        self,
        source: str,
        target: str,
        max_length: int = 5,
        max_paths: int = 10
    ) -> List[List[Tuple[str, str, str]]]:
        """
        Find reasoning paths between entities.
        
        Args:
            source: Source entity ID
            target: Target entity ID
            max_length: Maximum path length
            max_paths: Maximum number of paths to return
            
        Returns:
            List of paths, each path is list of (head, relation, tail) triples
        """
        if source not in self.graph or target not in self.graph:
            return []
        
        try:
            # Find all simple paths
            all_paths = nx.all_simple_paths(
                self.graph,
                source,
                target,
                cutoff=max_length
            )
            
            result_paths = []
            for path_nodes in list(all_paths)[:max_paths]:
                # Convert node path to triple path
                path_triples = []
                for i in range(len(path_nodes) - 1):
                    head = path_nodes[i]
                    tail = path_nodes[i + 1]
                    relations = self.get_relations_between(head, tail)
                    if relations:
                        path_triples.append((head, relations[0], tail))
                if path_triples:
                    result_paths.append(path_triples)
                    
            return result_paths
            
        except nx.NetworkXNoPath:
            return []
    
    def load_entity_name_map(self, mapping_file: str = "data/webqsp/entity_name_map.json"):
        """
        Load entity name mapping from JSON file.
        Uses global cache if loading from default location.
        
        Args:
            mapping_file: Path to entity name mapping JSON file
        """
        # Use global cache for default file
        if mapping_file == "data/webqsp/entity_name_map.json":
            self.entity_name_map = get_global_entity_name_map()
        else:
            # Load custom mapping file
            try:
                mapping_path = Path(mapping_file)
                if mapping_path.exists():
                    with open(mapping_path, 'r', encoding='utf-8') as f:
                        self.entity_name_map = json.load(f)
                    print(f"✓ Loaded {len(self.entity_name_map)} entity name mappings from {mapping_file}")
                else:
                    print(f"Warning: Entity name mapping file not found: {mapping_file}")
            except Exception as e:
                print(f"Error loading entity name mapping: {e}")
                self.entity_name_map = {}
    
    def to_text(self) -> str:
        """Convert knowledge graph to readable text format with entity name mapping.
        
        Automatically uses the global entity name map (loaded once, shared across all instances).
        Uses entity_name_map (kb_id -> text) if available for human-readable names.
        Falls back to entity.name for entities not in the mapping.
        """
        lines = []
        
        # Use global entity name mapping (loaded once for all instances)
        self.entity_name_map = get_global_entity_name_map()
        
        entity_name_map = self.entity_name_map
        
        def get_entity_display_name(entity_id: str) -> str:
            """Get display name for entity, using mapping if available."""
            if entity_id in entity_name_map:
                return entity_name_map[entity_id]
            entity = self.entities.get(entity_id)
            return entity.name if entity else entity_id
        
        lines.append("Entities:")
        for entity in self.entities.values():
            display_name = get_entity_display_name(entity.id)
            # Show mapped name if different from entity.name
            if entity.id in entity_name_map and display_name != entity.name:
                lines.append(f"  - {display_name} [kb_id: {entity.id}] ({entity.type})")
            else:
                lines.append(f"  - {entity.name} ({entity.type})")
        
        lines.append("\nRelations:")
        for relation in self.relations:
            head_name = get_entity_display_name(relation.head)
            tail_name = get_entity_display_name(relation.tail)
            lines.append(f"  - {head_name} --[{relation.relation}]--> {tail_name}")
        
        return "\n".join(lines)
    
    def load_from_dict(self, data: Dict):
        """Load knowledge graph from dictionary."""
        # Load entities
        for ent_data in data.get("entities", []):
            entity = Entity(
                id=ent_data["id"],
                name=ent_data["name"],
                type=ent_data.get("type", "Entity"),
                attributes=ent_data.get("attributes", {})
            )
            self.add_entity(entity)
        
        # Load relations
        for rel_data in data.get("relations", []):
            relation = Relation(
                head=rel_data["head"],
                relation=rel_data["relation"],
                tail=rel_data["tail"],
                weight=rel_data.get("weight", 1.0),
                attributes=rel_data.get("attributes", {})
            )
            self.add_relation(relation)
    
    def load_from_json(self, filepath: str):
        """Load knowledge graph from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.load_from_dict(data)
    
    def to_dict(self) -> Dict:
        """Export knowledge graph to dictionary."""
        return {
            "entities": [
                {
                    "id": e.id,
                    "name": e.name,
                    "type": e.type,
                    "attributes": e.attributes
                }
                for e in self.entities.values()
            ],
            "relations": [
                {
                    "head": r.head,
                    "relation": r.relation,
                    "tail": r.tail,
                    "weight": r.weight,
                    "attributes": r.attributes
                }
                for r in self.relations
            ]
        }
    
    def save_to_json(self, filepath: str):
        """Save knowledge graph to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def __len__(self) -> int:
        """Return number of entities."""
        return len(self.entities)
    
    def stats(self) -> Dict[str, int]:
        """Return graph statistics."""
        return {
            "num_entities": len(self.entities),
            "num_relations": len(self.relations),
            "num_entity_types": len(set(e.type for e in self.entities.values())),
            "num_relation_types": len(set(r.relation for r in self.relations)),
        }
