"""Test EPERM system with WebQSP dataset."""

from webqsp_loader import WebQSPLoader
from eperm_system import EPERMSystem
from llm_client import LLMClient
from evidence_path_finder_nonllm import NonLLMEvidencePathFinder
from batch_inference_processor import BatchInferenceProcessor, BatchResult
import time
import unicodedata
import re
import json
from statistics import mean, stdev, median
from collections import defaultdict
from datetime import datetime
import os
from pathlib import Path


class CheckpointManager:
    """Manages checkpointing for long-running tests."""
    
    def __init__(self, checkpoint_dir: str = "test_results/checkpoints"):
        """Initialize checkpoint manager."""
        self.checkpoint_dir = checkpoint_dir
        Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(self, results: list, checkpoint_name: str = None, metadata: dict = None) -> str:
        """
        Save results as a checkpoint.
        
        Args:
            results: List of result dictionaries
            checkpoint_name: Optional custom checkpoint name
            metadata: Optional metadata to save with checkpoint
            
        Returns:
            Path to saved checkpoint
        """
        if checkpoint_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_name = f"checkpoint_{len(results)}_{timestamp}.json"
        
        checkpoint_path = os.path.join(self.checkpoint_dir, checkpoint_name)
        
        checkpoint_data = {
            'timestamp': datetime.now().isoformat(),
            'num_results': len(results),
            'results': results,
            'metadata': metadata or {}
        }
        
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        return checkpoint_path
    
    def load_checkpoint(self, checkpoint_path: str) -> tuple:
        """
        Load results from a checkpoint.
        
        Args:
            checkpoint_path: Path to checkpoint file
            
        Returns:
            Tuple of (results, metadata)
        """
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
        
        return checkpoint_data.get('results', []), checkpoint_data.get('metadata', {})
    
    def get_latest_checkpoint(self) -> str:
        """Get path to most recent checkpoint."""
        checkpoints = sorted(
            [f for f in os.listdir(self.checkpoint_dir) if f.startswith('checkpoint_')],
            reverse=True
        )
        if checkpoints:
            return os.path.join(self.checkpoint_dir, checkpoints[0])
        return None
    
    def list_checkpoints(self) -> list:
        """List all available checkpoints."""
        return sorted(
            [f for f in os.listdir(self.checkpoint_dir) if f.startswith('checkpoint_')],
            reverse=True
        )


class RealTimeAccuracyTracker:
    """Tracks and displays real-time accuracy metrics."""
    
    def __init__(self):
        """Initialize accuracy tracker."""
        self.results = []
        self.start_time = time.time()
        self.checkpoint_manager = CheckpointManager()
    
    def add_result(self, result: dict):
        """Add a result and update running metrics."""
        self.results.append(result)
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        if not self.results:
            return {
                'total': 0,
                'correct': 0,
                'accuracy': 0.0,
                'avg_confidence': 0.0,
                'avg_time': 0.0,
                'elapsed_time': 0.0
            }
        
        correct = sum(1 for r in self.results if r['correct'])
        confidences = [r['confidence'] for r in self.results]
        times = [r['time'] for r in self.results if r['time'] > 0]
        
        return {
            'total': len(self.results),
            'correct': correct,
            'accuracy': correct / len(self.results) * 100,
            'avg_confidence': mean(confidences) if confidences else 0.0,
            'avg_time': mean(times) if times else 0.0,
            'elapsed_time': time.time() - self.start_time
        }
    
    def print_progress(self, sample_num: int, total_samples: int, current_result: dict = None):
        """Print progress update with real-time accuracy."""
        stats = self.get_stats()
        elapsed = stats['elapsed_time']
        
        # Calculate estimated time remaining
        if stats['total'] > 0:
            avg_time_per_sample = elapsed / stats['total']
            remaining_samples = total_samples - sample_num
            eta_seconds = avg_time_per_sample * remaining_samples
            eta_str = self._format_time(eta_seconds)
        else:
            eta_str = "Calculating..."
        
        # Build progress bar
        progress_pct = (sample_num / total_samples) * 100
        bar_length = 30
        filled = int(bar_length * sample_num / total_samples)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Print progress line
        print(f"\n[{bar}] {progress_pct:5.1f}% ({sample_num}/{total_samples})")
        print(f"  Accuracy: {stats['accuracy']:5.1f}% ({stats['correct']}/{stats['total']})")
        print(f"  Avg Confidence: {stats['avg_confidence']:.3f}")
        print(f"  Avg Time/Sample: {stats['avg_time']:.2f}s")
        print(f"  Elapsed: {self._format_time(elapsed)} | ETA: {eta_str}")
        
        # Show current result if provided
        if current_result:
            status = "✓" if current_result['correct'] else "✗"
            print(f"  Current: {status} {current_result['predicted_answer'][:50]}")
    
    def checkpoint_results(self, checkpoint_interval: int = None) -> bool:
        """
        Save checkpoint if interval threshold is met.
        
        Args:
            checkpoint_interval: Save checkpoint every N samples
            
        Returns:
            True if checkpoint was saved
        """
        if checkpoint_interval is None:
            return False
        
        if len(self.results) > 0 and len(self.results) % checkpoint_interval == 0:
            path = self.checkpoint_manager.save_checkpoint(
                self.results,
                checkpoint_name=f"checkpoint_{len(self.results)}.json",
                metadata={
                    'sample_number': len(self.results),
                    'timestamp': datetime.now().isoformat(),
                    'current_accuracy': self.get_stats()['accuracy']
                }
            )
            print(f"  [CHECKPOINT] Saved {len(self.results)} results to {os.path.basename(path)}")
            return True
        
        return False
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_checkpoint_manager(self) -> CheckpointManager:
        """Get the checkpoint manager."""
        return self.checkpoint_manager


