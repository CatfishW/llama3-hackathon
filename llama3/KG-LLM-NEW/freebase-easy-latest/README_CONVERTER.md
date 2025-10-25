# Large File Converter - README

## Overview

These scripts convert your 22GB+ text files into efficient **Parquet format** with the following benefits:
- ✅ **60-80% compression** (typical for text data)
- ✅ **Columnar storage** - fast queries without loading entire file
- ✅ **Memory-safe** - processes files in chunks
- ✅ **Fast I/O** - much faster than CSV/TXT
- ✅ **Type-aware** - preserves data types

## Scripts

### 1. `convert_to_parquet.py`
Converts large text files to Parquet format safely.

**Features:**
- Chunked processing (100k lines at a time)
- Automatic data type detection
- Progress tracking with tqdm
- Memory management with garbage collection
- File-specific parsers for facts, links, and scores

### 2. `read_parquet.py`
Interactive tool to query and explore Parquet files.

**Features:**
- View file info without loading entire file
- Search and filter data
- Export samples to CSV
- Column statistics
- Random sampling

## Installation

1. Install required packages:
```powershell
pip install -r requirements_converter.txt
```

Or install manually:
```powershell
pip install pandas pyarrow tqdm
```

## Usage

### Step 1: Convert Text Files to Parquet

```powershell
cd "z:\llama3_20250528\llama3\KG-LLM-NEW\freebase-easy-latest"
python convert_to_parquet.py
```

This will:
1. Detect all `.txt` files in the directory
2. Show you what will be converted
3. Ask for confirmation
4. Process each file in chunks (safe for large files)
5. Create `.parquet` files with the same name

**Example output:**
```
Files to convert:
  • facts.txt (22.5 GB) → facts.parquet
  • freebase-links.txt (18.3 GB) → freebase-links.parquet
  • scores.txt (5.2 GB) → scores.parquet

Proceed with conversion? (y/n): y
```

**Processing time estimate:**
- ~5-15 minutes per GB depending on your CPU
- 22GB file ≈ 2-5 hours

### Step 2: Work with Parquet Files

#### Option A: Interactive Tool
```powershell
python read_parquet.py
```

This opens an interactive menu where you can:
- Browse file information
- Preview data
- Search for specific values
- Export samples
- Filter and create subsets

#### Option B: Python Scripts
```python
import pandas as pd
import pyarrow.parquet as pq

# Load entire file (if it fits in memory)
df = pd.read_parquet('facts.parquet')

# Load only specific columns (much faster!)
df = pd.read_parquet('facts.parquet', columns=['subject', 'predicate'])

# Read in chunks (for files larger than RAM)
parquet_file = pq.ParquetFile('facts.parquet')
for batch in parquet_file.iter_batches(batch_size=10000):
    df = batch.to_pandas()
    # Process this batch
    print(df.head())
```

## File Formats

### facts.txt → facts.parquet
Columns: `subject`, `predicate`, `object`, `extra`

### freebase-links.txt → freebase-links.parquet
Columns: `entity_id`, `entity_name`, `relation`, `freebase_url`

### scores.txt → scores.parquet
Columns: `entity`, `score_type`, `score_value`

## Performance Tips

### Memory Management
1. **Don't load entire file** - Use chunked reading:
   ```python
   for chunk in parquet_file.iter_batches(batch_size=100000):
       process(chunk)
   ```

2. **Load only needed columns**:
   ```python
   df = pd.read_parquet('file.parquet', columns=['col1', 'col2'])
   ```

3. **Filter early** using PyArrow:
   ```python
   import pyarrow.compute as pc
   table = pq.read_table('file.parquet')
   filtered = table.filter(pc.equal(table['column'], 'value'))
   ```

### For Extra Large Files (100GB+)
Use **Dask** for distributed processing:
```python
import dask.dataframe as dd

# Dask handles files larger than RAM
df = dd.read_parquet('huge_file.parquet')
result = df[df['column'] == 'value'].compute()
```

## Troubleshooting

### "MemoryError" during conversion
- **Solution:** Reduce `CHUNK_SIZE` in `convert_to_parquet.py`
- Change line 16: `CHUNK_SIZE = 50000` (or lower)

### Conversion is slow
- **Normal!** Large files take time
- 22GB typically takes 2-5 hours
- Check Task Manager to ensure CPU is being used

### "Module not found" error
```powershell
pip install pandas pyarrow tqdm
```

### Want to cancel conversion?
- Press `Ctrl+C` in the terminal
- Partially converted files can be deleted

## Comparison: TXT vs Parquet

| Feature | TXT | Parquet |
|---------|-----|---------|
| Size (22GB file) | 22 GB | ~5-8 GB |
| Load time (full) | ~5 min | ~30 sec |
| Query single column | Load all | Load only that column |
| Memory usage | All in RAM | Chunked/lazy loading |
| Compression | None | Snappy (fast) |
| Type safety | All strings | Typed columns |

## Advanced: Parallel Processing

By default, files are processed sequentially for memory safety. To enable parallel processing (if you have 64GB+ RAM):

Edit `convert_to_parquet.py` line 260:
```python
# Change this:
for task in tasks:
    result = convert_file_wrapper(task)

# To this:
with Pool(MAX_WORKERS) as pool:
    results = pool.map(convert_file_wrapper, tasks)
```

## Additional Resources

- [Apache Parquet Documentation](https://parquet.apache.org/)
- [PyArrow Documentation](https://arrow.apache.org/docs/python/)
- [Pandas Parquet Guide](https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html)

## Support

If you encounter issues:
1. Check the error message carefully
2. Verify you have enough disk space (need at least 25% of original file size)
3. Ensure Python 3.8+ is installed
4. Try reducing chunk size for memory issues

---

**Created:** October 2025  
**Python Version:** 3.8+  
**Tested on:** Windows, Linux, macOS
