"""Subgraph retriever module for EPERM system."""

from __future__ import annotations
from typing import List, Set, Tuple
import re
from knowledge_graph import KnowledgeGraph, Entity
from llm_client import LLMClient
from config import RETRIEVER_CONFIG, SYSTEM_CONFIG


class SubgraphRetriever:
    """Retrieves question-relevant subgraphs from knowledge graph."""
    
    def __init__(self, kg: KnowledgeGraph, llm_client: LLMClient):
        """
        Initialize subgraph retriever.
        
        Args:
            kg: Knowledge graph to query
            llm_client: LLM client for entity extraction
        """
        self.kg = kg
        self.llm = llm_client
        self.max_subgraph_size = RETRIEVER_CONFIG["max_subgraph_size"]
        self.max_hops = RETRIEVER_CONFIG["max_hops"]
        
    def retrieve(self, question: str) -> KnowledgeGraph:
        """
        Retrieve question-relevant subgraph.
        
        Args:
            question: Natural language question
            
        Returns:
            Subgraph as KnowledgeGraph
        """
        if SYSTEM_CONFIG["verbose"]:
            print(f"\n[Subgraph Retriever] Processing question: {question}")
        
        # Step 1: Extract seed entities from question
        seed_entities = self._extract_seed_entities(question)
        
        if not seed_entities:
            if SYSTEM_CONFIG["verbose"]:
                print("  No seed entities found, returning empty subgraph")
            return KnowledgeGraph()
        
        if SYSTEM_CONFIG["verbose"]:
            print(f"  Seed entities: {[self.kg.get_entity(e).name for e in seed_entities]}")
        
        # Step 2: Extract k-hop subgraph
        subgraph = self.kg.get_k_hop_subgraph(
            seed_entities,
            k=self.max_hops,
            max_nodes=self.max_subgraph_size
        )
        
        if SYSTEM_CONFIG["verbose"]:
            stats = subgraph.stats()
            print(f"  Retrieved subgraph: {stats['num_entities']} entities, {stats['num_relations']} relations")
        
        return subgraph
    
    def _extract_seed_entities(self, question: str) -> List[str]:
        """
        Extract seed entity IDs from question.
        
        Args:
            question: Question text
            
        Returns:
            List of entity IDs
        """
        # Use LLM to extract entity mentions
        entity_mentions = self._extract_entity_mentions_with_llm(question)
        
        # Match mentions to KG entities
        seed_entity_ids = []
        for mention in entity_mentions:
            matching_entities = self.kg.get_entity_by_name(mention)
            if matching_entities:
                # Take best match (first one)
                seed_entity_ids.append(matching_entities[0].id)
        
        return seed_entity_ids
    
    def _extract_entity_mentions_with_llm(self, question: str) -> List[str]:
        """
        Use LLM to extract entity mentions from question.
        
        Args:
            question: Question text
            
        Returns:
            List of entity mention strings
        """
        system_prompt = """You are an entity extraction system. Given a question, extract all entity mentions.
Return ONLY a comma-separated list of entities, nothing else.

Examples:
Question: "Who is the founder of Microsoft?"
Answer: Microsoft

Question: "What is the capital of France and Germany?"
Answer: France, Germany

Question: "When did Apple release the iPhone?"
Answer: Apple, iPhone"""
        
        user_prompt = f"Question: \"{question}\"\nAnswer:"
        
        try:
            response = self.llm.generate_with_prompt(
                system_prompt,
                user_prompt,
                temperature=0.3
            )
            
            # Parse comma-separated entities
            entities = [e.strip() for e in response.strip().split(',')]
            entities = [e for e in entities if e]  # Remove empty
            
            return entities
            
        except Exception as e:
            if SYSTEM_CONFIG["verbose"]:
                print(f"  Error extracting entities with LLM: {e}")
            # Fallback: simple capitalized word extraction
            return self._extract_entities_simple(question)
    
    def _extract_entities_simple(self, question: str) -> List[str]:
        """
        Simple fallback entity extraction using capitalization.
        
        Args:
            question: Question text
            
        Returns:
            List of potential entity mentions
        """
        # Find capitalized words/phrases
        words = question.split()
        entities = []
        
        for word in words:
            # Remove punctuation
            word = re.sub(r'[^\w\s]', '', word)
            if word and word[0].isupper() and len(word) > 1:
                entities.append(word)
        
        return entities
