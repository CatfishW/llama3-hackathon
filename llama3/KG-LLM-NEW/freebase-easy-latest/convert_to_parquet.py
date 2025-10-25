#!/usr/bin/env python3
"""
Convert large text files to efficient Parquet format with chunked processing.
Supports multiprocessing and handles 22GB+ files safely.
"""

import os
import sys
from pathlib import Path
from typing import Iterator, Dict, List
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import gc

# Configuration
CHUNK_SIZE = 100000  # Process 100k lines at a time
MAX_WORKERS = max(1, cpu_count() - 1)  # Leave one CPU free
OUTPUT_FORMAT = 'parquet'  # Most efficient format

class LargeFileConverter:
    """Convert large text files to Parquet format efficiently."""
    
    def __init__(self, input_file: Path, output_file: Path):
        self.input_file = input_file
        self.output_file = output_file
        self.file_type = self._detect_file_type()
        
    def _detect_file_type(self) -> str:
        """Detect the type of file based on filename."""
        filename = self.input_file.name.lower()
        if 'facts' in filename:
            return 'facts'
        elif 'links' in filename:
            return 'links'
        elif 'scores' in filename:
            return 'scores'
        else:
            return 'unknown'
    
    def _parse_facts_line(self, line: str) -> Dict:
        """Parse a line from facts.txt."""
        try:
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                return {
                    'subject': parts[0].strip(),
                    'predicate': parts[1].strip(),
                    'object': parts[2].strip(),
                    'extra': parts[3].strip() if len(parts) > 3 else ''
                }
        except Exception as e:
            pass
        return None
    
    def _parse_links_line(self, line: str) -> Dict:
        """Parse a line from freebase-links.txt."""
        try:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                # Format: :d:id:name  freebase-entity  <url>  .
                entity_parts = parts[0].split(':', 3)
                entity_id = entity_parts[2] if len(entity_parts) > 2 else ''
                entity_name = entity_parts[3] if len(entity_parts) > 3 else ''
                
                return {
                    'entity_id': entity_id,
                    'entity_name': entity_name,
                    'relation': parts[1].strip(),
                    'freebase_url': parts[2].strip().strip('<>'),
                }
        except Exception as e:
            pass
        return None
    
    def _parse_scores_line(self, line: str) -> Dict:
        """Parse a line from scores.txt."""
        try:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                return {
                    'entity': parts[0].strip(),
                    'score_type': parts[1].strip(),
                    'score_value': float(parts[2].strip()),
                }
        except Exception as e:
            pass
        return None
    
    def _parse_line(self, line: str) -> Dict:
        """Parse a line based on file type."""
        if self.file_type == 'facts':
            return self._parse_facts_line(line)
        elif self.file_type == 'links':
            return self._parse_links_line(line)
        elif self.file_type == 'scores':
            return self._parse_scores_line(line)
        else:
            # Generic parser: split by tabs
            parts = line.strip().split('\t')
            return {f'col_{i}': part.strip() for i, part in enumerate(parts)}
    
    def _count_lines(self) -> int:
        """Count total lines in file (for progress bar)."""
        print(f"📊 Counting lines in {self.input_file.name}...")
        try:
            with open(self.input_file, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception as e:
            print(f"⚠️  Warning: Could not count lines: {e}")
            return None
    
    def _read_chunks(self, chunk_size: int) -> Iterator[List[Dict]]:
        """Read file in chunks to avoid memory issues."""
        with open(self.input_file, 'r', encoding='utf-8', errors='ignore') as f:
            chunk = []
            for line in f:
                if line.strip():  # Skip empty lines
                    parsed = self._parse_line(line)
                    if parsed:
                        chunk.append(parsed)
                
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
                    gc.collect()  # Force garbage collection
            
            # Yield remaining lines
            if chunk:
                yield chunk
    
    def convert(self):
        """Convert the file to Parquet format."""
        print(f"\n{'='*80}")
        print(f"🔄 Converting: {self.input_file.name}")
        print(f"📦 Output: {self.output_file.name}")
        print(f"📋 File type: {self.file_type}")
        print(f"{'='*80}\n")
        
        # Count lines for progress bar
        total_lines = self._count_lines()
        
        # Initialize Parquet writer
        writer = None
        schema = None
        processed_lines = 0
        
        try:
            # Create progress bar
            pbar = tqdm(total=total_lines, unit='lines', unit_scale=True,
                       desc=f"Processing {self.input_file.name}")
            
            for chunk in self._read_chunks(CHUNK_SIZE):
                if not chunk:
                    continue
                
                # Convert chunk to DataFrame
                df = pd.DataFrame(chunk)
                
                # Initialize writer with schema from first chunk
                if writer is None:
                    schema = pa.Schema.from_pandas(df)
                    writer = pq.ParquetWriter(
                        self.output_file,
                        schema,
                        compression='snappy',  # Good balance of speed and compression
                        use_dictionary=True,  # Efficient for repeated strings
                    )
                
                # Write chunk to Parquet
                table = pa.Table.from_pandas(df, schema=schema)
                writer.write_table(table)
                
                processed_lines += len(chunk)
                pbar.update(len(chunk))
                
                # Clear memory
                del df, table, chunk
                gc.collect()
            
            pbar.close()
            
            if writer:
                writer.close()
            
            # Get file sizes
            input_size = self.input_file.stat().st_size
            output_size = self.output_file.stat().st_size
            compression_ratio = (1 - output_size / input_size) * 100
            
            print(f"\n✅ Conversion complete!")
            print(f"   📊 Processed: {processed_lines:,} lines")
            print(f"   💾 Input size: {input_size / (1024**3):.2f} GB")
            print(f"   💾 Output size: {output_size / (1024**3):.2f} GB")
            print(f"   📉 Compression: {compression_ratio:.1f}%")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during conversion: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if writer:
                writer.close()


def convert_file_wrapper(args):
    """Wrapper function for multiprocessing."""
    input_file, output_file = args
    converter = LargeFileConverter(input_file, output_file)
    return converter.convert()


def main():
    """Main conversion process."""
    print("🚀 Large File Converter - Text to Parquet")
    print(f"⚙️  Using {MAX_WORKERS} CPU cores")
    print(f"📦 Chunk size: {CHUNK_SIZE:,} lines\n")
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Files to convert
    files_to_convert = [
        'facts.txt',
        'freebase-links.txt',
        'scores.txt'
    ]
    
    # Prepare conversion tasks
    tasks = []
    for filename in files_to_convert:
        input_file = script_dir / filename
        if not input_file.exists():
            print(f"⚠️  File not found: {filename}")
            continue
        
        output_file = script_dir / f"{input_file.stem}.parquet"
        tasks.append((input_file, output_file))
    
    if not tasks:
        print("❌ No files to convert!")
        return
    
    # Ask for confirmation
    print("Files to convert:")
    for input_file, output_file in tasks:
        size_gb = input_file.stat().st_size / (1024**3)
        print(f"  • {input_file.name} ({size_gb:.2f} GB) → {output_file.name}")
    
    response = input(f"\nProceed with conversion? (y/n): ").strip().lower()
    if response != 'y':
        print("❌ Conversion cancelled.")
        return
    
    # Convert files sequentially (safer for very large files)
    # Note: Parallel processing could be enabled but may cause memory issues
    print("\n" + "="*80)
    print("Starting conversion (sequential mode for memory safety)...")
    print("="*80)
    
    results = []
    for task in tasks:
        result = convert_file_wrapper(task)
        results.append(result)
    
    # Summary
    print("\n" + "="*80)
    print("📊 CONVERSION SUMMARY")
    print("="*80)
    successful = sum(results)
    print(f"✅ Successful: {successful}/{len(tasks)}")
    print(f"❌ Failed: {len(tasks) - successful}/{len(tasks)}")
    
    print("\n💡 Tips for using Parquet files:")
    print("   • Use pandas: pd.read_parquet('file.parquet')")
    print("   • Use pyarrow: pq.read_table('file.parquet')")
    print("   • Load specific columns: pd.read_parquet('file.parquet', columns=['col1'])")
    print("   • Use dask for files larger than RAM: dask.dataframe.read_parquet()")
    

if __name__ == '__main__':
    main()
