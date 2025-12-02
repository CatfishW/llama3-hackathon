"""Answer predictor module for EPERM system."""

from __future__ import annotations
from typing import List, Dict
from dataclasses import dataclass
import json
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
        # Check if we have sufficient evidence
        has_evidence = evidence_paths and len(evidence_paths) > 0
        has_strong_evidence = has_evidence and any(path.score >= 0.5 for path in evidence_paths)
        
        # Format evidence paths
        evidence_text = self._format_evidence(evidence_paths, subgraph)
        
        if not has_evidence or not has_strong_evidence:
            # Low/no evidence - allow LLM to use its knowledge
            system_prompt = """You are a helpful question answering system. 

You will be asked a question. If evidence paths are provided from a knowledge graph, use them primarily.
If evidence is insufficient or weak, you may use your own knowledge to provide the best answer.

Return JSON with:
- "answer": the direct answer to the question (concise, typically 1-10 words)
- "confidence": float between 0 and 1 (how confident are you in this answer?)
- "reasoning": brief explanation of your reasoning and whether it's from evidence or knowledge

Be direct and specific. If evidence is weak, indicate that you're using general knowledge."""
            
            if not has_evidence:
                user_prompt = f"""Question: "{question}"

No evidence paths found in the knowledge graph.
Use your general knowledge to answer this question. (return JSON):"""
            else:
                user_prompt = f"""Question: "{question}"

Limited evidence from Knowledge Graph:
{evidence_text}

The evidence above is weak or limited. You may supplement with your general knowledge to answer this question. (return JSON):"""
        else:
            # Strong evidence available - rely primarily on it
            system_prompt = """You are a question answering system. Given a question and evidence paths from a knowledge graph, provide a concise answer.

Return JSON with:
- "answer": the direct answer to the question (concise, typically 1-10 words)
- "confidence": float between 0 and 1 (how confident are you?)
- "reasoning": brief explanation of your reasoning

Be direct and specific. Prioritize the evidence paths provided. Give high confidence when evidence clearly supports an answer."""
            
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
    
    def predict_batch(
        self,
        questions: List[str],
        evidence_paths_list: List[List[EvidencePath]],
        subgraph: KnowledgeGraph,
        batch_size: int = 32
    ) -> List[Answer]:
        """
        Predict answers for multiple questions using batched LLM inference.
        Supports configurable batch sizes for optimal performance.
        
        Args:
            questions: List of question texts
            evidence_paths_list: List of evidence path lists (one per question)
            subgraph: Subgraph context
            batch_size: Number of questions to process per batch (32 recommended)
            
        Returns:
            List of Answer objects
        """
        if SYSTEM_CONFIG["verbose"]:
            print(f"\n[Answer Predictor] Generating {len(questions)} answers in batches of {batch_size}")
        
        all_results = []
        
        # Process in batches
        for batch_start in range(0, len(questions), batch_size):
            batch_end = min(batch_start + batch_size, len(questions))
            batch_questions = questions[batch_start:batch_end]
            batch_evidence = evidence_paths_list[batch_start:batch_end]
            
            if SYSTEM_CONFIG["verbose"]:
                print(f"  Processing batch {batch_start // batch_size + 1} ({batch_start}-{batch_end})")
            
            # Process this batch
            batch_results = self._predict_batch_internal(batch_questions, batch_evidence, subgraph)
            all_results.extend(batch_results)
        
        return all_results
    
    def _predict_batch_internal(
        self,
        questions: List[str],
        evidence_paths_list: List[List[EvidencePath]],
        subgraph: KnowledgeGraph
    ) -> List[Answer]:
        """
        Internal method to predict a single batch of answers.
        
        Args:
            questions: Batch of question texts
            evidence_paths_list: Batch of evidence path lists
            subgraph: Subgraph context
            
        Returns:
            List of Answer objects
        """
        # Prepare batch messages
        batch_messages = []
        batch_evidence_list = []
        batch_questions = []
        
        for question, evidence_paths in zip(questions, evidence_paths_list):
            if not evidence_paths:
                continue  # Skip questions with no evidence for now
            
            # Select top-k evidence paths
            top_paths = sorted(evidence_paths, key=lambda p: p.score, reverse=True)[:self.top_k_paths]
            
            # Format evidence
            evidence_text = self._format_evidence(top_paths, subgraph)
            
            # Check evidence strength
            has_strong_evidence = any(path.score >= 0.5 for path in top_paths)
            
            # Build messages
            if not has_strong_evidence:
                system_prompt = """You are a helpful question answering system. 

You will be asked a question. If evidence paths are provided from a knowledge graph, use them primarily.
If evidence is insufficient or weak, you may use your own knowledge to provide the best answer.

Return JSON with:
- "answer": the direct answer to the question (concise, typically 1-10 words)
- "confidence": float between 0 and 1 (how confident are you in this answer?)
- "reasoning": brief explanation of your reasoning"""
                user_prompt = f"""Question: "{question}"

Limited evidence from Knowledge Graph:
{evidence_text}

Supplement with your knowledge if needed. (return JSON):"""
            else:
                system_prompt = """You are a question answering system. Given a question and evidence paths from a knowledge graph, provide a concise answer.

Return JSON with:
- "answer": the direct answer to the question (concise, typically 1-10 words)
- "confidence": float between 0 and 1 (how confident are you?)
- "reasoning": brief explanation of your reasoning"""
                user_prompt = f"""Question: "{question}"

Evidence from Knowledge Graph:
{evidence_text}

Based on this evidence, what is the answer? (return JSON):"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            batch_messages.append(messages)
            batch_evidence_list.append(top_paths)
            batch_questions.append(question)
        
        # Make batch LLM calls
        if not batch_messages:
            return []
        
        responses = self.llm.batch_chat(batch_messages, temperature=0.3)
        
        # Parse responses
        results = []
        
        for question, response, top_paths in zip(batch_questions, responses, batch_evidence_list):
            try:
                json_text = response.strip()
                if json_text.startswith("```"):
                    lines = json_text.split('\n')
                    json_text = '\n'.join(lines[1:-1])
                
                result = json.loads(json_text)
                
                answer_text = result.get("answer", "Unable to determine")
                confidence = float(result.get("confidence", 0.5))
                reasoning = result.get("reasoning", "")
                
                answer = Answer(
                    answer=answer_text,
                    confidence=confidence,
                    supporting_paths=top_paths,
                    reasoning=reasoning
                )
                results.append(answer)
                
            except Exception as e:
                if SYSTEM_CONFIG["verbose"]:
                    print(f"  Error parsing batch response: {e}")
                results.append(Answer(
                    answer="Error processing",
                    confidence=0.0,
                    supporting_paths=[],
                    reasoning=str(e)
                ))
        
        return results
    
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

