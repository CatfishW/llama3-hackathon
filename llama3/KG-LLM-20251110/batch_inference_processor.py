"""Batch inference processor for efficient parallel question answering.

This module provides batch-level processing for the EPERM system, allowing
multiple QA items to be processed in parallel for better throughput.

Architecture:
  1. Collect QA items into batches
  2. Find evidence paths for all questions in a batch (parallel LLM scoring)
  3. Generate answers for all paths in a batch (parallel LLM inference)
  4. Track batch-level metrics (throughput, latency, resource utilization)

Example:
    processor = BatchInferenceProcessor(batch_size=8)
    batch_results = processor.process_batch(qa_items, system, tracker)
"""

from __future__ import annotations
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import time
from statistics import mean

from llm_client import LLMClient
from eperm_system import EPERMSystem
from evidence_path_finder_fast import EvidencePath
from knowledge_graph import KnowledgeGraph
from config import SYSTEM_CONFIG


@dataclass
class BatchResult:
    """Result for a single item in a batch."""
    item_id: str
    question: str
    gold_answers: List[str]
    predicted_answer: str
    confidence: float
    correct: bool
    processing_time: float
    num_evidence_paths: int
    error: Optional[str] = None


@dataclass
class BatchMetrics:
    """Metrics for a single batch processing."""
    batch_size: int
    batch_processing_time: float
    total_items_processed: int
    successful_items: int
    failed_items: int
    items_per_second: float
    avg_item_time: float
    batch_number: int
    
    def __str__(self) -> str:
        """Format metrics for display."""
        return (f"Batch #{self.batch_number}: "
                f"{self.successful_items}/{self.batch_size} successful | "
                f"{self.items_per_second:.2f} items/sec | "
                f"Avg: {self.avg_item_time:.2f}s")