def _expand_abbreviations(text: str) -> str:
    """
    Expand common abbreviations for better matching.
    
    Examples:
    - U.S. -> United States
    - U.S.A. -> United States of America
    - etc.
    """
    # Common abbreviations and expansions
    abbreviations = {
        r'\bu\.s\.a\.?\b': 'united states of america',
        r'\bu\.s\.?\b': 'united states',
        r'\bu\.k\.?\b': 'united kingdom',
        r'\bint\'l\b': 'international',
        r'\brep\.\b': 'representative',
        r'\bdir\.\b': 'director',
        r'\bpres\.\b': 'president',
        r'\bv\.p\.\b': 'vice president',
        r'\bfmr\.\b': 'former',
    }
    
    text = text.lower()
    for abbrev, expansion in abbreviations.items():
        text = re.sub(abbrev, expansion, text, flags=re.IGNORECASE)
    
    return text


def _get_content_words(text: str) -> set:
    """
    Extract content words (removing stop words) from text.
    
    Stop words: articles, prepositions, auxiliary verbs, etc.
    """
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'that', 'this', 'these',
        'those', 'what', 'which', 'who', 'whom', 'where', 'when', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 'just', 'before', 'during', 'after', 'serve', 'serves'
    }
    
    words = set(text.split())
    return words - stop_words


def _normalize_text(text: str) -> str:
    """
    Normalize text for comparison by:
    - Converting to lowercase
    - Expanding abbreviations
    - Removing accents/diacritics
    - Removing extra whitespace
    - Removing punctuation
    """
    # Expand abbreviations first
    text = _expand_abbreviations(text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove accents (é -> e, ñ -> n, etc.)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Remove punctuation and extra whitespace
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def _flexible_match(predicted: str, gold_answers: list, verbose: bool = False) -> bool:
    """
    Check if predicted answer matches any gold answer with advanced flexible matching.
    
    Handles:
    - Case differences (Padme vs padme)
    - Accent differences (Padmé vs Padme)
    - Article differences (The Bahamas vs Bahamas)
    - Whitespace differences
    - Word order differences (Tennessee governor vs Governor of Tennessee)
    - Abbreviations (U.S. vs United States)
    - Partial matches with semantic understanding
    
    Matching criteria (in order):
    1. Exact match after normalization
    2. Substring containment
    3. Content word overlap (70%+)
    4. Content word overlap (50%+) - more permissive
    5. Fuzzy matching with Jaccard similarity (60%+)
    
    Args:
        predicted: Predicted answer string
        gold_answers: List of gold answer strings
        verbose: Print matching details for debugging
        
    Returns:
        True if match found, False otherwise
    """
    # Normalize predicted answer
    pred_norm = _normalize_text(predicted)
    pred_words = _get_content_words(pred_norm)
    
    if verbose:
        print(f"\n  [MATCH DEBUG]")
        print(f"    Predicted (normalized): {pred_norm}")
        print(f"    Predicted (content words): {pred_words}")
    
    for gold in gold_answers:
        gold_norm = _normalize_text(gold)
        gold_words = _get_content_words(gold_norm)
        
        if verbose:
            print(f"    Gold (normalized): {gold_norm}")
            print(f"    Gold (content words): {gold_words}")
        
        # Strategy 1: Exact match after normalization
        if pred_norm == gold_norm:
            if verbose:
                print(f"    ✓ EXACT MATCH")
            return True
        
        # Strategy 2: Substring containment
        if gold_norm in pred_norm or pred_norm in gold_norm:
            if verbose:
                print(f"    ✓ SUBSTRING MATCH")
            return True
        
        # Strategy 3: High content word overlap (70%+)
        if pred_words and gold_words:
            overlap = len(pred_words & gold_words)
            similarity_high = overlap / max(len(pred_words), len(gold_words))
            if similarity_high >= 0.7:
                if verbose:
                    print(f"    ✓ HIGH OVERLAP ({similarity_high:.1%})")
                return True
            
            # Strategy 4: Moderate content word overlap (50%+)
            if similarity_high >= 0.5:
                if verbose:
                    print(f"    ✓ MODERATE OVERLAP ({similarity_high:.1%})")
                return True
        
        # Strategy 5: Jaccard similarity (fuzzy matching)
        if pred_words and gold_words:
            intersection = len(pred_words & gold_words)
            union = len(pred_words | gold_words)
            jaccard_similarity = intersection / union if union > 0 else 0
            
            if jaccard_similarity >= 0.6:
                if verbose:
                    print(f"    ✓ FUZZY MATCH (Jaccard: {jaccard_similarity:.1%})")
                return True
    
    if verbose:
        print(f"    ✗ NO MATCH FOUND")
    
    return False


def test_pure_llm(question: str, llm_client: LLMClient) -> tuple:
    """
    Test pure LLM without KG paths or evidence.
    
    Args:
        question: Question to answer
        llm_client: LLM client instance
        
    Returns:
        Tuple of (answer, confidence, reasoning)
    """
    system_prompt = """You are a helpful AI assistant that answers questions accurately and concisely.
Answer the question directly without additional explanation unless necessary.
If you're unsure, provide your best answer based on your knowledge."""

    user_prompt = f"Question: {question}\n\nAnswer:"
    
    try:
        response = llm_client.generate_with_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            use_cache=True
        )
        
        # Clean up response
        answer = response.strip()
        
        # Assign default confidence (pure LLM has no explicit confidence)
        confidence = 0.5
        reasoning = "Direct LLM response without KG evidence"
        
        return answer, confidence, reasoning
        
    except Exception as e:
        print(f"Error in pure LLM prediction: {e}")
        return "ERROR", 0.0, str(e)


