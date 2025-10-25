#!/usr/bin/env python3
"""
Estimate conversion time and output size for large text files.
Run this before converting to plan your disk space and time.
"""

import os
from pathlib import Path
from datetime import timedelta

def format_size(bytes_size):
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def estimate_conversion(input_file: Path):
    """Estimate conversion metrics for a file."""
    file_size = input_file.stat().st_size
    file_size_gb = file_size / (1024**3)
    
    # Estimation factors (based on typical text data)
    COMPRESSION_RATIO = 0.35  # Parquet typically compresses to 30-40% of original
    PROCESSING_SPEED_MB_PER_SEC = 3.5  # ~3-5 MB/s on average CPU
    
    # Calculate estimates
    estimated_output_size = file_size * COMPRESSION_RATIO
    estimated_time_seconds = (file_size / (1024**2)) / PROCESSING_SPEED_MB_PER_SEC
    space_saved = file_size - estimated_output_size
    
    return {
        'input_size': file_size,
        'input_size_gb': file_size_gb,
        'estimated_output_size': estimated_output_size,
        'estimated_output_size_gb': estimated_output_size / (1024**3),
        'space_saved': space_saved,
        'space_saved_percent': (space_saved / file_size) * 100,
        'estimated_time_seconds': estimated_time_seconds,
        'estimated_time': str(timedelta(seconds=int(estimated_time_seconds)))
    }

def count_lines_fast(filepath: Path, sample_size: int = 10000):
    """Estimate total lines by sampling."""
    try:
        with open(filepath, 'rb') as f:
            # Count lines in first 10MB
            chunk = f.read(10 * 1024 * 1024)
            lines_in_sample = chunk.count(b'\n')
            
            # Get total file size
            f.seek(0, 2)
            total_size = f.tell()
            
            # Estimate total lines
            if len(chunk) > 0:
                estimated_total = int((total_size / len(chunk)) * lines_in_sample)
                return estimated_total
            return None
    except Exception as e:
        return None

def main():
    print("📊 File Conversion Estimator")
    print("="*80)
    
    script_dir = Path(__file__).parent
    
    # Find text files
    text_files = list(script_dir.glob("*.txt"))
    
    if not text_files:
        print("❌ No .txt files found in the current directory.")
        return
    
    print("\n🔍 Analyzing files...\n")
    
    total_input_size = 0
    total_output_size = 0
    total_time_seconds = 0
    
    for txt_file in text_files:
        if txt_file.name.startswith('.'):
            continue
            
        print(f"📄 {txt_file.name}")
        print("-" * 80)
        
        estimates = estimate_conversion(txt_file)
        
        print(f"   Input size:           {format_size(estimates['input_size'])} ({estimates['input_size_gb']:.2f} GB)")
        print(f"   Estimated output:     {format_size(estimates['estimated_output_size'])} ({estimates['estimated_output_size_gb']:.2f} GB)")
        print(f"   Space saved:          {format_size(estimates['space_saved'])} ({estimates['space_saved_percent']:.1f}%)")
        print(f"   Estimated time:       {estimates['estimated_time']}")
        
        # Estimate line count
        line_count = count_lines_fast(txt_file)
        if line_count:
            print(f"   Estimated lines:      {line_count:,}")
        
        print()
        
        total_input_size += estimates['input_size']
        total_output_size += estimates['estimated_output_size']
        total_time_seconds += estimates['estimated_time_seconds']
    
    # Summary
    print("="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Total files:              {len(text_files)}")
    print(f"Total input size:         {format_size(total_input_size)} ({total_input_size/(1024**3):.2f} GB)")
    print(f"Estimated output size:    {format_size(total_output_size)} ({total_output_size/(1024**3):.2f} GB)")
    print(f"Space to be saved:        {format_size(total_input_size - total_output_size)} ({((total_input_size - total_output_size)/total_input_size)*100:.1f}%)")
    print(f"Estimated total time:     {str(timedelta(seconds=int(total_time_seconds)))}")
    
    # Disk space check
    stat = os.statvfs(script_dir) if hasattr(os, 'statvfs') else None
    if stat:
        free_space = stat.f_bavail * stat.f_frsize
        print(f"\n💾 Disk space available:  {format_size(free_space)} ({free_space/(1024**3):.2f} GB)")
        
        if total_output_size > free_space:
            print(f"⚠️  WARNING: Not enough disk space for conversion!")
            print(f"   Need: {format_size(total_output_size)}")
            print(f"   Have: {format_size(free_space)}")
        else:
            remaining = free_space - total_output_size
            print(f"✅ Sufficient disk space (will have {format_size(remaining)} remaining)")
    
    print("\n" + "="*80)
    print("💡 Notes:")
    print("   • Estimates are approximate (±20-30%)")
    print("   • Actual compression depends on data redundancy")
    print("   • Processing speed varies by CPU and disk speed")
    print("   • Keep original files until verifying conversion")
    print("="*80)

if __name__ == '__main__':
    main()
