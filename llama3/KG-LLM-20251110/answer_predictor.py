"""Answer predictor module for EPERM system."""

from __future__ import annotations
from typing import List, Dict
from dataclasses import dataclass
from knowledge_graph import KnowledgeGraph
from evidence_path_finder import EvidencePath
from llm_client import LLMClient
from config import PREDICTOR_CONFIG, SYSTEM_CONFIG


@dataclass
class Answer:
    """Final answer with confidence and supporting evidence."""
    answer: str
    confidence: float
    supporting_paths: List[EvidencePath]
    reasoning: str


class AnswerPredictor:
    """Predicts final answer based on weighted evidence paths."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize answer predictor.
        
        Args:
            llm_client: LLM client for answer generation
        """
        self.llm = llm_client
        self.top_k_paths = PREDICTOR_CONFIG["top_k_paths"]
        self.min_confidence = PREDICTOR_CONFIG["min_confidence"]
        
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
            evidence_paths: List of evidence paths
            subgraph: Original subgraph for context
            
        Returns:
            Answer object with result and metadata
        """
        if SYSTEM_CONFIG["verbose"]:
            print(f"\n[Answer Predictor] Generating answer")
        
        if not evidence_paths:
            return Answer(
                answer="Unable to find answer",
                confidence=0.0,
                supporting_paths=[],
                reasoning="No evidence paths found"
            )
        
        # Select top-k evidence paths
        top_paths = sorted(evidence_paths, key=lambda p: p.score, reverse=True)[:self.top_k_paths]
        
        # Generate answer using LLM
        answer_text, confidence, reasoning = self._generate_answer(
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
        
        if SYSTEM_CONFIG["verbose"]:
            print(f"  Answer: {answer_text}")
            print(f"  Confidence: {confidence:.3f}")
        
        return answer
    
    def _generate_answer(
        self,
        question: str,
        evidence_paths: List[EvidencePath],
        subgraph: KnowledgeGraph
    ) -> tuple[str, float, str]:
        """
        Generate answer using LLM with evidence paths.
        
        Args:
            question: Question text
            evidence_paths: Top evidence paths
            subgraph: Subgraph context
            
        Returns:
            Tuple of (answer_text, confidence, reasoning)
        """
        # Format evidence paths
        evidence_text = self._format_evidence(evidence_paths, subgraph)
        
        system_prompt = """You are a question answering system. Given a question and evidence paths from a knowledge graph, provide a concise answer.

Return JSON with:
- "answer": the direct answer to the question (concise, typically 1-10 words)
- "confidence": float between 0 and 1 (how confident are you?)
- "reasoning": brief explanation of your reasoning

Be direct and specific. If the evidence clearly supports an answer, give it with high confidence."""
        
        user_prompt = f"""Question: "{question}"

Evidence from Knowledge Graph:
{evidence_text}

Based on this evidence, what is the answer? (return JSON):"""
        
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
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "")
            
            return answer, confidence, reasoning
            
        except Exception as e:
            if SYSTEM_CONFIG["verbose"]:
                print(f"  Error generating answer with LLM: {e}")
            return "Error generating answer", 0.0, str(e)
    
    def _format_evidence(
        self,
        evidence_paths: List[EvidencePath],
        subgraph: KnowledgeGraph
    ) -> str:
        """
        Format evidence paths for LLM prompt with proper entity name mapping.
        
        This method ensures that:
        1. Entity IDs (like m.06f7lp) are mapped to human-readable names
        2. Relation paths (like location.location.containedby) are shortened to readable names
        3. Each path includes context about what it means
        
        Args:
            evidence_paths: Evidence paths to format
            subgraph: Subgraph for entity names
            
        Returns:
            Formatted evidence text with mapped names
        """
        lines = []
        
        if not evidence_paths:
            return "No evidence paths available."
        
        lines.append("Evidence reasoning chains from the knowledge graph:\n")
        
        for i, path_obj in enumerate(evidence_paths, 1):
            # Convert path to readable text (entity IDs -> names, relation paths -> names)
            path_text = path_obj.to_text(subgraph)
            score = path_obj.score
            
            # Add path with score and confidence indicator
            confidence_icon = "✓" if score >= 0.6 else "◐" if score >= 0.4 else "✗"
            lines.append(f"{i}. {confidence_icon} [Confidence: {score:.2f}] {path_text}")
            
            # Add reasoning if available
            if path_obj.reasoning:
                lines.append(f"   Context: {path_obj.reasoning}")
        
        return "\n".join(lines)