def analyze_matching_results(results: list, show_mismatches: bool = True):
    """
    Analyze matching results and show detailed comparison for failed matches.
    
    Args:
        results: List of result dictionaries from test_eperm_with_webqsp
        show_mismatches: Show detailed debug output for incorrect matches
    """
    print("\n" + "="*70)
    print("MATCHING ANALYSIS")
    print("="*70)
    
    mismatches = [r for r in results if not r['correct']]
    
    print(f"\nTotal Results: {len(results)}")
    print(f"Correct Matches: {len(results) - len(mismatches)}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"Match Rate: {(len(results) - len(mismatches)) / len(results) * 100:.1f}%")
    
    if show_mismatches and mismatches:
        print("\n" + "="*70)
        print("DETAILED MISMATCH ANALYSIS")
        print("="*70)
        
        for i, r in enumerate(mismatches, 1):
            print(f"\n{i}. Question: {r['question']}")
            print(f"   Predicted: {r['predicted_answer']}")
            print(f"   Gold Answers:")
            for gold in r['gold_answers']:
                print(f"     - {gold}")
            
            # Run matching with verbose output
            print(f"\n   Re-running match with debug:")
            _flexible_match(r['predicted_answer'], r['gold_answers'], verbose=True)


def test_eperm_with_webqsp(num_samples: int = 3, max_kg_size: int = 1000, 
                           checkpoint_interval: int = None, resume_from_checkpoint: str = None,
                           use_pure_llm: bool = False, batch_size: int = 1,
                           use_nonllm_paths: bool = False):
    """
    Test EPERM system with WebQSP data with real-time accuracy and checkpointing.
    
    Args:
        num_samples: Number of samples to test
        max_kg_size: Maximum triples in KG (smaller = faster)
        checkpoint_interval: Save checkpoint every N samples (None = no checkpointing)
        resume_from_checkpoint: Path to checkpoint to resume from
        use_pure_llm: If True, use pure LLM without KG paths (baseline comparison)
        batch_size: Number of samples to process in parallel (for batched inference)
        use_nonllm_paths: If True, use non-LLM evidence path finder instead of LLM-based
    """
    if use_pure_llm:
        mode_name = "Pure LLM (No KG)"
    elif use_nonllm_paths:
        mode_name = "EPERM System (Non-LLM Paths)"
    else:
        mode_name = "EPERM System (LLM Paths)"
    print("\n" + "="*70)
    print(f"{mode_name} - WebQSP Integration Test")
    print("="*70)
    
    # Initialize tracking
    tracker = RealTimeAccuracyTracker()
    
    # Handle checkpoint resumption
    start_idx = 0
    if resume_from_checkpoint:
        print(f"\nResuming from checkpoint: {resume_from_checkpoint}")
        results, metadata = tracker.get_checkpoint_manager().load_checkpoint(resume_from_checkpoint)
        tracker.results = results
        start_idx = len(results)
        print(f"✓ Loaded {start_idx} previous results")
        print(f"  Current accuracy: {tracker.get_stats()['accuracy']:.1f}%")
    
    # Load WebQSP data
    print("\nStep 1: Loading WebQSP data...")
    loader = WebQSPLoader()
    qa_dataset = loader.create_qa_dataset(
        "data/webqsp/test_simple.json",
        num_samples=num_samples,
        max_kg_size=max_kg_size if not use_pure_llm else 0  # No KG needed for pure LLM
    )
    print(f"✓ Loaded {len(qa_dataset)} samples")
    
    # Initialize LLM client and path finder
    llm_client = None
    path_finder = None
    
    if use_pure_llm:
        print("\nInitializing LLM client for pure LLM mode...")
        llm_client = LLMClient()
        print("✓ LLM client ready")
    elif use_nonllm_paths:
        print("\nInitializing non-LLM evidence path finder...")
        path_finder = NonLLMEvidencePathFinder()
        print("✓ Non-LLM path finder ready")
        print("Initializing LLM client for answer generation...")
        llm_client = LLMClient()
        print("✓ LLM client ready")
    else:
        print("\nInitializing LLM-based evidence path finder...")
        llm_client = LLMClient()
        print("✓ LLM client ready")
    
    # Initialize batch processor if batch_size > 1
    batch_processor = None
    if batch_size > 1 and not use_pure_llm:
        batch_processor = BatchInferenceProcessor(batch_size=batch_size, verbose=True)
        print(f"\n✓ Batch processing enabled (batch_size={batch_size})")
    
    # Test each sample with EPERM or pure LLM
    results = tracker.results  # Use tracker's results list
    
    # If using batch processing, process in batches
    if batch_processor and not use_pure_llm:
        print("\n" + "="*70)
        print("Processing samples in batches...")
        print("="*70)
        
        for batch_start_idx in range(0, len(qa_dataset), batch_size):
            batch_end_idx = min(batch_start_idx + batch_size, len(qa_dataset))
            qa_batch = qa_dataset[batch_start_idx:batch_end_idx]
            
            try:
                system = EPERMSystem()
                
                # Process batch
                batch_results, batch_metrics = batch_processor.process_batch(
                    qa_batch,
                    system,
                    llm_client,
                    _flexible_match,
                    _normalize_text
                )
                
                # Convert BatchResult to tracker results format
                for batch_result in batch_results:
                    tracker.add_result({
                        'question': batch_result.question,
                        'gold_answers': batch_result.gold_answers,
                        'predicted_answer': batch_result.predicted_answer,
                        'confidence': batch_result.confidence,
                        'correct': batch_result.correct,
                        'time': batch_result.processing_time,
                        'num_evidence_paths': batch_result.num_evidence_paths,
                        'error': batch_result.error
                    })
                
                # Update sample count
                sample_num = start_idx + batch_end_idx
                
                # Show progress
                current_result = {
                    'question': batch_results[-1].question,
                    'predicted_answer': batch_results[-1].predicted_answer,
                    'correct': batch_results[-1].correct
                }
                tracker.print_progress(sample_num, start_idx + len(qa_dataset), current_result)
                
                # Checkpoint if needed
                if checkpoint_interval:
                    tracker.checkpoint_results(checkpoint_interval)
                    
            except Exception as e:
                print(f"\n✗ Error processing batch: {e}")
                import traceback
                traceback.print_exc()
                
                # Skip this batch and continue
                continue
        
        # Print batch statistics
        batch_processor.print_batch_statistics()
    
    # Single-item processing (for pure LLM or small batches)
    else:
        for i, qa_item in enumerate(qa_dataset, 1):
            sample_num = start_idx + i  # Adjust for resumed checkpoints
            print(f"\n{'='*70}")
            print(f"Test {i}/{len(qa_dataset)}")
            print(f"{'='*70}")
            print(f"ID: {qa_item['id']}")
            print(f"Question: {qa_item['question']}")
            print(f"Gold Answers: {', '.join(qa_item['answers'])}")
            if not use_pure_llm:
                print(f"KG Size: {qa_item['kg_stats']['num_entities']} entities, "
                      f"{qa_item['kg_stats']['num_relations']} relations")
            
            try:
                start_time = time.time()
                
                if use_pure_llm:
                    # Pure LLM mode - no KG paths
                    print("\nRunning pure LLM (no KG)...")
                    answer_text, confidence, reasoning = test_pure_llm(
                        qa_item['question'],
                        llm_client
                    )
                    
                    elapsed_time = time.time() - start_time
                    
                    # Check if answer matches
                    correct = _flexible_match(answer_text, qa_item['answers'])
                    
                    print(f"\n{'='*70}")
                    print(f"RESULT:")
                    print(f"  Predicted: {answer_text}")
                    print(f"  Confidence: {confidence:.3f}")
                    print(f"  Gold: {', '.join(qa_item['answers'])}")
                    print(f"  Match: {'✓ CORRECT' if correct else '✗ INCORRECT'}")
                    print(f"  Time: {elapsed_time:.2f}s")
                    
                    result = {
                        'question': qa_item['question'],
                        'gold_answers': qa_item['answers'],
                        'predicted_answer': answer_text,
                        'confidence': confidence,
                        'correct': correct,
                        'time': elapsed_time,
                        'num_evidence_paths': 0  # No paths in pure LLM mode
                    }
                    tracker.add_result(result)
                    
                else:
                    # EPERM mode with KG paths
                    # Initialize EPERM with this sample's KG
                    system = EPERMSystem()
                    system.kg = qa_item['kg']
                    system.retriever = None  # Skip retrieval, use full KG
                    
                    # For WebQSP, we already have the subgraph, so we can directly
                    # use the evidence path finder and answer predictor
                    print("\nRunning EPERM pipeline...")
                    
                    # Find evidence paths (using non-LLM or LLM path finder)
                    if use_nonllm_paths:
                        print("  Finding paths (non-LLM)...")
                        evidence_paths = path_finder.find_evidence_paths(
                            qa_item['question'],
                            qa_item['kg']
                        )
                    else:
                        print("  Finding paths (LLM-based)...")
                        evidence_paths = system.path_finder.find_evidence_paths(
                            qa_item['question'],
                            qa_item['kg']
                        )
                    
                    if not evidence_paths:
                        print("  ⚠ No evidence paths found, using LLM fallback...")
                        
                        # Fallback: use pure LLM prediction
                        answer_text, confidence, reasoning = test_pure_llm(
                            qa_item['question'],
                            llm_client
                        )
                        
                        elapsed_time = time.time() - start_time
                        correct = _flexible_match(answer_text, qa_item['answers'])
                        
                        print(f"\n{'='*70}")
                        print(f"RESULT (LLM Fallback):")
                        print(f"  Predicted: {answer_text}")
                        print(f"  Confidence: {confidence:.3f}")
                        print(f"  Gold: {', '.join(qa_item['answers'])}")
                        print(f"  Match: {'✓ CORRECT' if correct else '✗ INCORRECT'}")
                        print(f"  Time: {elapsed_time:.2f}s")
                        print(f"  Evidence Paths: 0 (used LLM fallback)")
                        
                        result = {
                            'question': qa_item['question'],
                            'gold_answers': qa_item['answers'],
                            'predicted_answer': answer_text,
                            'confidence': confidence,
                            'correct': correct,
                            'time': elapsed_time,
                            'num_evidence_paths': 0,
                            'used_fallback': True
                        }
                        tracker.add_result(result)
                        
                        # Show real-time progress
                        tracker.print_progress(sample_num, start_idx + len(qa_dataset), result)
                        
                        # Checkpoint if needed
                        if checkpoint_interval:
                            tracker.checkpoint_results(checkpoint_interval)
                        
                        continue
                    
                    # Predict answer
                    answer = system.answer_predictor.predict(
                        qa_item['question'],
                        evidence_paths,
                        qa_item['kg']
                    )
                    
                    elapsed_time = time.time() - start_time
                    
                    # Check if answer matches any gold answer (flexible matching)
                    correct = _flexible_match(answer.answer, qa_item['answers'])
                    
                    print(f"\n{'='*70}")
                    print(f"RESULT:")
                    print(f"  Predicted: {answer.answer}")
                    print(f"  Confidence: {answer.confidence:.3f}")
                    print(f"  Gold: {', '.join(qa_item['answers'])}")
                    print(f"  Match: {'✓ CORRECT' if correct else '✗ INCORRECT'}")
                    print(f"  Time: {elapsed_time:.2f}s")
                    print(f"  Evidence Paths: {len(answer.supporting_paths)}")
                    
                    if answer.supporting_paths and len(answer.supporting_paths) > 0:
                        print(f"\n  Top Evidence Path:")
                        top_path = answer.supporting_paths[0]
                        print(f"    {top_path.to_text(qa_item['kg'])}")
                        print(f"    Score: {top_path.score:.3f}")
                    
                    result = {
                        'question': qa_item['question'],
                        'gold_answers': qa_item['answers'],
                        'predicted_answer': answer.answer,
                        'confidence': answer.confidence,
                        'correct': correct,
                        'time': elapsed_time,
                        'num_evidence_paths': len(answer.supporting_paths)
                    }
                    tracker.add_result(result)
                
                # Show real-time progress
                tracker.print_progress(sample_num, start_idx + len(qa_dataset), result)
                
                # Checkpoint if needed
                if checkpoint_interval:
                    tracker.checkpoint_results(checkpoint_interval)
                
            except Exception as e:
                print(f"\n✗ Error processing sample: {e}")
                import traceback
                traceback.print_exc()
                
                result = {
                    'question': qa_item['question'],
                'gold_answers': qa_item['answers'],
                'predicted_answer': "ERROR",
                'confidence': 0.0,
                'correct': False,
                'time': 0.0,
                'error': str(e)
            }
            tracker.add_result(result)
            
            # Show real-time progress even on error
            tracker.print_progress(sample_num, start_idx + len(qa_dataset), result)
            
            # Checkpoint if needed
            if checkpoint_interval:
                tracker.checkpoint_results(checkpoint_interval)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    results = tracker.results
    total = len(results)
    correct = sum(1 for r in results if r['correct'])
    avg_confidence = sum(r['confidence'] for r in results) / total if total > 0 else 0
    avg_time = sum(r['time'] for r in results) / total if total > 0 else 0
    
    print(f"Total Questions: {total}")
    print(f"Correct Answers: {correct}")
    print(f"Accuracy: {correct/total*100:.1f}%" if total > 0 else "N/A")
    print(f"Avg Confidence: {avg_confidence:.3f}")
    print(f"Avg Time: {avg_time:.2f}s")
    
    print("\n" + "="*70)
    print("Detailed Results:")
    print("="*70)
    for i, r in enumerate(results, 1):
        status = "✓" if r['correct'] else "✗"
        print(f"{i}. {status} Q: {r['question'][:50]}...")
        print(f"   Gold: {', '.join(r['gold_answers'])}")
        print(f"   Pred: {r['predicted_answer']} (conf: {r['confidence']:.2f})")
    
    # Save final results
    print("\n" + "="*70)
    print("Saving Final Results...")
    print("="*70)
    summary = summarize_test_results(results, output_file="test_results/webqsp_summary.json")
    
    return results, tracker


def summarize_test_results(results: list, output_file: str = None) -> dict:
    """
    Generate comprehensive summary statistics from test results.
    
    Args:
        results: List of result dictionaries from test_eperm_with_webqsp
        output_file: Optional file path to save results as JSON
        
    Returns:
        Dictionary containing summary statistics
    """
    if not results:
        print("No results to summarize")
        return {}
    
    # Extract key metrics
    total = len(results)
    correct = sum(1 for r in results if r['correct'])
    incorrect = total - correct
    errors = sum(1 for r in results if 'error' in r)
    
    # Time statistics
    times = [r['time'] for r in results if r['time'] > 0]
    
    # Confidence statistics
    confidences = [r['confidence'] for r in results]
    confidences_correct = [r['confidence'] for r in results if r['correct']]
    confidences_incorrect = [r['confidence'] for r in results if not r['correct']]
    
    # Evidence path statistics
    evidence_counts = [r.get('num_evidence_paths', 0) for r in results if 'num_evidence_paths' in r]
    
    # Build summary dictionary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_questions': total,
        'correct_answers': correct,
        'incorrect_answers': incorrect,
        'errors': errors,
        'accuracy': correct / total * 100 if total > 0 else 0,
        'accuracy_without_errors': correct / (total - errors) * 100 if (total - errors) > 0 else 0,
        'timing': {
            'total_time': sum(times),
            'avg_time': mean(times) if times else 0,
            'min_time': min(times) if times else 0,
            'max_time': max(times) if times else 0,
            'std_dev_time': stdev(times) if len(times) > 1 else 0,
            'median_time': median(times) if times else 0,
        },
        'confidence': {
            'avg_all': mean(confidences) if confidences else 0,
            'avg_correct': mean(confidences_correct) if confidences_correct else 0,
            'avg_incorrect': mean(confidences_incorrect) if confidences_incorrect else 0,
            'min_confidence': min(confidences) if confidences else 0,
            'max_confidence': max(confidences) if confidences else 0,
            'std_dev_confidence': stdev(confidences) if len(confidences) > 1 else 0,
        },
        'evidence_paths': {
            'avg_count': mean(evidence_counts) if evidence_counts else 0,
            'min_count': min(evidence_counts) if evidence_counts else 0,
            'max_count': max(evidence_counts) if evidence_counts else 0,
        }
    }
    
    # Print formatted summary
    print("\n" + "="*70)
    print("COMPREHENSIVE TEST RESULTS SUMMARY")
    print("="*70)
    print(f"Timestamp: {summary['timestamp']}")
    
    print("\n--- ACCURACY ---")
    print(f"Total Questions: {summary['total_questions']}")
    print(f"Correct: {summary['correct_answers']}")
    print(f"Incorrect: {summary['incorrect_answers']}")
    print(f"Errors: {summary['errors']}")
    print(f"Overall Accuracy: {summary['accuracy']:.2f}%")
    if summary['errors'] > 0:
        print(f"Accuracy (excluding errors): {summary['accuracy_without_errors']:.2f}%")
    
    print("\n--- TIMING STATISTICS ---")
    print(f"Total Time: {summary['timing']['total_time']:.2f}s")
    print(f"Average Time: {summary['timing']['avg_time']:.2f}s")
    print(f"Median Time: {summary['timing']['median_time']:.2f}s")
    print(f"Min Time: {summary['timing']['min_time']:.2f}s")
    print(f"Max Time: {summary['timing']['max_time']:.2f}s")
    if summary['timing']['std_dev_time'] > 0:
        print(f"Std Dev: {summary['timing']['std_dev_time']:.2f}s")
    
    print("\n--- CONFIDENCE STATISTICS ---")
    print(f"Average Confidence (all): {summary['confidence']['avg_all']:.3f}")
    print(f"Average Confidence (correct): {summary['confidence']['avg_correct']:.3f}")
    print(f"Average Confidence (incorrect): {summary['confidence']['avg_incorrect']:.3f}")
    print(f"Min Confidence: {summary['confidence']['min_confidence']:.3f}")
    print(f"Max Confidence: {summary['confidence']['max_confidence']:.3f}")
    if summary['confidence']['std_dev_confidence'] > 0:
        print(f"Std Dev: {summary['confidence']['std_dev_confidence']:.3f}")
    
    print("\n--- EVIDENCE PATH STATISTICS ---")
    print(f"Average Evidence Paths: {summary['evidence_paths']['avg_count']:.1f}")
    print(f"Min Evidence Paths: {summary['evidence_paths']['min_count']}")
    print(f"Max Evidence Paths: {summary['evidence_paths']['max_count']}")
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump({
                'summary': summary,
                'detailed_results': results
            }, f, indent=2)
        print(f"\n✓ Results saved to {output_file}")
    
    print("\n" + "="*70)
    
    return summary


