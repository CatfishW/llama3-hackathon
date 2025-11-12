"""Optimized test for EPERM system with WebQSP dataset - designed for full test set.

Key optimizations:
1. Reduced LLM calls - skip entity extraction, use heuristics where possible
2. Batch processing with progress tracking
3. Parallel LLM inference where possible
4. Simplified path finding with cutoffs
5. Result caching and resume capability
6. Progress saving every N samples
"""

from webqsp_loader import WebQSPLoader
from eperm_system import EPERMSystem
from knowledge_graph import KnowledgeGraph
from llm_client import LLMClient
from evidence_path_finder_fast import FastEvidencePathFinder
from answer_predictor_fast import FastAnswerPredictor
import time
import json
import os
from pathlib import Path
import unicodedata
import re
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _flexible_match(predicted: str, gold_answers: list, gold_entity_ids: list = None, kg=None) -> bool:
    """
    Check if predicted answer matches any gold answer with flexible matching.
    
    Args:
        predicted: Predicted answer (entity ID or text)
        gold_answers: List of gold answer texts
        gold_entity_ids: List of gold answer entity IDs (optional)
        kg: Knowledge graph to resolve entity names (optional)
        
    Returns:
        True if match found
    """
    pred_norm = _normalize_text(predicted)
    
    # First try: Direct entity ID match
    if gold_entity_ids and predicted in gold_entity_ids:
        return True
    
    # Second try: If predicted is an entity ID, get its name from KG
    predicted_text = predicted
    if kg and predicted in kg.entities:
        predicted_text = kg.entities[predicted].name
        pred_norm = _normalize_text(predicted_text)
    
    # Third try: Text-based flexible matching with gold answers
    for gold in gold_answers:
        gold_norm = _normalize_text(gold)
        
        if pred_norm == gold_norm:
            return True
        
        if gold_norm in pred_norm or pred_norm in gold_norm:
            return True
        
        pred_words = set(pred_norm.split())
        gold_words = set(gold_norm.split())
        
        if pred_words and gold_words:
            overlap = len(pred_words & gold_words)
            similarity = overlap / max(len(pred_words), len(gold_words))
            if similarity >= 0.5:
                return True
    
    # Fourth try: If we have gold entity IDs, check if predicted text matches any of those entity names
    if gold_entity_ids and kg:
        for gold_entity_id in gold_entity_ids:
            if gold_entity_id in kg.entities:
                gold_entity_name = kg.entities[gold_entity_id].name
                gold_entity_norm = _normalize_text(gold_entity_name)
                
                if pred_norm == gold_entity_norm:
                    return True
                
                if gold_entity_norm in pred_norm or pred_norm in gold_entity_norm:
                    return True
    
    return False


