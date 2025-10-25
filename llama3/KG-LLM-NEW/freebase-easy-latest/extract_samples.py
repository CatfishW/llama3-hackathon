#!/usr/bin/env python3
"""
Extract sample lines from large text files.
"""

import os
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent

# Files to sample
files_to_sample = [
    'facts.txt',
    'freebase-links.txt',
    'scores.txt'
]

# Number of lines to extract from the beginning and end
num_samples = 50

def extract_samples(filepath, num_lines=50):
    """Extract first and last num_lines from a file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = []
            # Read file line by line to get first samples
            for i, line in enumerate(f):
                if i < num_lines:
                    lines.append(('start', i + 1, line.rstrip('\n')))
                else:
                    break
            
            # Count total lines and get last samples
            f.seek(0)
            total_lines = sum(1 for _ in f)
            
            if total_lines > num_lines * 2:
                # Get last num_lines
                f.seek(0)
                all_lines = f.readlines()
                for i, line in enumerate(all_lines[-num_lines:], start=total_lines - num_lines + 1):
                    lines.append(('end', i, line.rstrip('\n')))
            
            return total_lines, lines
    except Exception as e:
        return None, str(e)

# Extract samples from each file
for filename in files_to_sample:
    filepath = script_dir / filename
    
    if not filepath.exists():
        print(f"⚠️  File not found: {filename}")
        continue
    
    print(f"\n{'='*80}")
    print(f"File: {filename}")
    print(f"{'='*80}")
    
    total_lines, samples = extract_samples(filepath, num_samples)
    
    if total_lines is None:
        print(f"❌ Error reading file: {samples}")
        continue
    
    print(f"Total lines: {total_lines:,}")
    print(f"\nFirst {num_samples} lines:")
    print("-" * 80)
    for position, line_num, content in samples:
        if position == 'start':
            print(f"[Line {line_num}] {content[:150]}")
    
    if total_lines > num_samples * 2:
        print(f"\n... ({total_lines - num_samples * 2:,} lines omitted) ...\n")
        print(f"Last {num_samples} lines:")
        print("-" * 80)
        for position, line_num, content in samples:
            if position == 'end':
                print(f"[Line {line_num}] {content[:150]}")
    
    print()

print(f"\n✅ Sampling complete!")