def test_single_sample_detailed():
    """Test a single sample with detailed output."""
    print("\n" + "="*70)
    print("Detailed Single Sample Test")
    print("="*70)
    
    # Load one sample
    loader = WebQSPLoader()
    qa_dataset = loader.create_qa_dataset(
        "data/webqsp/train_simple.json",
        num_samples=1,
        max_kg_size=15000000  # Smaller for detailed analysis
    )
    
    qa_item = qa_dataset[0]
    
    print(f"\nQuestion: {qa_item['question']}")
    print(f"Gold Answer: {', '.join(qa_item['answers'])}")
    print(f"\nKG Statistics:")
    for key, value in qa_item['kg_stats'].items():
        print(f"  {key}: {value}")
    
    print(f"\nSample Triples from KG:")
    kg = qa_item['kg']
    for i, relation in enumerate(kg.relations[:10]):
        head_name = kg.entities[relation.head].name
        tail_name = kg.entities[relation.tail].name
        rel_name = relation.relation.split('.')[-1]  # Show last part
        print(f"  {i+1}. {head_name} --[{rel_name}]--> {tail_name}")
    
    # Run EPERM
    print(f"\n{'='*70}")
    print("Running EPERM...")
    print(f"{'='*70}")
    
    system = EPERMSystem()
    system.kg = qa_item['kg']
    
    evidence_paths = system.path_finder.find_evidence_paths(
        qa_item['question'],
        qa_item['kg']
    )
    
    if evidence_paths:
        print(f"\nFound {len(evidence_paths)} evidence paths")
        print("\nTop 3 Evidence Paths:")
        for i, path in enumerate(evidence_paths[:3], 1):
            print(f"\n{i}. Score: {path.score:.3f}")
            print(f"   Path: {path.to_text(qa_item['kg'])}")
            if path.reasoning:
                print(f"   Reasoning: {path.reasoning}")
    
    answer = system.answer_predictor.predict(
        qa_item['question'],
        evidence_paths,
        qa_item['kg']
    )
    
    print(f"\n{'='*70}")
    print("Final Answer:")
    print(f"{'='*70}")
    print(f"Answer: {answer.answer}")
    print(f"Confidence: {answer.confidence:.3f}")
    print(f"Reasoning: {answer.reasoning}")


