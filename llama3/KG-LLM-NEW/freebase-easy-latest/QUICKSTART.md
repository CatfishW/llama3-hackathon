# Quick Start Guide - Large File Converter

## ⚡ Quick Start (3 Steps)

### Step 1: Estimate
See what will happen before converting:
```powershell
python estimate_conversion.py
```

### Step 2: Convert
Convert your text files to efficient Parquet format:
```powershell
python convert_to_parquet.py
```

### Step 3: Read & Query
Explore your converted files:
```powershell
python read_parquet.py
```

## 🎯 Or Use the Batch File (Windows)
Double-click: `run_conversion.bat`

This will:
1. Show estimates
2. Ask for confirmation
3. Convert all files
4. Done!

## 📊 What Gets Converted

Your files → Compressed Parquet files:
- `facts.txt` (22+ GB) → `facts.parquet` (~7-8 GB)
- `freebase-links.txt` → `freebase-links.parquet`
- `scores.txt` → `scores.parquet`

**Benefits:**
- 60-70% smaller files
- 10-50x faster to query
- Load only columns you need
- Work with files larger than your RAM

## 💻 Using Parquet Files in Python

### Load entire file
```python
import pandas as pd
df = pd.read_parquet('facts.parquet')
```

### Load only specific columns (faster!)
```python
df = pd.read_parquet('facts.parquet', columns=['subject', 'predicate'])
```

### Process in chunks (for huge files)
```python
import pyarrow.parquet as pq

parquet_file = pq.ParquetFile('facts.parquet')
for batch in parquet_file.iter_batches(batch_size=100000):
    df = batch.to_pandas()
    # Process this chunk
    print(len(df))
```

### Search/filter without loading everything
```python
import pyarrow.parquet as pq
import pyarrow.compute as pc

table = pq.read_table('facts.parquet')
filtered = table.filter(
    pc.match_substring(table['subject'], 'Einstein')
)
df = filtered.to_pandas()
```

## 🔧 System Requirements

- **Python**: 3.8 or higher
- **RAM**: 4GB minimum (8GB+ recommended)
- **Disk Space**: ~35% of original file size for output
- **Time**: ~2-5 hours for 22GB file

## ⚠️ Important Notes

1. **Keep original files** until you verify the conversion worked
2. **Don't open other memory-intensive programs** during conversion
3. **Conversion is safe to cancel** with Ctrl+C if needed
4. **Each file is processed sequentially** to prevent crashes

## 🆘 Troubleshooting

**Out of memory?**
- Close other programs
- Edit `convert_to_parquet.py` line 16: change `CHUNK_SIZE = 100000` to `50000`

**Taking too long?**
- This is normal! 22GB takes 2-5 hours
- Check Task Manager - CPU should be active
- Leave it running overnight

**Missing packages?**
```powershell
pip install pandas pyarrow tqdm
```

## 📚 Full Documentation
See `README_CONVERTER.md` for complete details.

---
**Ready to start?** Run: `python estimate_conversion.py`
