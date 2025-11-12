"""Fast answer predictor with minimal LLM overhead.

Optimizations:
1. Direct answer extraction from paths
2. Simpler prompts
3. Fallback to heuristics
"""

from __future__ import annotations
from typing import List, Dict
from dataclasses import dataclass
from knowledge_graph import KnowledgeGraph
from evidence_path_finder_fast import EvidencePath
from llm_client import LLMClient
from config import PREDICTOR_CONFIG, SYSTEM_CONFIG


@dataclass
class Answer:
    """Final answer with confidence and supporting evidence."""
    answer: str
    confidence: float
    supporting_paths: List[EvidencePath]
    reasoning: str


class FastAnswerPredictor:
    """Fast answer predictor with optimized LLM usage."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize fast answer predictor.
        
        Args:
            llm_client: LLM client for answer generation
        """
        self.llm = llm_client
        self.top_k_paths = min(PREDICTOR_CONFIG["top_k_paths"], 5)  # Use fewer paths
        
    def predict(
        self,
        question: str,
        evidence_paths: List[EvidencePath],
        subgraph: KnowledgeGraph
    ) -> Answer:
        """
        Predict final answer using evidence paths.
        
        Args:
            question: Question text
            evidence_paths: List of evidence paths (can be empty)
            subgraph: Original subgraph for context
            
        Returns:
            Answer object with result and metadata
        """
        # If no evidence paths, try LLM prediction directly from KG
        if not evidence_paths:
            answer_text, confidence, reasoning = self._generate_answer_from_kg(
                question,
                subgraph
            )
            return Answer(
                answer=answer_text,
                confidence=confidence,
                supporting_paths=[],
                reasoning=reasoning
            )
        
        # Select top-k evidence paths
        top_paths = sorted(evidence_paths, key=lambda p: p.score, reverse=True)[:self.top_k_paths]
        
        # Try heuristic extraction first (fast)
        # heuristic_answer = self._extract_answer_heuristic(top_paths, subgraph)
        # if heuristic_answer:
        #     answer_text, confidence = heuristic_answer
        #     return Answer(
        #         answer=answer_text,
        #         confidence=confidence,
        #         supporting_paths=top_paths,
        #         reasoning="Extracted from top evidence path"
        #     )
        
        # Fallback to LLM generation (slower but more accurate)
        answer_text, confidence, reasoning = self._generate_answer_llm(
            question,
            top_paths,
            subgraph
        )
        
        answer = Answer(
            answer=answer_text,
            confidence=confidence,
            supporting_paths=top_paths,
            reasoning=reasoning
        )
        
        return answer
    
    def _extract_answer_heuristic(
        self,
        evidence_paths: List[EvidencePath],
        subgraph: KnowledgeGraph
    ) -> tuple[str, float] | None:
        """
        Extract answer using heuristics (no LLM).
        
        Strategy: Take the tail entity of the highest-scoring path
        Returns entity ID for proper matching with gold answers
        
        Args:
            evidence_paths: Evidence paths
            subgraph: Subgraph for entity info
            
        Returns:
            Tuple of (answer_entity_id, confidence) or None
        """
        if not evidence_paths:
            return None
        
        # Get highest scoring path
        best_path = evidence_paths[0]
        
        if not best_path.path:
            return None
        
        # Extract answer from path tail (return entity ID, not name)
        last_triple = best_path.path[-1]
        tail_entity_id = last_triple[2]  # (head, relation, tail)
        
        if tail_entity_id in subgraph.entities:
            # Return entity ID for proper comparison
            answer = tail_entity_id
            # Confidence based on path score
            confidence = min(best_path.score, 0.9)  # Cap at 0.9 for heuristic
            return (answer, confidence)
        
        return None
    
    def _generate_answer_llm(
        self,
        question: str,
        evidence_paths: List[EvidencePath],
        subgraph: KnowledgeGraph
    ) -> tuple[str, float, str]:
        """
        Generate answer using LLM (optimized prompt).
        
        Args:
            question: Question text
            evidence_paths: Top evidence paths
            subgraph: Subgraph context
            
        Returns:
            Tuple of (answer_text, confidence, reasoning)
        """
        # Format evidence concisely
        evidence_text = self._format_evidence_concise(evidence_paths, subgraph)
        
        # Collect candidate entity IDs from paths
        candidate_entities = set()
        for path_obj in evidence_paths[:5]:
            for triple in path_obj.path:
                candidate_entities.add(triple[2])  # tail entities
        
        # Simplified prompt for faster inference
        system_prompt = """You are a QA system. Answer the question based on evidence.

Return JSON:
{"answer": "entity_id", "confidence": 0.0-1.0, "reasoning": "brief explanation"}

Choose the most relevant entity ID from the evidence paths."""
        
        user_prompt = f"""Q: {question}

Evidence:
{evidence_text}

Candidate entities: {', '.join(list(candidate_entities)[:10])}

Answer with the best entity ID (JSON):"""
        
        try:
            response = self.llm.generate_with_prompt(
                system_prompt,
                user_prompt,
                temperature=0.2  # Lower temperature for consistency
            )
            
            # Parse JSON response
            import json
            json_text = response.strip()
            if json_text.startswith("```"):
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1])
            
            result = json.loads(json_text)
            
            answer = result.get("answer", "Unable to determine")
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            
            return answer, confidence, reasoning
            
        except Exception as e:
            if SYSTEM_CONFIG["verbose"]:
                print(f"  Error generating answer with LLM: {e}")
            
            # Fallback to heuristic
            heuristic = self._extract_answer_heuristic(evidence_paths, subgraph)
            if heuristic:
                answer, conf = heuristic
                return answer, conf, "Fallback to heuristic extraction"
            
            return "Error generating answer", 0.0, str(e)
    
    def _generate_answer_from_kg(
        self,
        question: str,
        subgraph: KnowledgeGraph
    ) -> tuple[str, float, str]:
        """
        Generate answer directly from KG when no evidence paths found.
        
        Args:
            question: Question text
            subgraph: Subgraph context
            
        Returns:
            Tuple of (answer_entity_id, confidence, reasoning)
        """
        # Get sample entities from KG
        entity_sample = []
        for entity_id, entity in list(subgraph.entities.items())[:20]:
            entity_sample.append(f"{entity_id}: {entity.name}")
        
        # Get sample relations
        relation_sample = []
        for relation in subgraph.relations[:10]:
            head_name = subgraph.entities[relation.head].name if relation.head in subgraph.entities else relation.head
            tail_name = subgraph.entities[relation.tail].name if relation.tail in subgraph.entities else relation.tail
            relation_sample.append(f"{head_name} --[{relation.relation}]--> {tail_name}")
        
        system_prompt = """You are a QA system. Answer based on the knowledge graph context.

Return JSON:
{"answer": "entity_id", "confidence": 0.0-1.0, "reasoning": "brief explanation"}

Choose the most relevant entity ID from the knowledge graph."""
        
        user_prompt = f"""Q: {question}

Knowledge Graph Context:
Entities (sample): {', '.join(entity_sample[:10])}

Relations (sample):
{chr(10).join(relation_sample[:5])}

Answer with the best entity ID (JSON):"""
        
        try:
            response = self.llm.generate_with_prompt(
                system_prompt,
                user_prompt,
                temperature=0.3
            )
            
            # Parse JSON response
            import json
            json_text = response.strip()
            if json_text.startswith("```"):
                lines = json_text.split('\n')
                json_text = '\n'.join(lines[1:-1])
            
            result = json.loads(json_text)
            
            answer = result.get("answer", "Unable to determine")
            confidence = float(result.get("confidence", 0.3))  # Lower default for no paths
            reasoning = result.get("reasoning", "Generated from KG without evidence paths")
            
            return answer, confidence, reasoning
            
        except Exception as e:
            if SYSTEM_CONFIG["verbose"]:
                print(f"  Error generating answer from KG: {e}")
            
            # Return a random entity as last resort
            if subgraph.entities:
                import random
                random_entity = random.choice(list(subgraph.entities.keys()))
                return random_entity, 0.1, f"Random selection (error: {str(e)})"
            
            return "Unable to find answer", 0.0, "No entities in KG"
    
    def _format_evidence_concise(
        self,
        evidence_paths: List[EvidencePath],
        subgraph: KnowledgeGraph
    ) -> str:
        """
        Format evidence paths concisely with proper entity and relation name mapping.
        
        This method ensures that:
        1. Entity IDs are mapped to human-readable names
        2. Relation paths are shortened to readable names
        3. Top 3 paths are selected for efficiency
        
        Args:
            evidence_paths: Evidence paths to format
            subgraph: Subgraph for entity names
            
        Returns:
            Formatted evidence text with mapped names
        """
        if not evidence_paths:
            return "No evidence paths available."
        
        lines = []
        lines.append("Top reasoning chains:\n")
        
        for i, path_obj in enumerate(evidence_paths[:3], 1):  # Only top 3 for efficiency
            # Convert path to readable text (entity IDs -> names, relation paths -> names)
            path_text = path_obj.to_text(subgraph)
            
            # Add path with confidence score
            confidence_icon = "✓" if path_obj.score >= 0.6 else "◐" if path_obj.score >= 0.4 else "✗"
            lines.append(f"{i}. {confidence_icon} [{path_obj.score:.2f}] {path_text}")
        
        return "\n".join(lines)