if __name__ == "__main__":
    import sys
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test EPERM or Pure LLM on WebQSP")
    parser.add_argument('--mode', type=str, default='eperm', choices=['eperm', 'pure-llm', 'nonllm', 'both'],
                        help='Test mode: eperm (LLM paths), pure-llm (no KG), nonllm (non-LLM paths), or both')
    parser.add_argument('--num_samples', type=int, default=20000,
                        help='Number of samples to test')
    parser.add_argument('--max_kg_size', type=int, default=100,
                        help='Maximum KG size (triples)')
    parser.add_argument('--checkpoint_interval', type=int, default=100,
                        help='Checkpoint interval (0 = no checkpointing)')
    parser.add_argument('--resume', type=str, default=None,
                        help='Resume from checkpoint file')
    parser.add_argument('--batch_size', type=int, default=1,
                        help='Batch size for inference (1 = no batching, >1 = parallel inference)')
    parser.add_argument('--use-nonllm-paths', action='store_true',
                        help='Use non-LLM evidence path finder')
    parser.add_argument('--enable-batching', action='store_true',
                        help='Force enable batch processing even with batch_size=1')
    parser.add_argument('--batch_benchmark', action='store_true',
                        help='Run batch size benchmark (tests 1, 2, 4, 8, 16)')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("WebQSP-EPERM Integration Test Suite")
    print("="*70)
    print(f"Mode: {args.mode}")
    print(f"Samples: {args.num_samples}")
    print(f"Max KG size: {args.max_kg_size}")
    print(f"Batch size: {args.batch_size}")
    print(f"Use non-LLM paths: {args.use_nonllm_paths}")
    print(f"Enable batching: {args.enable_batching}")
    print(f"Checkpoint interval: {args.checkpoint_interval if args.checkpoint_interval > 0 else 'disabled'}")
    
    if args.batch_benchmark:
        print(f"Batch size benchmark: Enabled (will test multiple batch sizes)")
    
    try:
        # Test 1: Single sample detailed
        # print("\n\nTEST 1: Single Sample (Detailed)")
        # test_single_sample_detailed()
        
        checkpoint_interval = args.checkpoint_interval if args.checkpoint_interval > 0 else None
        
        # Handle batch size benchmark mode
        if args.batch_benchmark:
            print("\n\n" + "="*70)
            print("BATCH SIZE BENCHMARK")
            print("="*70)
            
            batch_sizes = [1, 2, 4, 8, 16]
            benchmark_results = {}
            
            for batch_size in batch_sizes:
                print(f"\n>>> Testing batch_size={batch_size}")
                try:
                    results, tracker = test_eperm_with_webqsp(
                        num_samples=args.num_samples,
                        max_kg_size=args.max_kg_size,
                        checkpoint_interval=None,  # No checkpointing during benchmark
                        resume_from_checkpoint=None,
                        use_pure_llm=False,
                        batch_size=batch_size,
                        use_nonllm_paths=args.use_nonllm_paths
                    )
                    
                    stats = tracker.get_stats()
                    benchmark_results[batch_size] = {
                        'accuracy': (sum(1 for r in results if r['correct']) / len(results) * 100) if results else 0,
                        'avg_time': stats['avg_time'],
                        'items_per_second': len(results) / stats['elapsed_time'] if stats['elapsed_time'] > 0 else 0,
                        'total_time': stats['elapsed_time']
                    }
                    
                except Exception as e:
                    print(f"  Error: {e}")
                    benchmark_results[batch_size] = {'error': str(e)}
            
            # Print benchmark summary
            print("\n\n" + "="*70)
            print("BENCHMARK SUMMARY")
            print("="*70)
            print(f"\n{'Batch Size':<12} {'Accuracy':<12} {'Avg Time':<12} {'Items/sec':<12} {'Total Time':<12}")
            print("-" * 60)
            for batch_size in batch_sizes:
                if batch_size in benchmark_results:
                    r = benchmark_results[batch_size]
                    if 'error' not in r:
                        print(f"{batch_size:<12} {r['accuracy']:>10.1f}% {r['avg_time']:>10.2f}s "
                              f"{r['items_per_second']:>10.2f} {r['total_time']:>10.2f}s")
                    else:
                        print(f"{batch_size:<12} ERROR: {r['error']}")
            print("="*70)
            sys.exit(0)
        
        if args.mode == 'both':
            # Run both modes for comparison
            print("\n\n" + "="*70)
            print("COMPARISON MODE: Pure LLM vs LLM Paths vs Non-LLM Paths")
            print("="*70)
            
            print("\n>>> PHASE 1: Pure LLM (No KG) <<<")
            results_llm, tracker_llm = test_eperm_with_webqsp(
                num_samples=args.num_samples,
                max_kg_size=args.max_kg_size,
                checkpoint_interval=checkpoint_interval,
                resume_from_checkpoint=args.resume,
                use_pure_llm=True
            )
            
            print("\n>>> PHASE 2: EPERM (LLM Paths) <<<")
            results_eperm, tracker_eperm = test_eperm_with_webqsp(
                num_samples=args.num_samples,
                max_kg_size=args.max_kg_size,
                checkpoint_interval=checkpoint_interval,
                resume_from_checkpoint=None,
                use_pure_llm=False,
                use_nonllm_paths=False
            )
            
            print("\n>>> PHASE 3: EPERM (Non-LLM Paths) <<<")
            results_nonllm, tracker_nonllm = test_eperm_with_webqsp(
                num_samples=args.num_samples,
                max_kg_size=args.max_kg_size,
                checkpoint_interval=checkpoint_interval,
                resume_from_checkpoint=None,
                use_pure_llm=False,
                use_nonllm_paths=True
            )
            
            # Compare results
            print("\n\n" + "="*70)
            print("COMPARISON SUMMARY: All Three Modes")
            print("="*70)
            
            stats_llm = tracker_llm.get_stats()
            stats_eperm = tracker_eperm.get_stats()
            stats_nonllm = tracker_nonllm.get_stats()
            
            print(f"\n{'Metric':<25} {'Pure LLM':<15} {'LLM Paths':<15} {'Non-LLM Paths':<15}")
            print("-" * 70)
            print(f"{'Accuracy':<25} {stats_llm['accuracy']:>6.2f}% {stats_eperm['accuracy']:>12.2f}% {stats_nonllm['accuracy']:>14.2f}%")
            print(f"{'Avg Confidence':<25} {stats_llm['avg_confidence']:>6.3f} {stats_eperm['avg_confidence']:>17.3f} {stats_nonllm['avg_confidence']:>19.3f}")
            print(f"{'Avg Time/Sample':<25} {stats_llm['avg_time']:>6.2f}s {stats_eperm['avg_time']:>16.2f}s {stats_nonllm['avg_time']:>19.2f}s")
            
            results = results_nonllm
            tracker = tracker_nonllm
            
        elif args.mode == 'pure-llm':
            # Pure LLM mode
            print("\n\n" + "="*70)
            print("TEST: Pure LLM (No KG) Mode")
            print("="*70)
            
            results, tracker = test_eperm_with_webqsp(
                num_samples=args.num_samples,
                max_kg_size=args.max_kg_size,
                checkpoint_interval=checkpoint_interval,
                resume_from_checkpoint=args.resume,
                use_pure_llm=True
            )
            
        elif args.mode == 'nonllm':
            # Non-LLM paths mode
            print("\n\n" + "="*70)
            print("TEST: EPERM (Non-LLM Paths) Mode")
            print("="*70)
            
            results, tracker = test_eperm_with_webqsp(
                num_samples=args.num_samples,
                max_kg_size=args.max_kg_size,
                checkpoint_interval=checkpoint_interval,
                resume_from_checkpoint=args.resume,
                use_pure_llm=False,
                use_nonllm_paths=True,
                batch_size=args.batch_size
            )
            
        else:
            # EPERM mode with LLM paths (default)
            path_type = "Non-LLM Paths" if args.use_nonllm_paths else "LLM Paths"
            print("\n\n" + "="*70)
            print(f"TEST: EPERM ({path_type}) Mode")
            print("="*70)
            
            results, tracker = test_eperm_with_webqsp(
                num_samples=args.num_samples,
                max_kg_size=args.max_kg_size,
                checkpoint_interval=checkpoint_interval,
                resume_from_checkpoint=args.resume,
                use_pure_llm=False,
                use_nonllm_paths=args.use_nonllm_paths,
                batch_size=args.batch_size
            )
        
        # Analyze matching results
        analyze_matching_results(results, show_mismatches=True)
        
        # Get checkpoint manager for reference
        checkpoint_mgr = tracker.get_checkpoint_manager()
        print("\n" + "="*70)
        print("CHECKPOINTS SAVED")
        print("="*70)
        saved_checkpoints = checkpoint_mgr.list_checkpoints()
        for i, checkpoint in enumerate(saved_checkpoints[:5], 1):  # Show first 5
            print(f"{i}. {checkpoint}")
        
        if len(saved_checkpoints) > 5:
            print(f"... and {len(saved_checkpoints) - 5} more")
        
        # Example: How to resume from checkpoint
        print("\n" + "="*70)
        print("TO RESUME FROM CHECKPOINT:")
        print("="*70)
        if saved_checkpoints:
            latest = checkpoint_mgr.get_latest_checkpoint()
            print(f"results, tracker = test_eperm_with_webqsp(")
            print(f"    num_samples=20000,")
            print(f"    max_kg_size=100,")
            print(f"    checkpoint_interval=100,")
            print(f"    resume_from_checkpoint='{latest}'")
            print(f")")
        
        print("\n" + "="*70)
        print("✓ All tests completed!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        print("Progress has been saved in checkpoints - you can resume later")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