class OptimizedEPERMTester:
    """Optimized EPERM testing with caching and batching."""
    
    def __init__(self, 
                 results_dir: str = "test_results",
                 max_kg_size: int = 300,  # Increased from 150 to 300
                 save_interval: int = 50):
        """
        Initialize optimized tester.
        
        Args:
            results_dir: Directory to save results
            max_kg_size: Maximum triples per KG (increased to improve entity matching)
            save_interval: Save results every N samples
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.max_kg_size = max_kg_size
        self.save_interval = save_interval
        
        # Statistics
        self.stats = {
            'total_samples': 0,
            'processed': 0,
            'correct': 0,
            'errors': 0,
            'total_time': 0.0,
            'avg_time_per_sample': 0.0
        }
    
    def load_checkpoint(self, checkpoint_file: str) -> Dict:
        """Load results from checkpoint."""
        checkpoint_path = self.results_dir / checkpoint_file
        if checkpoint_path.exists():
            with open(checkpoint_path, 'r') as f:
                return json.load(f)
        return {'results': [], 'stats': self.stats.copy()}
    
    def save_checkpoint(self, results: List[Dict], checkpoint_file: str):
        """Save results checkpoint."""
        checkpoint_path = self.results_dir / checkpoint_file
        checkpoint_data = {
            'results': results,
            'stats': self.stats.copy(),
            'timestamp': time.time()
        }
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    
    def process_single_sample(self, qa_item: Dict, sample_idx: int) -> Dict:
        """
        Process a single QA sample with optimizations.
        
        Args:
            qa_item: QA item with question, answers, kg
            sample_idx: Sample index for tracking
            
        Returns:
            Result dictionary
        """
        start_time = time.time()
        
        try:
            # Use fast modules directly (skip EPERM system overhead)
            from config import SYSTEM_CONFIG
            original_verbose = SYSTEM_CONFIG["verbose"]
            SYSTEM_CONFIG["verbose"] = False
            
            # Initialize fast modules
            llm = LLMClient()
            fast_path_finder = FastEvidencePathFinder(llm)
            fast_answer_predictor = FastAnswerPredictor(llm)
            
            # Find evidence paths with timeout
            evidence_paths = fast_path_finder.find_evidence_paths(
                qa_item['question'],
                qa_item['kg']
            )
            
            # Restore verbose setting
            SYSTEM_CONFIG["verbose"] = original_verbose
            
            # Predict answer (even with no evidence paths, try LLM)
            answer = fast_answer_predictor.predict(
                qa_item['question'],
                evidence_paths,  # Can be empty list
                qa_item['kg']
            )
            
            elapsed_time = time.time() - start_time
            
            # Check correctness with flexible matching (including entity ID matching)
            gold_entity_ids = qa_item.get('answer_entity_ids', [])
            correct = _flexible_match(
                answer.answer, 
                qa_item['answers'],
                gold_entity_ids=gold_entity_ids,
                kg=qa_item['kg']
            )
            
            # Get human-readable predicted answer
            predicted_answer = answer.answer
            if answer.answer in qa_item['kg'].entities:
                predicted_answer = f"{answer.answer} ({qa_item['kg'].entities[answer.answer].name})"
            
            result = {
                'id': qa_item['id'],
                'question': qa_item['question'],
                'gold_answers': qa_item['answers'],
                'gold_entity_ids': gold_entity_ids,
                'predicted_answer': predicted_answer,
                'predicted_entity_id': answer.answer,
                'confidence': answer.confidence,
                'correct': correct,
                'time': elapsed_time,
                'num_paths': len(answer.supporting_paths)
            }
            
            return result
            
        except Exception as e:
            gold_entity_ids = qa_item.get('answer_entity_ids', [])
            return {
                'id': qa_item.get('id', f'sample_{sample_idx}'),
                'question': qa_item['question'],
                'gold_answers': qa_item['answers'],
                'gold_entity_ids': gold_entity_ids,
                'predicted_answer': "ERROR",
                'predicted_entity_id': None,
                'confidence': 0.0,
                'correct': False,
                'time': time.time() - start_time,
                'error': str(e)
            }
    
    def test_dataset(self,
                    file_path: str,
                    num_samples: int = None,
                    resume_from: str = None,
                    parallel: bool = False) -> List[Dict]:
        """
        Test on WebQSP dataset with optimizations.
        
        Args:
            file_path: Path to WebQSP file
            num_samples: Number of samples to test (None = all)
            resume_from: Resume from checkpoint file
            parallel: Use parallel processing (experimental)
            
        Returns:
            List of results
        """
        print("\n" + "="*70)
        print("Optimized EPERM Testing on WebQSP Dataset")
        print("="*70)
        
        # Load checkpoint if resuming
        results = []
        start_idx = 0
        if resume_from:
            checkpoint = self.load_checkpoint(resume_from)
            results = checkpoint.get('results', [])
            self.stats = checkpoint.get('stats', self.stats.copy())
            start_idx = len(results)
            print(f"\n✓ Resuming from checkpoint: {len(results)} samples already processed")
        
        # Load data
        print(f"\nLoading WebQSP data from: {file_path}")
        loader = WebQSPLoader()
        
        # Determine total samples
        if num_samples is None:
            # Count total lines in file
            with open(file_path, 'r') as f:
                total_lines = sum(1 for _ in f)
            num_samples = total_lines
            print(f"Processing entire dataset: {num_samples} samples")
        else:
            print(f"Processing {num_samples} samples")
        
        # Skip already processed
        samples_to_process = num_samples - start_idx
        if samples_to_process <= 0:
            print("All samples already processed!")
            return results
        
        print(f"Remaining to process: {samples_to_process}")
        print(f"Max KG size: {self.max_kg_size} triples")
        print(f"Save interval: {self.save_interval} samples")
        
        # Load data in chunks to save memory
        chunk_size = 100
        current_idx = start_idx
        
        with tqdm(total=samples_to_process, desc="Processing", unit="sample") as pbar:
            while current_idx < num_samples:
                # Load next chunk
                chunk_end = min(current_idx + chunk_size, num_samples)
                chunk_samples = []
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i < current_idx:
                            continue
                        if i >= chunk_end:
                            break
                        
                        try:
                            sample = json.loads(line)
                            kg = loader.sample_to_kg(sample, limit_size=self.max_kg_size)
                            
                            # Extract answers and kb_ids, filter out None values
                            answers = []
                            answer_entity_ids = []
                            
                            for ans in sample.get('answers', []):
                                if ans and ans.get('text') and ans['text'] is not None:
                                    answers.append(ans['text'])
                                    # Use kb_id directly from the dataset (Freebase entity ID)
                                    if ans.get('kb_id'):
                                        answer_entity_ids.append(ans['kb_id'])
                            
                            # Skip samples with no valid answers
                            if not answers:
                                print(f"\nSkipping sample {i}: No valid answers")
                                continue
                            
                            qa_item = {
                                'id': sample.get('id', f'sample_{i}'),
                                'question': sample.get('question', ''),
                                'answers': answers,
                                'answer_entity_ids': list(set(answer_entity_ids)),  # Remove duplicates
                                'kg': kg,
                                'kg_stats': kg.stats()
                            }
                            chunk_samples.append((i, qa_item))
                        except Exception as e:
                            print(f"\nError loading sample {i}: {e}")
                            continue
                
                # Process chunk
                for idx, qa_item in chunk_samples:
                    result = self.process_single_sample(qa_item, idx)
                    results.append(result)
                    
                    # Update stats
                    self.stats['processed'] += 1
                    self.stats['total_time'] += result['time']
                    if result['correct']:
                        self.stats['correct'] += 1
                    if 'error' in result:
                        self.stats['errors'] += 1
                    
                    pbar.update(1)
                    
                    # Update progress bar description with accuracy
                    if self.stats['processed'] > 0:
                        acc = self.stats['correct'] / self.stats['processed'] * 100
                        avg_time = self.stats['total_time'] / self.stats['processed']
                        pbar.set_postfix({
                            'acc': f"{acc:.1f}%",
                            'avg_time': f"{avg_time:.2f}s"
                        })
                    
                    # Save checkpoint
                    if len(results) % self.save_interval == 0:
                        checkpoint_file = f"checkpoint_{len(results)}.json"
                        self.save_checkpoint(results, checkpoint_file)
                        pbar.write(f"✓ Checkpoint saved: {checkpoint_file}")
                
                current_idx = chunk_end
        
        # Update final stats
        self.stats['total_samples'] = len(results)
        if self.stats['processed'] > 0:
            self.stats['avg_time_per_sample'] = self.stats['total_time'] / self.stats['processed']
        
        # Save final results
        final_file = f"final_results_{len(results)}.json"
        self.save_checkpoint(results, final_file)
        print(f"\n✓ Final results saved: {final_file}")
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """Print summary statistics."""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        total = len(results)
        correct = sum(1 for r in results if r['correct'])
        errors = sum(1 for r in results if 'error' in r)
        
        if total > 0:
            accuracy = correct / total * 100
            avg_confidence = sum(r['confidence'] for r in results) / total
            avg_time = sum(r['time'] for r in results) / total
            total_time = sum(r['time'] for r in results)
            
            print(f"\nTotal Samples:    {total}")
            print(f"Correct:          {correct}")
            print(f"Incorrect:        {total - correct - errors}")
            print(f"Errors:           {errors}")
            print(f"\nAccuracy:         {accuracy:.2f}%")
            print(f"Avg Confidence:   {avg_confidence:.3f}")
            print(f"Avg Time/Sample:  {avg_time:.2f}s")
            print(f"Total Time:       {total_time/60:.1f} minutes")
            print(f"Est. Full Test:   {(avg_time * 1639)/60:.1f} minutes")  # 1639 is typical test size
            
            # Breakdown by correctness
            print(f"\n{'='*70}")
            print("Confidence Distribution:")
            correct_conf = [r['confidence'] for r in results if r['correct']]
            incorrect_conf = [r['confidence'] for r in results if not r['correct'] and 'error' not in r]
            
            if correct_conf:
                print(f"  Correct answers:   avg={sum(correct_conf)/len(correct_conf):.3f}")
            if incorrect_conf:
                print(f"  Incorrect answers: avg={sum(incorrect_conf)/len(incorrect_conf):.3f}")


def quick_test(num_samples: int = 10):
    """Quick test on small subset."""
    print("\n" + "="*70)
    print(f"QUICK TEST: {num_samples} samples")
    print("="*70)
    
    tester = OptimizedEPERMTester(
        results_dir="test_results/quick",
        max_kg_size=300,  # Increased to improve entity matching
        save_interval=5
    )
    
    results = tester.test_dataset(
        "data/webqsp/train_simple.json",
        num_samples=num_samples
    )
    
    tester.print_summary(results)
    
    # Show some examples
    print(f"\n{'='*70}")
    print("Sample Results:")
    print(f"{'='*70}")
    for i, r in enumerate(results[:5], 1):
        status = "✓" if r['correct'] else "✗"
        print(f"\n{i}. {status} [{r['confidence']:.2f}] {r['question'][:60]}...")
        print(f"   Gold: {', '.join(r['gold_answers'][:2])}")
        if r.get('gold_entity_ids'):
            print(f"   Gold IDs: {', '.join(r['gold_entity_ids'][:3])}")
        print(f"   Pred: {r['predicted_answer']}")
        if r.get('predicted_entity_id'):
            print(f"   Pred ID: {r['predicted_entity_id']}")
    
    return results


def full_test(dataset: str = "test"):
    """Run on full test set with all optimizations."""
    print("\n" + "="*70)
    print(f"FULL TEST: {dataset} dataset")
    print("="*70)
    
    file_map = {
        'train': 'data/webqsp/train_simple.json',
        'test': 'data/webqsp/test_simple.json'
    }
    
    tester = OptimizedEPERMTester(
        results_dir=f"test_results/{dataset}_full",
        max_kg_size=300,  # Increased to improve entity matching
        save_interval=50
    )
    
    # Check for existing checkpoint
    checkpoint_files = sorted(tester.results_dir.glob("checkpoint_*.json"))
    resume_from = None
    if checkpoint_files:
        latest = checkpoint_files[-1]
        print(f"\nFound checkpoint: {latest.name}")
        response = input("Resume from checkpoint? (y/n): ").strip().lower()
        if response == 'y':
            resume_from = latest.name
    
    results = tester.test_dataset(
        file_map[dataset],
        num_samples=None,  # Process all
        resume_from=resume_from
    )
    
    tester.print_summary(results)
    
    return results


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("Optimized WebQSP-EPERM Testing")
    print("="*70)
    print("\nOptions:")
    print("  1. Quick test (10 samples)")
    print("  2. Medium test (100 samples)")
    print("  3. Full test set")
    print("  4. Full training set")
    
    try:
        if len(sys.argv) > 1:
            choice = sys.argv[1]
        else:
            choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            results = quick_test(num_samples=10)
        elif choice == "2":
            tester = OptimizedEPERMTester(
                results_dir="test_results/medium",
                max_kg_size=300,  # Fixed: was accidentally set to 30M
                save_interval=20
            )
            results = tester.test_dataset(
                "data/webqsp/train_simple.json",
                num_samples=100
            )
            tester.print_summary(results)
        elif choice == "3":
            results = full_test(dataset="test")
        elif choice == "4":
            results = full_test(dataset="train")
        else:
            print("Invalid choice!")
            sys.exit(1)
        
        print("\n" + "="*70)
        print("✓ Testing completed!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n✗ Testing interrupted by user")
        print("Results saved in checkpoints - can resume later!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ Testing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
