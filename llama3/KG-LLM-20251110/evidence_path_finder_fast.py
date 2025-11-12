"""Fast evidence path finder with minimal LLM calls.

Optimizations:
1. Heuristic-based candidate identification (no LLM)
2. Batch LLM scoring of paths
3. Simpler path scoring with cutoffs
4. Early termination
"""

from __future__ import annotations
from typing import List, Dict, Tuple
from dataclasses import dataclass
from knowledge_graph import KnowledgeGraph
from llm_client import LLMClient
from config import PATH_FINDER_CONFIG, SYSTEM_CONFIG


@dataclass
class EvidencePath:
    """Represents a reasoning path with score."""
    path: List[Tuple[str, str, str]]  # List of (head, relation, tail) triples
    score: float
    reasoning: str  # Explanation from LLM
    
    def _get_entity_name(self, entity_id: str, kg: KnowledgeGraph) -> str:
        """
        Get readable entity name from entity ID.
        Maps entity IDs to their human-readable names, with fallback to ID if not found.
        
        Priority:
        1. Check entity_name_map in KG (from answer data in WebQSP)
        2. Look up entity.name in KG
        3. Fall back to entity ID
        """
        if not entity_id:
            return "Unknown"
        
        # Look up entity directly
        entity = kg.get_entity(entity_id)
        if entity and entity.name:
            return entity.name
        
        # Fall back to entity ID
        return entity_id
    
    def _get_relation_name(self, relation_path: str) -> str:
        """
        Convert full relation path to readable name.
        E.g., 'location.location.containedby' -> 'containedby'
        """
        if not relation_path:
            return "unknown_relation"
        
        # Get the last part of the relation path (most specific)
        parts = relation_path.split('.')
        return parts[-1] if parts else relation_path
    
    def to_text(self, kg: KnowledgeGraph) -> str:
        """
        Convert path to readable text with proper entity name and relation name mapping.
        
        Example output:
        Jamaica --[containedby]--> Caribbean Region → Caribbean Region --[languages_spoken]--> English
        """
        parts = []
        for head_id, relation, tail_id in self.path:
            # Map entity IDs to human-readable names
            head_name = self._get_entity_name(head_id, kg)
            tail_name = self._get_entity_name(tail_id, kg)
            
            # Convert relation path to readable name
            rel_name = self._get_relation_name(relation)
            
            parts.append(f"{head_name} --[{rel_name}]--> {tail_name}")
        
        return " → ".join(parts)


