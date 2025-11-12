"""Evidence path finder module for EPERM system."""

from __future__ import annotations
from typing import List, Dict, Tuple
from dataclasses import dataclass
import json
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


class EvidencePathFinder:
    """Finds and scores evidence reasoning paths in subgraph."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize evidence path finder.
        
        Args:
            llm_client: LLM client for path reasoning
        """
        self.llm = llm_client
        self.max_paths = PATH_FINDER_CONFIG["max_paths"]
        self.max_path_length = PATH_FINDER_CONFIG["max_path_length"]
        self.score_weights = PATH_FINDER_CONFIG["score_weights"]
        
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
        if SYSTEM_CONFIG["verbose"]:
            print(f"\n[Evidence Path Finder] Finding paths for question")
        
        if len(subgraph) == 0:
            return []
        
        # Step 1: Identify potential answer entities
        answer_candidates = self._identify_answer_candidates(question, subgraph)
        
        if not answer_candidates:
            if SYSTEM_CONFIG["verbose"]:
                print("  No answer candidates identified")
            return []
        
        if SYSTEM_CONFIG["verbose"]:
            print(f"  Answer candidates: {[c['entity'].name for c in answer_candidates[:3]]}")
        
        # Step 2: Find paths to answer candidates
        all_paths = self._find_paths_to_candidates(question, subgraph, answer_candidates)
        
        if not all_paths:
            if SYSTEM_CONFIG["verbose"]:
                print("  No valid paths found")
            return []
        
        # Step 3: Score and rank paths
        scored_paths = self._score_paths(question, all_paths, subgraph)
        
        # Return top-k paths
        top_paths = sorted(scored_paths, key=lambda p: p.score, reverse=True)[:self.max_paths]
        
        if SYSTEM_CONFIG["verbose"]:
            print(f"  Found {len(top_paths)} evidence paths")
            for i, path in enumerate(top_paths[:3], 1):
                print(f"    Path {i} (score={path.score:.3f}): {path.to_text(subgraph)}")
        
        return top_paths
    
    def _identify_answer_candidates(
        self,
        question: str,
        subgraph: KnowledgeGraph
    ) -> List[Dict]:
        """
        Use LLM to identify potential answer entities in subgraph.
        
        Args:
            question: Question text
            subgraph: Subgraph to search
            
        Returns:
            List of candidate dictionaries with 'entity' and 'relevance'
        """
        # Prepare subgraph context
        subgraph_text = subgraph.to_text()
        
        system_prompt = """You are a knowledge graph reasoning assistant. Given a question and a knowledge graph subgraph, identify which entities are most likely to be the answer.

Return a JSON list of entity names with relevance scores (0-1).

Example:
Question: "Who founded Microsoft?"
Entities: ["Microsoft", "Bill Gates", "Windows", "Seattle"]
Answer: [{"entity": "Bill Gates", "relevance": 0.95}, {"entity": "Microsoft", "relevance": 0.3}]"""
        
        user_prompt = f"""Question: "{question}"

Knowledge Graph:
{subgraph_text}

Identify potential answer entities (return JSON list):"""
        
        try:
            response = self.llm.generate_with_prompt(
                system_prompt,
                user_prompt,
                temperature=0.3
            )
            
            # Parse JSON response
            # Extract JSON from response (handle markdown code blocks)
            json_text = response.strip()
            if json_text.startswith("```"):
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1])
            
            candidates_data = json.loads(json_text)
            
            # Match to actual entities
            candidates = []
            for item in candidates_data:
                entity_name = item["entity"]
                relevance = item.get("relevance", 0.5)
                
                matching_entities = subgraph.get_entity_by_name(entity_name)
                if matching_entities:
                    candidates.append({
                        "entity": matching_entities[0],
                        "relevance": relevance
                    })
            
            return sorted(candidates, key=lambda c: c["relevance"], reverse=True)
            
        except Exception as e:
            if SYSTEM_CONFIG["verbose"]:
                print(f"  Error identifying candidates with LLM: {e}")
            # Fallback: return all entities with neutral score
            return [
                {"entity": entity, "relevance": 0.5}
                for entity in subgraph.entities.values()
            ]
    
    def _find_paths_to_candidates(
        self,
        question: str,
        subgraph: KnowledgeGraph,
        candidates: List[Dict]
    ) -> List[List[Tuple[str, str, str]]]:
        """
        Find reasoning paths to answer candidates.
        
        Args:
            question: Question text
            subgraph: Subgraph
            candidates: Answer candidates
            
        Returns:
            List of paths (each path is list of triples)
        """
        all_paths = []
        
        # Get seed entities from question
        # For simplicity, use all entities mentioned in candidates as potential sources
        target_entity_ids = [c["entity"].id for c in candidates[:5]]  # Top 5 candidates
        
        # Find paths between entities in subgraph
        for target_id in target_entity_ids:
            # Find paths from other entities to this target
            for source_id in subgraph.entities.keys():
                if source_id == target_id:
                    continue
                
                paths = subgraph.find_paths(
                    source_id,
                    target_id,
                    max_length=self.max_path_length,
                    max_paths=3  # Max 3 paths per source-target pair
                )
                all_paths.extend(paths)
        
        return all_paths[:50]  # Limit total paths for efficiency
    
    def _score_paths(
        self,
        question: str,
        paths: List[List[Tuple[str, str, str]]],
        subgraph: KnowledgeGraph
    ) -> List[EvidencePath]:
        """
        Score reasoning paths using LLM.
        
        Args:
            question: Question text
            paths: List of paths to score
            subgraph: Subgraph context
            
        Returns:
            List of EvidencePath objects with scores
        """
        scored_paths = []
        
        for path in paths:
            # Convert path to text
            path_text = self._path_to_text(path, subgraph)
            
            # Get LLM scoring and reasoning
            score, reasoning = self._score_single_path(question, path_text)
            
            evidence_path = EvidencePath(
                path=path,
                score=score,
                reasoning=reasoning
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
            parts.append(f"{head_name} --[{relation}]--> {tail_name}")
        return " → ".join(parts)
    
    def _score_single_path(self, question: str, path_text: str) -> Tuple[float, str]:
        """
        Score a single reasoning path.
        
        Args:
            question: Question text
            path_text: Path in text format
            
        Returns:
            Tuple of (score, reasoning)
        """
        system_prompt = """You are a reasoning path evaluator. Given a question and a reasoning path from a knowledge graph, evaluate how well this path supports answering the question.

Return JSON with:
- "score": float between 0 and 1 (how relevant/useful is this path?)
- "reasoning": brief explanation

Example:
Question: "Who founded Microsoft?"
Path: "Bill Gates --[founded]--> Microsoft"
Answer: {"score": 0.95, "reasoning": "Direct evidence that Bill Gates founded Microsoft"}"""
        
        user_prompt = f"""Question: "{question}"
Reasoning Path: {path_text}

Evaluate this path (return JSON):"""
        
        try:
            response = self.llm.generate_with_prompt(
                system_prompt,
                user_prompt,
                temperature=0.2
            )
            
            # Parse JSON
            json_text = response.strip()
            if json_text.startswith("```"):
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1])
            
            result = json.loads(json_text)
            score = float(result.get("score", 0.5))
            reasoning = result.get("reasoning", "")
            
            return score, reasoning
            
        except Exception as e:
            if SYSTEM_CONFIG["verbose"]:
                print(f"  Error scoring path: {e}")
            return 0.5, "Unable to score path"