class BatchInferenceProcessor:
    """Process multiple QA items in parallel batches."""
    
    def __init__(self, batch_size: int = 4, verbose: bool = True):
        """
        Initialize batch inference processor.
        
        Args:
            batch_size: Number of items to process in parallel
            verbose: Whether to print detailed batch information
        """
        self.batch_size = max(1, batch_size)
        self.verbose = verbose
        self.batch_count = 0
        self.total_processed = 0
        self.batch_metrics_history: List[BatchMetrics] = []
    
    def process_batch(
        self,
        qa_items: List[Dict[str, Any]],
        system: EPERMSystem,
        llm_client: LLMClient,
        flexible_match_fn,
        normalize_fn
    ) -> Tuple[List[BatchResult], BatchMetrics]:
        """
        Process a batch of QA items in parallel.
        
        Batching is used for answer prediction only. Path finding is done sequentially
        for each item in the batch to avoid complexity and maintain independence.
        
        Args:
            qa_items: List of QA item dictionaries (all should have same structure)
            system: EPERM system instance
            llm_client: LLM client for inference
            flexible_match_fn: Function to check if predicted answer matches gold answers
            normalize_fn: Function to normalize text for matching
            
        Returns:
            Tuple of (batch_results, batch_metrics)
        """
        self.batch_count += 1
        batch_start_time = time.time()
        
        if self.verbose:
            print(f"\n{'='*70}")
            print(f"Processing Batch #{self.batch_count} ({len(qa_items)} items)")
            print(f"{'='*70}")
        
        batch_results: List[BatchResult] = []
        
        # Step 1: Find evidence paths for each question (sequential, not batched)
        if self.verbose:
            print(f"Step 1: Finding evidence paths for {len(qa_items)} questions...")
        
        batch_evidence_paths = []
        for qa_item in qa_items:
            try:
                system.kg = qa_item['kg']
                evidence_paths = system.path_finder.find_evidence_paths(
                    qa_item['question'],
                    qa_item['kg']
                )
                batch_evidence_paths.append(evidence_paths)
            except Exception as e:
                if self.verbose:
                    print(f"    Error finding paths: {e}")
                batch_evidence_paths.append([])
        
        # Step 2: Generate answers for all evidence paths in batch (parallel)
        if self.verbose:
            print(f"Step 2: Generating answers for all evidence paths...")
        
        for i, qa_item in enumerate(qa_items):
            try:
                item_start_time = time.time()
                
                evidence_paths = batch_evidence_paths[i]
                
                # Generate answer
                if not evidence_paths:
                    # No evidence paths found - use LLM to predict answer directly
                    system_prompt = """You are a helpful AI assistant that answers questions accurately and concisely.
Answer the question directly without additional explanation unless necessary.
If you're unsure, provide your best answer based on your knowledge."""
                    user_prompt = f"Question: {qa_item['question']}\n\nAnswer:"
                    
                    try:
                        answer_text = llm_client.generate_with_prompt(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            temperature=0.1,
                            use_cache=True
                        ).strip()
                        confidence = 0.5  # Default confidence for LLM fallback
                    except:
                        answer_text = "No answer found"
                        confidence = 0.0
                    
                    num_paths = 0
                else:
                    # Predict answer from evidence paths
                    answer = system.answer_predictor.predict(
                        qa_item['question'],
                        evidence_paths,
                        qa_item['kg']
                    )
                    answer_text = answer.answer
                    confidence = answer.confidence
                    num_paths = len(answer.supporting_paths)
                
                # Check if answer is correct
                correct = flexible_match_fn(answer_text, qa_item['answers'])
                
                processing_time = time.time() - item_start_time
                
                result = BatchResult(
                    item_id=qa_item['id'],
                    question=qa_item['question'],
                    gold_answers=qa_item['answers'],
                    predicted_answer=answer_text,
                    confidence=confidence,
                    correct=correct,
                    processing_time=processing_time,
                    num_evidence_paths=num_paths,
                    error=None
                )
                batch_results.append(result)
                
                if self.verbose:
                    status = "✓" if correct else "✗"
                    print(f"  {i+1}. {status} {qa_item['question'][:50]}...")
                
            except Exception as e:
                if self.verbose:
                    print(f"  {i+1}. ✗ ERROR: {str(e)}")
                
                result = BatchResult(
                    item_id=qa_item['id'],
                    question=qa_item['question'],
                    gold_answers=qa_item['answers'],
                    predicted_answer="ERROR",
                    confidence=0.0,
                    correct=False,
                    processing_time=0.0,
                    num_evidence_paths=0,
                    error=str(e)
                )
                batch_results.append(result)
        
        # Compute batch metrics
        batch_time = time.time() - batch_start_time
        successful = sum(1 for r in batch_results if r.error is None)
        failed = len(batch_results) - successful
        items_per_second = len(batch_results) / batch_time if batch_time > 0 else 0
        avg_item_time = batch_time / len(batch_results) if batch_results else 0
        
        metrics = BatchMetrics(
            batch_size=len(qa_items),
            batch_processing_time=batch_time,
            total_items_processed=len(batch_results),
            successful_items=successful,
            failed_items=failed,
            items_per_second=items_per_second,
            avg_item_time=avg_item_time,
            batch_number=self.batch_count
        )
        
        self.batch_metrics_history.append(metrics)
        self.total_processed += len(batch_results)
        
        if self.verbose:
            print(f"\n{metrics}")
        
        return batch_results, metrics
    
    def _batch_find_evidence_paths(
        self,
        qa_items: List[Dict[str, Any]],
        system: EPERMSystem,
        llm_client: LLMClient
    ) -> List[List[EvidencePath]]:
        """
        Find evidence paths for multiple questions in parallel.
        
        This method groups multiple path-finding operations and uses batch
        LLM calls for scoring, reducing overall inference time.
        
        Args:
            qa_items: List of QA items with 'question' and 'kg' fields
            system: EPERM system (for access to path finder)
            llm_client: LLM client for batch operations
            
        Returns:
            List of evidence path lists (one per QA item)
        """
        all_paths_per_item = []
        
        # Step 1: Generate candidate paths for each question (no LLM needed)
        if SYSTEM_CONFIG.get("verbose"):
            print(f"  Generating candidate paths for {len(qa_items)} questions...")
        
        candidate_paths_per_item = []
        for qa_item in qa_items:
            # Use the path finder's internal method to get candidates without scoring
            system.kg = qa_item['kg']
            candidates = system.path_finder._get_candidate_paths(
                qa_item['question'],
                qa_item['kg']
            )
            candidate_paths_per_item.append(candidates)
        
        # Step 2: Prepare batch scoring of all candidate paths
        # Group candidates by question for batch scoring
        batch_scoring_tasks = []
        for i, (qa_item, candidates) in enumerate(zip(qa_items, candidate_paths_per_item)):
            if candidates:
                batch_scoring_tasks.append({
                    'item_idx': i,
                    'question': qa_item['question'],
                    'candidates': candidates[:15],  # Limit to top 15
                    'kg': qa_item['kg']
                })
        
        # Step 3: Score paths using batch LLM calls
        if batch_scoring_tasks:
            if SYSTEM_CONFIG.get("verbose"):
                print(f"  Batch scoring {len(batch_scoring_tasks)} candidate path sets...")
            
            scored_results = self._batch_score_paths(
                batch_scoring_tasks,
                system.path_finder,
                llm_client
            )
        else:
            scored_results = {}
        
        # Step 4: Collect results
        for i, qa_item in enumerate(qa_items):
            if i in scored_results:
                all_paths_per_item.append(scored_results[i])
            else:
                all_paths_per_item.append([])
        
        return all_paths_per_item
    
    def _batch_score_paths(
        self,
        batch_tasks: List[Dict[str, Any]],
        path_finder,
        llm_client: LLMClient
    ) -> Dict[int, List[EvidencePath]]:
        """
        Score multiple sets of candidate paths using batch LLM calls.
        
        Args:
            batch_tasks: List of scoring tasks with 'item_idx', 'question', 'candidates'
            path_finder: Evidence path finder instance
            llm_client: LLM client for batch inference
            
        Returns:
            Dictionary mapping item_idx to list of scored EvidencePath objects
        """
        results = {}
        
        try:
            # Prepare batch messages for LLM
            batch_messages = []
            task_indices = []
            
            for task in batch_tasks:
                item_idx = task['item_idx']
                question = task['question']
                candidates = task['candidates']
                kg = task['kg']
                
                # Format paths for scoring
                paths_text = []
                for i, path in enumerate(candidates):
                    path_str = path_finder._path_to_text(path, kg)
                    paths_text.append(f"{i+1}. {path_str}")
                
                all_paths_str = "\n".join(paths_text)
                
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
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                batch_messages.append(messages)
                task_indices.append(item_idx)
            
            # Call LLM in batch mode
            responses = llm_client.batch_chat(batch_messages, temperature=0.2, use_cache=True)
            
            # Parse responses
            import json
            for task, response, item_idx in zip(batch_tasks, responses, task_indices):
                scored_paths = []
                
                try:
                    # Parse JSON response
                    json_text = response.strip()
                    if json_text.startswith("```"):
                        lines = json_text.split('\n')
                        json_text = '\n'.join(lines[1:-1])
                    
                    scores_data = json.loads(json_text)
                    
                    # Create EvidencePath objects
                    for item in scores_data:
                        path_id = item.get("path_id", 1) - 1  # Convert to 0-indexed
                        if 0 <= path_id < len(task['candidates']):
                            score = float(item.get("score", 0.5))
                            reasoning = item.get("reasoning", "")
                            
                            evidence_path = EvidencePath(
                                path=task['candidates'][path_id],
                                score=score,
                                reasoning=reasoning
                            )
                            scored_paths.append(evidence_path)
                    
                except json.JSONDecodeError:
                    # Fallback to heuristic scoring
                    if SYSTEM_CONFIG.get("verbose"):
                        print(f"    Warning: Could not parse JSON for item {item_idx}")
                    scored_paths = path_finder._score_paths_heuristic(
                        task['candidates'],
                        task['kg']
                    )
                
                results[item_idx] = sorted(scored_paths, key=lambda p: p.score, reverse=True)
        
        except Exception as e:
            if SYSTEM_CONFIG.get("verbose"):
                print(f"  Error in batch path scoring: {e}")
            
            # Fallback: return empty results, will be handled in caller
            for task in batch_tasks:
                results[task['item_idx']] = []
        
        return results
    
    def get_batch_statistics(self) -> Dict[str, Any]:
        """
        Get aggregated statistics across all batches processed.
        
        Returns:
            Dictionary with batch-level statistics
        """
        if not self.batch_metrics_history:
            return {
                'total_batches': 0,
                'total_items_processed': 0,
                'avg_batch_time': 0.0,
                'avg_items_per_second': 0.0,
                'total_successful': 0,
                'total_failed': 0
            }
        
        total_time = sum(m.batch_processing_time for m in self.batch_metrics_history)
        total_items_processed = sum(m.total_items_processed for m in self.batch_metrics_history)
        total_successful = sum(m.successful_items for m in self.batch_metrics_history)
        total_failed = sum(m.failed_items for m in self.batch_metrics_history)
        
        return {
            'total_batches': len(self.batch_metrics_history),
            'total_items_processed': total_items_processed,
            'avg_batch_time': mean(m.batch_processing_time for m in self.batch_metrics_history),
            'avg_items_per_second': mean(m.items_per_second for m in self.batch_metrics_history),
            'total_successful': total_successful,
            'total_failed': total_failed,
            'overall_success_rate': (total_successful / total_items_processed * 100) 
                                   if total_items_processed > 0 else 0
        }
    
    def print_batch_statistics(self):
        """Print formatted batch statistics."""
        stats = self.get_batch_statistics()
        
        print("\n" + "="*70)
        print("BATCH PROCESSING STATISTICS")
        print("="*70)
        print(f"Total Batches: {stats['total_batches']}")
        print(f"Total Items Processed: {stats['total_items_processed']}")
        print(f"Average Batch Time: {stats['avg_batch_time']:.2f}s")
        print(f"Average Throughput: {stats['avg_items_per_second']:.2f} items/sec")
        print(f"Total Successful: {stats['total_successful']}")
        print(f"Total Failed: {stats['total_failed']}")
        print(f"Overall Success Rate: {stats['overall_success_rate']:.1f}%")
        print("="*70)
