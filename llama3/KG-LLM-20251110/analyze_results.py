"""Utility script to analyze test results from checkpoints."""

import json
import sys
from pathlib import Path
from typing import Dict, List


def load_results(result_file: str) -> Dict:
    """Load results from JSON file."""
    with open(result_file, 'r') as f:
        return json.load(f)


def analyze_results(results_data: Dict):
    """Analyze and print detailed statistics."""
    results = results_data.get('results', [])
    stats = results_data.get('stats', {})
    
    print("\n" + "="*70)
    print("DETAILED RESULTS ANALYSIS")
    print("="*70)
    
    # Basic stats
    total = len(results)
    correct = sum(1 for r in results if r.get('correct', False))
    errors = sum(1 for r in results if 'error' in r)
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Total Samples:     {total}")
    print(f"   Correct:           {correct} ({correct/total*100:.1f}%)")
    print(f"   Incorrect:         {total-correct-errors} ({(total-correct-errors)/total*100:.1f}%)")
    print(f"   Errors:            {errors} ({errors/total*100:.1f}%)")
    
    # Timing stats
    if results:
        times = [r.get('time', 0) for r in results]
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n⏱️  Timing Statistics:")
        print(f"   Average time:      {avg_time:.2f}s")
        print(f"   Min time:          {min_time:.2f}s")
        print(f"   Max time:          {max_time:.2f}s")
        print(f"   Total time:        {sum(times)/60:.1f} minutes")
        
        # Estimate full test
        if total < 1639:
            est_full = (avg_time * 1639) / 60
            print(f"   Est. full test:    {est_full:.1f} minutes ({est_full/60:.1f} hours)")
    
    # Confidence analysis
    correct_results = [r for r in results if r.get('correct', False)]
    incorrect_results = [r for r in results if not r.get('correct', False) and 'error' not in r]
    
    if correct_results:
        correct_conf = [r.get('confidence', 0) for r in correct_results]
        avg_correct_conf = sum(correct_conf) / len(correct_conf)
        print(f"\n🎯 Confidence Analysis:")
        print(f"   Avg confidence (correct):   {avg_correct_conf:.3f}")
    
    if incorrect_results:
        incorrect_conf = [r.get('confidence', 0) for r in incorrect_results]
        avg_incorrect_conf = sum(incorrect_conf) / len(incorrect_conf)
        print(f"   Avg confidence (incorrect): {avg_incorrect_conf:.3f}")
    
    # Path statistics
    path_counts = [r.get('num_paths', 0) for r in results]
    if path_counts:
        avg_paths = sum(path_counts) / len(path_counts)
        no_paths = sum(1 for p in path_counts if p == 0)
        print(f"\n🔍 Path Finding Statistics:")
        print(f"   Avg paths found:   {avg_paths:.1f}")
        print(f"   No paths found:    {no_paths} ({no_paths/total*100:.1f}%)")
    
    # Error analysis
    if errors > 0:
        error_results = [r for r in results if 'error' in r]
        error_types = {}
        for r in error_results:
            error_msg = r.get('error', 'Unknown')
            error_type = error_msg.split(':')[0]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        print(f"\n❌ Error Breakdown:")
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {error_type}: {count}")
    
    # Top errors (if any)
    print(f"\n❌ Sample Incorrect Predictions:")
    incorrect_samples = [r for r in results if not r.get('correct', False) and 'error' not in r][:5]
    for i, r in enumerate(incorrect_samples, 1):
        print(f"\n   {i}. Q: {r.get('question', 'N/A')[:60]}...")
        print(f"      Gold: {', '.join(r.get('gold_answers', [])[:2])}")
        print(f"      Pred: {r.get('predicted_answer', 'N/A')} (conf: {r.get('confidence', 0):.2f})")
    
    # Top correct predictions
    print(f"\n✅ Sample Correct Predictions:")
    correct_samples = [r for r in results if r.get('correct', False)][:5]
    for i, r in enumerate(correct_samples, 1):
        print(f"\n   {i}. Q: {r.get('question', 'N/A')[:60]}...")
        print(f"      Gold: {', '.join(r.get('gold_answers', [])[:2])}")
        print(f"      Pred: {r.get('predicted_answer', 'N/A')} (conf: {r.get('confidence', 0):.2f})")
    
    print("\n" + "="*70)


def compare_results(file1: str, file2: str):
    """Compare two result files."""
    data1 = load_results(file1)
    data2 = load_results(file2)
    
    results1 = data1.get('results', [])
    results2 = data2.get('results', [])
    
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    
    total1 = len(results1)
    total2 = len(results2)
    correct1 = sum(1 for r in results1 if r.get('correct', False))
    correct2 = sum(1 for r in results2 if r.get('correct', False))
    
    print(f"\nFile 1: {file1}")
    print(f"  Samples: {total1}")
    print(f"  Accuracy: {correct1/total1*100:.1f}%")
    
    print(f"\nFile 2: {file2}")
    print(f"  Samples: {total2}")
    print(f"  Accuracy: {correct2/total2*100:.1f}%")
    
    if total1 == total2:
        diff = (correct2/total2 - correct1/total1) * 100
        print(f"\nDifference: {diff:+.1f}%")
    
    print("="*70)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Analyze single result:")
        print("    python analyze_results.py <result_file.json>")
        print("\n  Compare two results:")
        print("    python analyze_results.py <file1.json> <file2.json>")
        print("\n  List available results:")
        print("    python analyze_results.py --list")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        # List all result files
        results_dir = Path("test_results")
        if results_dir.exists():
            print("\nAvailable result files:")
            for subdir in results_dir.iterdir():
                if subdir.is_dir():
                    print(f"\n  {subdir.name}/")
                    for file in sorted(subdir.glob("*.json")):
                        size_kb = file.stat().st_size / 1024
                        print(f"    - {file.name} ({size_kb:.1f} KB)")
        else:
            print("No test_results directory found!")
        return
    
    file1 = sys.argv[1]
    
    if len(sys.argv) == 3:
        # Compare mode
        file2 = sys.argv[2]
        compare_results(file1, file2)
    else:
        # Analyze mode
        data = load_results(file1)
        analyze_results(data)


if __name__ == "__main__":
    main()
