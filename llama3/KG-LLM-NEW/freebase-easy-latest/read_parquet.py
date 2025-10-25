#!/usr/bin/env python3
"""
Efficiently read and query Parquet files without loading everything into memory.
Demonstrates various ways to work with large Parquet files.
"""

import sys
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc
from tqdm import tqdm

class ParquetReader:
    """Efficient Parquet file reader with various query methods."""
    
    def __init__(self, parquet_file: Path):
        self.parquet_file = parquet_file
        self.parquet_table = pq.ParquetFile(parquet_file)
        
    def get_info(self):
        """Get basic information about the Parquet file."""
        print(f"\n{'='*80}")
        print(f"📊 Parquet File Information: {self.parquet_file.name}")
        print(f"{'='*80}")
        
        metadata = self.parquet_table.metadata
        schema = self.parquet_table.schema_arrow
        
        print(f"📋 Schema:")
        for i, field in enumerate(schema):
            print(f"   {i+1}. {field.name}: {field.type}")
        
        print(f"\n📦 File Statistics:")
        print(f"   • Number of rows: {metadata.num_rows:,}")
        print(f"   • Number of columns: {metadata.num_columns}")
        print(f"   • Number of row groups: {metadata.num_row_groups}")
        print(f"   • File size: {self.parquet_file.stat().st_size / (1024**3):.2f} GB")
        
        # Estimate memory usage if loaded fully
        estimated_memory = metadata.num_rows * metadata.num_columns * 50  # Rough estimate
        print(f"   • Estimated memory (if loaded): {estimated_memory / (1024**3):.2f} GB")
        
    def preview_head(self, n: int = 10):
        """Preview first n rows."""
        print(f"\n📖 First {n} rows:")
        print("-" * 80)
        df = self.parquet_table.read_row_group(0).to_pandas().head(n)
        print(df.to_string())
        
    def preview_random(self, n: int = 10):
        """Preview random n rows."""
        print(f"\n🎲 Random {n} rows:")
        print("-" * 80)
        
        # Read metadata to get total rows
        total_rows = self.parquet_table.metadata.num_rows
        
        # Sample random row indices
        import random
        sample_indices = sorted(random.sample(range(total_rows), min(n, total_rows)))
        
        # Read and display
        table = self.parquet_table.read()
        sample_table = table.take(sample_indices)
        df = sample_table.to_pandas()
        print(df.to_string())
        
    def search(self, column: str, value: str, max_results: int = 100):
        """Search for rows where column contains value."""
        print(f"\n🔍 Searching for '{value}' in column '{column}'...")
        print("-" * 80)
        
        results = []
        for i in range(self.parquet_table.num_row_groups):
            row_group = self.parquet_table.read_row_group(i)
            
            if column not in row_group.column_names:
                print(f"❌ Column '{column}' not found!")
                return
            
            # Convert to pandas for easy filtering
            df = row_group.to_pandas()
            
            # Filter rows
            mask = df[column].astype(str).str.contains(value, case=False, na=False)
            filtered = df[mask]
            
            results.append(filtered)
            
            if sum(len(r) for r in results) >= max_results:
                break
        
        if results:
            all_results = pd.concat(results, ignore_index=True).head(max_results)
            print(f"Found {len(all_results)} results (showing first {max_results}):")
            print(all_results.to_string())
        else:
            print("No results found.")
    
    def get_column_stats(self, column: str):
        """Get statistics for a specific column."""
        print(f"\n📈 Statistics for column '{column}':")
        print("-" * 80)
        
        table = self.parquet_table.read([column])
        
        if column not in table.column_names:
            print(f"❌ Column '{column}' not found!")
            return
        
        col = table[column]
        
        print(f"   • Total values: {len(col):,}")
        print(f"   • Null values: {col.null_count:,}")
        print(f"   • Unique values: {len(pc.unique(col)):,}")
        
        # For numeric columns, show more stats
        if pa.types.is_floating(col.type) or pa.types.is_integer(col.type):
            print(f"   • Min: {pc.min(col).as_py()}")
            print(f"   • Max: {pc.max(col).as_py()}")
            print(f"   • Mean: {pc.mean(col).as_py():.2f}")
    
    def iterate_batches(self, batch_size: int = 10000):
        """Demonstrate batch iteration for processing large files."""
        print(f"\n🔄 Iterating through batches (size: {batch_size:,})...")
        print("-" * 80)
        
        batch_reader = self.parquet_table.iter_batches(batch_size=batch_size)
        
        total_rows = 0
        for i, batch in enumerate(batch_reader, 1):
            total_rows += len(batch)
            if i <= 3:  # Show first 3 batches
                print(f"   Batch {i}: {len(batch):,} rows")
            elif i == 4:
                print(f"   ... (continuing to process all batches)")
                break
        
        # Count remaining
        for batch in batch_reader:
            total_rows += len(batch)
        
        print(f"\n✅ Processed {total_rows:,} total rows")
    
    def export_to_csv_sample(self, output_file: Path, n_rows: int = 1000):
        """Export a sample to CSV for inspection."""
        print(f"\n💾 Exporting {n_rows:,} rows to CSV: {output_file.name}")
        
        df = self.parquet_table.read_row_group(0).to_pandas().head(n_rows)
        df.to_csv(output_file, index=False)
        
        print(f"✅ Exported to {output_file}")
    
    def filter_and_save(self, filter_column: str, filter_value: str, 
                       output_file: Path, max_rows: int = None):
        """Filter data and save to a new Parquet file."""
        print(f"\n🔍 Filtering {filter_column}='{filter_value}' and saving...")
        
        results = []
        for i in range(self.parquet_table.num_row_groups):
            row_group = self.parquet_table.read_row_group(i)
            df = row_group.to_pandas()
            
            # Filter
            mask = df[filter_column].astype(str).str.contains(filter_value, case=False, na=False)
            filtered = df[mask]
            
            if len(filtered) > 0:
                results.append(filtered)
            
            if max_rows and sum(len(r) for r in results) >= max_rows:
                break
        
        if results:
            final_df = pd.concat(results, ignore_index=True)
            if max_rows:
                final_df = final_df.head(max_rows)
            
            final_df.to_parquet(output_file, compression='snappy')
            print(f"✅ Saved {len(final_df):,} rows to {output_file}")
        else:
            print("❌ No matching rows found.")


