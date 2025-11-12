"""Re-evaluate existing checkpoint results with entity ID mapping.

This script takes an existing checkpoint file and re-evaluates the correctness
by mapping gold answers to entity IDs and comparing them properly.
"""

import json
import sys
from pathlib import Path
from webqsp_loader import WebQSPLoader
from knowledge_graph import KnowledgeGraph
import unicodedata
import re


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _flexible_match(predicted: str, gold_answers: list, gold_entity_ids: list = None) -> bool:
    """
    Check if predicted answer matches any gold answer with flexible matching.
    
    Args:
        predicted: Predicted answer (entity ID or text)
        gold_answers: List of gold answer texts
        gold_entity_ids: List of gold answer entity IDs (optional)
        
    Returns:
        True if match found
    """
    pred_norm = _normalize_text(predicted)
    
    # First try: Direct entity ID match
    if gold_entity_ids and predicted in gold_entity_ids:
        return True
    
    # Try to extract entity ID from predicted answer (e.g., "09c7w0 (entity name)")
    predicted_id = predicted.split()[0] if ' ' in predicted else predicted
    if gold_entity_ids and predicted_id in gold_entity_ids:
        return True
    
    # Second try: Text-based flexible matching with gold answers
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
    
    return False


def reevaluate_checkpoint(checkpoint_path: str, dataset_path: str, output_path: str = None):
    """
    Re-evaluate a checkpoint with entity ID mapping.
    
    Args:
        checkpoint_path: Path to checkpoint JSON file
        dataset_path: Path to original WebQSP dataset file
        output_path: Path to save re-evaluated results (optional)
    """
    print(f"\n{'='*70}")
    print("Re-evaluating Checkpoint with Entity ID Mapping")
    print(f"{'='*70}")
    print(f"\nCheckpoint: {checkpoint_path}")
    print(f"Dataset: {dataset_path}")
    
    # Load checkpoint
    with open(checkpoint_path, 'r') as f:
        checkpoint = json.load(f)
    
    results = checkpoint.get('results', [])
    print(f"\nLoaded {len(results)} results from checkpoint")
    
    # Initialize loader
    loader = WebQSPLoader()
    
    # Load dataset samples to rebuild KGs and map entity IDs
    print("Loading dataset samples to map entity IDs...")
    sample_map = {}
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= len(results):
                break
            
            try:
                sample = json.loads(line)
                sample_id = sample.get('id', f'sample_{i}')
                sample_map[sample_id] = sample
            except Exception as e:
                print(f"Error loading sample {i}: {e}")
                continue
    
    print(f"Loaded {len(sample_map)} samples")
    
    # Re-evaluate each result
    print("\nRe-evaluating results...")
    updated_results = []
    original_correct = 0
    new_correct = 0
    changed_count = 0
    
    for result in results:
        sample_id = result['id']
        
        # Keep original result data
        updated_result = result.copy()
        original_correctness = result['correct']
        
        if original_correctness:
            original_correct += 1
        
        # Try to get entity ID mapping
        if sample_id in sample_map:
            try:
                sample = sample_map[sample_id]
                kg = loader.sample_to_kg(sample, limit_size=150)
                
                # Map gold answers to entity IDs
                gold_entity_ids = []
                for answer_text in result['gold_answers']:
                    entity_ids = loader.find_entity_ids_for_answer(answer_text, kg)
                    gold_entity_ids.extend(entity_ids)
                
                gold_entity_ids = list(set(gold_entity_ids))
                
                # Re-evaluate correctness
                predicted_answer = result.get('predicted_answer', '')
                new_correctness = _flexible_match(
                    predicted_answer,
                    result['gold_answers'],
                    gold_entity_ids=gold_entity_ids
                )
                
                # Update result
                updated_result['gold_entity_ids'] = gold_entity_ids
                updated_result['correct'] = new_correctness
                updated_result['original_correct'] = original_correctness
                
                if new_correctness != original_correctness:
                    changed_count += 1
                    updated_result['correctness_changed'] = True
                
                if new_correctness:
                    new_correct += 1
                
            except Exception as e:
                print(f"Error processing {sample_id}: {e}")
                # Keep original result if error
                pass
        
        updated_results.append(updated_result)
    
    # Update checkpoint with new results
    checkpoint['results'] = updated_results
    
    # Update stats
    total = len(updated_results)
    if total > 0:
        original_accuracy = (original_correct / total) * 100
        new_accuracy = (new_correct / total) * 100
        
        checkpoint['stats'] = {
            'total_samples': total,
            'original_correct': original_correct,
            'original_accuracy': original_accuracy,
            'new_correct': new_correct,
            'new_accuracy': new_accuracy,
            'correctness_changed': changed_count,
            'accuracy_improvement': new_accuracy - original_accuracy
        }
    
    # Save updated checkpoint
    if output_path is None:
        output_path = checkpoint_path.replace('.json', '_remapped.json')
    
    with open(output_path, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    # Print summary
    print(f"\n{'='*70}")
    print("Re-evaluation Summary")
    print(f"{'='*70}")
    print(f"\nTotal Samples:           {total}")
    print(f"Original Correct:        {original_correct} ({original_accuracy:.2f}%)")
    print(f"New Correct:             {new_correct} ({new_accuracy:.2f}%)")
    print(f"Correctness Changed:     {changed_count}")
    print(f"Accuracy Improvement:    {new_accuracy - original_accuracy:.2f}%")
    print(f"\nSaved to: {output_path}")
    
    # Show some examples that changed
    print(f"\n{'='*70}")
    print("Examples of Changed Evaluations:")
    print(f"{'='*70}")
    
    changed_examples = [r for r in updated_results if r.get('correctness_changed', False)]
    for i, r in enumerate(changed_examples[:10], 1):
        status = "✗ → ✓" if r['correct'] else "✓ → ✗"
        print(f"\n{i}. {status} [{r.get('confidence', 0.0):.2f}]")
        print(f"   Q: {r['question'][:70]}...")
        print(f"   Gold: {', '.join(r['gold_answers'][:2])}")
        if r.get('gold_entity_ids'):
            print(f"   Gold IDs: {', '.join(r['gold_entity_ids'][:3])}")
        print(f"   Pred: {r['predicted_answer']}")
    
    return checkpoint


def main():
    """Main function."""
    if len(sys.argv) < 3:
        print("\nUsage: python reevaluate_with_entity_mapping.py <checkpoint_file> <dataset_file> [output_file]")
        print("\nExample:")
        print("  python reevaluate_with_entity_mapping.py test_results/test_full/checkpoint_50.json data/webqsp/test_simple.json")
        sys.exit(1)
    
    checkpoint_path = sys.argv[1]
    dataset_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not Path(checkpoint_path).exists():
        print(f"Error: Checkpoint file not found: {checkpoint_path}")
        sys.exit(1)
    
    if not Path(dataset_path).exists():
        print(f"Error: Dataset file not found: {dataset_path}")
        sys.exit(1)
    
    try:
        reevaluate_checkpoint(checkpoint_path, dataset_path, output_path)
        print(f"\n{'='*70}")
        print("✓ Re-evaluation completed successfully!")
        print(f"{'='*70}\n")
    except Exception as e:
        print(f"\n✗ Error during re-evaluation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
