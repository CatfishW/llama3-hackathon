"""Main EPERM system orchestration."""

from __future__ import annotations
from typing import Dict, Optional
from knowledge_graph import KnowledgeGraph
from llm_client import LLMClient
from subgraph_retriever import SubgraphRetriever
from evidence_path_finder import EvidencePathFinder
from answer_predictor import AnswerPredictor, Answer
from config import SYSTEM_CONFIG


class EPERMSystem:
    """
    Evidence Path Enhanced Reasoning Model system.
    
    Orchestrates the three main modules:
    1. Subgraph Retriever
    2. Evidence Path Finder
    3. Answer Predictor
    """
    
    def __init__(self):
        """Initialize EPERM system."""
        self.kg: Optional[KnowledgeGraph] = None
        self.llm = LLMClient()
        self.retriever: Optional[SubgraphRetriever] = None
        self.path_finder = EvidencePathFinder(self.llm)
        self.answer_predictor = AnswerPredictor(self.llm)
        
        if SYSTEM_CONFIG["verbose"]:
            print("EPERM System initialized")
    
    def load_knowledge_graph(self, kg_path: str):
        """
        Load knowledge graph from file.
        
        Args:
            kg_path: Path to knowledge graph JSON file
        """
        if SYSTEM_CONFIG["verbose"]:
            print(f"\nLoading knowledge graph from: {kg_path}")
        
        self.kg = KnowledgeGraph()
        self.kg.load_from_json(kg_path)
        self.retriever = SubgraphRetriever(self.kg, self.llm)
        
        if SYSTEM_CONFIG["verbose"]:
            stats = self.kg.stats()
            print(f"Loaded KG: {stats}")
    
    def load_knowledge_graph_from_dict(self, kg_data: Dict):
        """
        Load knowledge graph from dictionary.
        
        Args:
            kg_data: Knowledge graph data dictionary
        """
        if SYSTEM_CONFIG["verbose"]:
            print(f"\nLoading knowledge graph from dictionary")
        
        self.kg = KnowledgeGraph()
        self.kg.load_from_dict(kg_data)
        self.retriever = SubgraphRetriever(self.kg, self.llm)
        
        if SYSTEM_CONFIG["verbose"]:
            stats = self.kg.stats()
            print(f"Loaded KG: {stats}")
    
    def answer_question(self, question: str) -> Answer:
        """
        Answer a question using the EPERM pipeline.
        
        Args:
            question: Natural language question
            
        Returns:
            Answer object with result and metadata
        """
        if self.kg is None or self.retriever is None:
            raise ValueError("Knowledge graph not loaded. Call load_knowledge_graph() first.")
        
        print(f"\n{'='*70}")
        print(f"Question: {question}")
        print(f"{'='*70}")
        
        # Step 1: Retrieve subgraph
        subgraph = self.retriever.retrieve(question)
        
        if len(subgraph) == 0:
            return Answer(
                answer="No relevant information found",
                confidence=0.0,
                supporting_paths=[],
                reasoning="Failed to retrieve relevant subgraph"
            )
        
        # Step 2: Find evidence paths
        evidence_paths = self.path_finder.find_evidence_paths(question, subgraph)
        
        if not evidence_paths:
            return Answer(
                answer="Unable to find reasoning paths",
                confidence=0.0,
                supporting_paths=[],
                reasoning="No evidence paths found in subgraph"
            )
        
        # Step 3: Predict answer
        answer = self.answer_predictor.predict(question, evidence_paths, subgraph)
        
        return answer
    
    def answer_question_detailed(self, question: str) -> Dict:
        """
        Answer question with detailed intermediate results.
        
        Args:
            question: Natural language question
            
        Returns:
            Dictionary with answer and all intermediate results
        """
        answer = self.answer_question(question)
        
        return {
            "question": question,
            "answer": answer.answer,
            "confidence": answer.confidence,
            "reasoning": answer.reasoning,
            "num_evidence_paths": len(answer.supporting_paths),
            "evidence_paths": [
                {
                    "path": path.to_text(self.kg),
                    "score": path.score,
                    "reasoning": path.reasoning
                }
                for path in answer.supporting_paths
            ]
        }
    
    def clear_cache(self):
        """Clear LLM response cache."""
        self.llm.clear_cache()
        if SYSTEM_CONFIG["verbose"]:
            print("System cache cleared")