class FastEvidencePathFinder:
    """Fast evidence path finder with minimal LLM calls."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize fast evidence path finder.
        
        Args:
            llm_client: LLM client for path reasoning
        """
        self.llm = llm_client
        self.max_paths = PATH_FINDER_CONFIG["max_paths"]
        self.max_path_length = min(PATH_FINDER_CONFIG["max_path_length"], 3)  # Shorter paths
        
    def find_evidence_paths(
        self,
        question: str,
        subgraph: KnowledgeGraph
    ) -> List[EvidencePath]:
        """
        Find and score evidence paths for answering the question.
        
        Args:
            question: Question text
            subgraph: Retrieved subgraph
            
        Returns:
            List of evidence paths with scores
        """
        if len(subgraph) == 0:
            return []
        
        # Step 1: Identify answer candidates using heuristics (no LLM)
        answer_candidates = self._identify_answer_candidates_fast(question, subgraph)
        
        if not answer_candidates:
            return []
        
        # Step 2: Find paths to candidates
        all_paths = self._find_paths_to_candidates_fast(subgraph, answer_candidates)
        
        if not all_paths:
            return []
        
        # Step 3: Score paths with single batched LLM call
        scored_paths = self._score_paths_batch(question, all_paths, subgraph)
        
        # Return top-k paths
        top_paths = sorted(scored_paths, key=lambda p: p.score, reverse=True)[:self.max_paths]
        
        return top_paths
    
    def _identify_answer_candidates_fast(
        self,
        question: str,
        subgraph: KnowledgeGraph
    ) -> List[str]:
        """
        Identify answer candidates using heuristics (no LLM).
        
        Strategy:
        1. Entities with many incoming edges (popular)
        2. Entities with relevant names (keyword matching)
        3. Entities at path endpoints
        
        Args:
            question: Question text
            subgraph: Subgraph to search
            
        Returns:
            List of candidate entity IDs
        """
        # Count incoming/outgoing edges
        in_degree = {}
        out_degree = {}
        for rel in subgraph.relations:
            out_degree[rel.head] = out_degree.get(rel.head, 0) + 1
            in_degree[rel.tail] = in_degree.get(rel.tail, 0) + 1
        
        # Score entities by degree and name matching
        candidates = []
        question_lower = question.lower()
        
        for entity_id, entity in subgraph.entities.items():
            score = 0.0
            
            # High in-degree suggests answer candidate
            score += in_degree.get(entity_id, 0) * 0.3
            
            # Some out-degree is good (connected)
            score += min(out_degree.get(entity_id, 0), 5) * 0.1
            
            # Name appears in question? Less likely to be answer
            entity_name_lower = entity.name.lower()
            if entity_name_lower in question_lower:
                score -= 5.0
            
            candidates.append((entity_id, score))
        
        # Return top candidates
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [entity_id for entity_id, score in candidates[:20]]  # Top 20
    
    def _find_paths_to_candidates_fast(
        self,
        subgraph: KnowledgeGraph,
        candidate_ids: List[str]
    ) -> List[List[Tuple[str, str, str]]]:
        """
        Find reasoning paths to answer candidates (fast heuristic).
        
        Args:
            subgraph: Subgraph
            candidate_ids: Answer candidate entity IDs
            
        Returns:
            List of paths (each path is list of triples)
        """
        all_paths = []
        
        # For each candidate, find paths from other entities
        for target_id in candidate_ids[:10]:  # Limit candidates
            # Find paths from entities mentioned in question or with high out-degree
            source_candidates = []
            for entity_id in subgraph.entities.keys():
                if entity_id != target_id:
                    source_candidates.append(entity_id)
            
            # Limit sources
            for source_id in source_candidates[:5]:
                paths = subgraph.find_paths(
                    source_id,
                    target_id,
                    max_length=self.max_path_length,
                    max_paths=2  # Only 2 paths per source-target
                )
                all_paths.extend(paths)
                
                # Early termination if we have enough
                if len(all_paths) >= 30:
                    return all_paths[:30]
        
        return all_paths[:30]  # Limit total paths
    
    def _score_paths_batch(
        self,
        question: str,
        paths: List[List[Tuple[str, str, str]]],
        subgraph: KnowledgeGraph
    ) -> List[EvidencePath]:
        """
        Score multiple paths with a single LLM call.
        
        Args:
            question: Question text
            paths: List of paths to score
            subgraph: Subgraph context
            
        Returns:
            List of EvidencePath objects with scores
        """
        if not paths:
            return []
        
        # Limit paths for efficient scoring
        paths = paths[:15]  # Top 15 paths only
        
        # Format all paths for batch scoring
        paths_text = []
        for i, path in enumerate(paths):
            path_str = self._path_to_text(path, subgraph)
            paths_text.append(f"{i+1}. {path_str}")
        
        all_paths_str = "\n".join(paths_text)
        
        # Single LLM call to score all paths
        system_prompt = """You are a reasoning path evaluator. Given a question and multiple reasoning paths from a knowledge graph, score each path (0-1) based on relevance.

Return JSON array with scores and brief reasoning for each path.

Example:
[
  {"path_id": 1, "score": 0.95, "reasoning": "Direct answer"},
  {"path_id": 2, "score": 0.3, "reasoning": "Weakly related"}
]"""
        
        user_prompt = f"""Question: "{question}"

Reasoning Paths:
{all_paths_str}

Score each path (return JSON array):"""
        
        try:
            response = self.llm.generate_with_prompt(
                system_prompt,
                user_prompt,
                temperature=0.2
            )
            
            # Parse JSON
            import json
            json_text = response.strip()
            if json_text.startswith("```"):
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1])
            
            scores_data = json.loads(json_text)
            
            # Create EvidencePath objects
            scored_paths = []
            for item in scores_data:
                path_id = item.get("path_id", 1) - 1  # Convert to 0-indexed
                if 0 <= path_id < len(paths):
                    score = float(item.get("score", 0.5))
                    reasoning = item.get("reasoning", "")
                    
                    evidence_path = EvidencePath(
                        path=paths[path_id],
                        score=score,
                        reasoning=reasoning
                    )
                    scored_paths.append(evidence_path)
            
            return scored_paths
            
        except Exception as e:
            if SYSTEM_CONFIG["verbose"]:
                print(f"  Error in batch scoring: {e}")
            
            # Fallback: score with heuristics
            return self._score_paths_heuristic(paths, subgraph)
    
    def _score_paths_heuristic(
        self,
        paths: List[List[Tuple[str, str, str]]],
        subgraph: KnowledgeGraph
    ) -> List[EvidencePath]:
        """Fallback heuristic scoring without LLM."""
        scored_paths = []
        
        for path in paths:
            # Simple heuristic: shorter paths are better
            score = 1.0 / (len(path) + 1)
            
            evidence_path = EvidencePath(
                path=path,
                score=score,
                reasoning="Heuristic score"
            )
            scored_paths.append(evidence_path)
        
        return scored_paths
    
    def _path_to_text(
        self,
        path: List[Tuple[str, str, str]],
        kg: KnowledgeGraph
    ) -> str:
        """Convert path to readable text."""
        parts = []
        for head_id, relation, tail_id in path:
            head_name = kg.get_entity(head_id).name if kg.get_entity(head_id) else head_id
            tail_name = kg.get_entity(tail_id).name if kg.get_entity(tail_id) else tail_id
            # Simplify relation name
            rel_simple = relation.split('.')[-1] if '.' in relation else relation
            parts.append(f"{head_name} -[{rel_simple}]-> {tail_name}")
        return " → ".join(parts)
