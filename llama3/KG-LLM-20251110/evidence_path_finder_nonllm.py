"""Non-LLM evidence path finder using graph algorithms and heuristics."""

from __future__ import annotations
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
import math
from collections import Counter
from knowledge_graph import KnowledgeGraph, get_global_entity_name_map
from evidence_path_finder import EvidencePath
from config import PATH_FINDER_CONFIG, SYSTEM_CONFIG


class NonLLMEvidencePathFinder:
    """Finds and scores evidence paths using graph algorithms without LLM."""
    
    def __init__(self):
        """Initialize non-LLM evidence path finder."""
        self.max_paths = PATH_FINDER_CONFIG["max_paths"]
        self.max_path_length = PATH_FINDER_CONFIG["max_path_length"]
        self.score_weights = PATH_FINDER_CONFIG["score_weights"]
        
        # TF-IDF cache for question keywords
        self.question_keywords_cache = {}
        
        # Entity popularity cache (degree centrality)
        self.entity_popularity_cache = {}
        
    def find_evidence_paths(
        self,
        question: str,
        subgraph: KnowledgeGraph
    ) -> List[EvidencePath]:
        """
        Find and score evidence paths using graph algorithms.
        
        Algorithm:
        1. Extract keywords from question (stop word removal, TF-IDF)
        2. Identify answer candidate entities (keyword matching + entity degree)
        3. Find all paths to candidates using BFS/DFS
        4. Score paths based on: relation importance, path length, entity popularity, keyword match
        5. Return top-k paths
        
        Args:
            question: Question text
            subgraph: Retrieved subgraph
            
        Returns:
            List of evidence paths with scores
        """
        if SYSTEM_CONFIG["verbose"]:
            print(f"\n[Non-LLM Evidence Path Finder] Finding paths for question")
        
        if len(subgraph) == 0:
            return []
        
        # Step 1: Extract question keywords (TF-IDF based)
        question_keywords = self._extract_question_keywords(question)
        
        if SYSTEM_CONFIG["verbose"]:
            print(f"  Question keywords: {question_keywords}")
        
        # Step 2: Identify potential answer entities
        answer_candidates = self._identify_answer_candidates_heuristic(
            question,
            question_keywords,
            subgraph
        )
        
        if not answer_candidates:
            if SYSTEM_CONFIG["verbose"]:
                print("  No answer candidates identified")
            return []
        
        if SYSTEM_CONFIG["verbose"]:
            print(f"  Answer candidates: {[c['entity'].name for c in answer_candidates[:3]]}")
        
        # Step 3: Find paths to answer candidates
        all_paths = self._find_paths_to_candidates(question, subgraph, answer_candidates)
        
        if not all_paths:
            if SYSTEM_CONFIG["verbose"]:
                print("  No valid paths found")
            return []
        
        # Step 4: Score and rank paths
        scored_paths = self._score_paths_heuristic(
            question,
            question_keywords,
            all_paths,
            subgraph
        )
        
        # Return top-k paths
        top_paths = sorted(scored_paths, key=lambda p: p.score, reverse=True)[:self.max_paths]
        
        if SYSTEM_CONFIG["verbose"]:
            print(f"  Found {len(top_paths)} evidence paths")
            for i, path in enumerate(top_paths[:3], 1):
                print(f"    Path {i} (score={path.score:.3f}): {path.to_text(subgraph)}")
        
        return top_paths
    
    def _extract_question_keywords(self, question: str) -> Dict[str, float]:
        """
        Extract keywords from question using TF-IDF-like scoring.
        
        Removes stop words, assigns higher weight to longer/rarer words.
        Returns: dict of {keyword: score}
        """
        # Stop words (common words to ignore)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'that', 'this', 'these',
            'those', 'what', 'which', 'who', 'whom', 'where', 'when', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 'just', 'before', 'during', 'after', 'serve', 'serves', 'is',
            'are', 'am', 'been', 'be', 'being', 'you', 'your', 'he', 'his', 'she',
            'her', 'it', 'its', 'we', 'our', 'they', 'their', 'them'
        }
        
        # Tokenize and filter
        words = question.lower().split()
        words = [w.strip('.,!?;:') for w in words]
        words = [w for w in words if w and w not in stop_words and len(w) > 2]
        
        # Score keywords (longer words get higher scores)
        keywords = {}
        word_freq = Counter(words)
        
        for word, freq in word_freq.items():
            # Score: frequency * length_factor
            # Longer, specific words are weighted higher
            length_factor = 1.0 + math.log(len(word))
            frequency_factor = math.log(freq + 1)
            score = length_factor * frequency_factor
            keywords[word] = score
        
        # Normalize scores
        if keywords:
            max_score = max(keywords.values())
            keywords = {k: v / max_score for k, v in keywords.items()}
        
        return keywords
    
    def _identify_answer_candidates_heuristic(
        self,
        question: str,
        question_keywords: Dict[str, float],
        subgraph: KnowledgeGraph
    ) -> List[Dict]:
        """
        Identify potential answer entities using heuristics (no LLM).
        
        Scores entities based on:
        1. Entity name keyword overlap with question
        2. Entity degree (importance in graph)
        3. Entity type (entities are often answers)
        
        Returns: List of {entity, score}
        """
        entity_scores = {}
        
        # Calculate entity popularity (degree centrality)
        entity_degrees = self._calculate_entity_degrees(subgraph)
        max_degree = max(entity_degrees.values()) if entity_degrees else 1
        
        # Get global entity name map for better matching
        entity_name_map = get_global_entity_name_map()
        
        for entity in subgraph.entities.values():
            score = 0.0
            
            # 1. Keyword overlap in entity name
            entity_name = entity.name.lower()
            entity_id_name = entity_name_map.get(entity.id, entity.name).lower()
            
            # Check if any question keyword appears in entity name
            keyword_overlap = 0.0
            for keyword, keyword_score in question_keywords.items():
                if keyword in entity_name or keyword in entity_id_name:
                    keyword_overlap += keyword_score
            
            # 2. Entity degree (popularity)
            degree_score = entity_degrees.get(entity.id, 0) / max_degree if max_degree > 0 else 0
            degree_score *= 0.5  # Lower weight than keyword overlap
            
            # 3. Prefer entities with longer/more specific names (likely more informative)
            name_length_score = min(1.0, len(entity.name) / 20.0)  # Normalize to ~20 chars
            name_length_score *= 0.3
            
            # Combine scores
            score = keyword_overlap + degree_score + name_length_score
            
            if score > 0:
                entity_scores[entity.id] = {
                    'entity': entity,
                    'score': score,
                    'keyword_overlap': keyword_overlap,
                    'degree': degree_score,
                    'name_length': name_length_score
                }
        
        # Return top-5 candidates
        candidates = sorted(
            [{'entity': v['entity'], 'score': v['score']} for v in entity_scores.values()],
            key=lambda x: x['score'],
            reverse=True
        )[:5]
        
        return candidates if candidates else list(subgraph.entities.values())[:5]
    
    def _calculate_entity_degrees(self, subgraph: KnowledgeGraph) -> Dict[str, float]:
        """Calculate degree centrality for each entity."""
        degrees = {}
        for entity_id in subgraph.entities.keys():
            # Count incoming and outgoing edges
            in_degree = len(list(subgraph.graph.predecessors(entity_id)))
            out_degree = len(list(subgraph.graph.successors(entity_id)))
            degrees[entity_id] = in_degree + out_degree
        return degrees
    
    def _find_paths_to_candidates(
        self,
        question: str,
        subgraph: KnowledgeGraph,
        candidates: List[Dict]
    ) -> List[List[Tuple[str, str, str]]]:
        """
        Find reasoning paths to answer candidates using BFS/DFS.
        
        Strategy: Find all entities and their paths to candidate entities,
        prioritizing paths through high-degree hub nodes.
        """
        all_paths = []
        target_entity_ids = [c["entity"].id for c in candidates[:5]]
        
        # Find paths from all entities to candidates
        for target_id in target_entity_ids:
            # Find paths from other entities to this target
            for source_id in subgraph.entities.keys():
                if source_id == target_id:
                    continue
                
                paths = subgraph.find_paths(
                    source_id,
                    target_id,
                    max_length=self.max_path_length,
                    max_paths=3
                )
                all_paths.extend(paths)
        
        return all_paths[:50]
    
    def _score_paths_heuristic(
        self,
        question: str,
        question_keywords: Dict[str, float],
        paths: List[List[Tuple[str, str, str]]],
        subgraph: KnowledgeGraph
    ) -> List[EvidencePath]:
        """
        Score paths using multiple heuristics.
        
        Scoring factors:
        1. Path length: Shorter paths are better (Occam's razor)
        2. Relation importance: Some relations are more informative
        3. Entity popularity: Hub entities are more trustworthy
        4. Question relevance: Keywords mentioned in path
        5. Diversity: Penalize redundant paths
        
        Returns: List of EvidencePath objects with scores
        """
        scored_paths = []
        
        # Entity popularity for scoring
        entity_degrees = self._calculate_entity_degrees(subgraph)
        max_degree = max(entity_degrees.values()) if entity_degrees else 1
        
        entity_name_map = get_global_entity_name_map()
        
        # Important relation keywords (relations containing these are scored higher)
        important_relation_keywords = {
            'found', 'created', 'author', 'invent', 'discover', 'winner', 
            'direct', 'film', 'movie', 'star', 'actor', 'award', 'birth',
            'country', 'capital', 'location', 'type', 'member', 'part'
        }
        
        for path in paths:
            score = 0.0
            reasoning_parts = []
            
            # Factor 1: Path length penalty (shorter is better)
            # Normalize: length 1-5 maps to 1.0-0.2 score contribution
            path_length_score = max(0.2, 1.0 - (len(path) - 1) * 0.15)
            score += path_length_score * 0.25
            reasoning_parts.append(f"path_length={path_length_score:.2f}")
            
            # Factor 2: Relation importance
            relation_importance_score = 0.0
            for head_id, relation, tail_id in path:
                # Check if relation contains important keywords
                relation_lower = relation.lower()
                for keyword in important_relation_keywords:
                    if keyword in relation_lower:
                        relation_importance_score += 0.25  # Boost for important relations
                        break
            
            relation_importance_score = min(1.0, relation_importance_score / len(path)) if path else 0
            score += relation_importance_score * 0.25
            reasoning_parts.append(f"relation_importance={relation_importance_score:.2f}")
            
            # Factor 3: Entity popularity (prefer paths through hub nodes)
            entity_popularity_score = 0.0
            for head_id, relation, tail_id in path:
                head_degree = entity_degrees.get(head_id, 0) / max_degree if max_degree > 0 else 0
                tail_degree = entity_degrees.get(tail_id, 0) / max_degree if max_degree > 0 else 0
                entity_popularity_score += (head_degree + tail_degree) / 2
            
            entity_popularity_score = entity_popularity_score / len(path) if path else 0
            score += entity_popularity_score * 0.25
            reasoning_parts.append(f"entity_popularity={entity_popularity_score:.2f}")
            
            # Factor 4: Question relevance (do entities/relations contain keywords?)
            question_relevance_score = 0.0
            for head_id, relation, tail_id in path:
                # Check entity names
                head_entity = subgraph.get_entity(head_id)
                tail_entity = subgraph.get_entity(tail_id)
                
                head_name = head_entity.name.lower() if head_entity else ""
                tail_name = tail_entity.name.lower() if tail_entity else ""
                relation_lower = relation.lower()
                
                # Check keyword overlap
                for keyword in question_keywords.keys():
                    if keyword in head_name or keyword in tail_name or keyword in relation_lower:
                        question_relevance_score += question_keywords[keyword]
            
            question_relevance_score = min(1.0, question_relevance_score)
            score += question_relevance_score * 0.25
            reasoning_parts.append(f"question_relevance={question_relevance_score:.2f}")
            
            # Final score (0-1 range)
            final_score = min(1.0, max(0.0, score))
            
            # Create reasoning string
            reasoning = "; ".join(reasoning_parts)
            
            evidence_path = EvidencePath(
                path=path,
                score=final_score,
                reasoning=reasoning
            )
            scored_paths.append(evidence_path)
        
        return scored_paths