def main():
    """Interactive Parquet file reader."""
    print("📚 Parquet File Reader & Query Tool")
    print("="*80)
    
    script_dir = Path(__file__).parent
    
    # Find all parquet files
    parquet_files = list(script_dir.glob("*.parquet"))
    
    if not parquet_files:
        print("❌ No Parquet files found in the current directory.")
        print("   Run convert_to_parquet.py first to convert your text files.")
        return
    
    print("\nAvailable Parquet files:")
    for i, pf in enumerate(parquet_files, 1):
        size_mb = pf.stat().st_size / (1024**2)
        print(f"  {i}. {pf.name} ({size_mb:.2f} MB)")
    
    # Select file
    choice = input(f"\nSelect a file (1-{len(parquet_files)}) or 'q' to quit: ").strip()
    
    if choice.lower() == 'q':
        return
    
    try:
        file_idx = int(choice) - 1
        if file_idx < 0 or file_idx >= len(parquet_files):
            print("❌ Invalid choice.")
            return
    except ValueError:
        print("❌ Invalid input.")
        return
    
    selected_file = parquet_files[file_idx]
    reader = ParquetReader(selected_file)
    
    # Show menu
    while True:
        print("\n" + "="*80)
        print("📋 Menu Options:")
        print("="*80)
        print("  1. Show file information")
        print("  2. Preview first 10 rows")
        print("  3. Preview random 10 rows")
        print("  4. Search for a value in a column")
        print("  5. Get column statistics")
        print("  6. Export sample to CSV (1000 rows)")
        print("  7. Filter and save subset")
        print("  8. Select different file")
        print("  9. Quit")
        
        action = input("\nSelect an option (1-9): ").strip()
        
        if action == '1':
            reader.get_info()
        elif action == '2':
            reader.preview_head()
        elif action == '3':
            reader.preview_random()
        elif action == '4':
            column = input("Enter column name: ").strip()
            value = input("Enter search value: ").strip()
            reader.search(column, value)
        elif action == '5':
            column = input("Enter column name: ").strip()
            reader.get_column_stats(column)
        elif action == '6':
            output_file = script_dir / f"{selected_file.stem}_sample.csv"
            reader.export_to_csv_sample(output_file)
        elif action == '7':
            column = input("Enter filter column: ").strip()
            value = input("Enter filter value: ").strip()
            output_file = script_dir / f"{selected_file.stem}_filtered.parquet"
            reader.filter_and_save(column, value, output_file)
        elif action == '8':
            main()
            return
        elif action == '9':
            print("👋 Goodbye!")
            return
        else:
            print("❌ Invalid option.")


if __name__ == '__main__':
    import pyarrow as pa  # Import here to avoid errors if not installed
    main()
