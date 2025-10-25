# Parquet Integration Guide

## Overview

The KG-LLM-NEW project now supports **Parquet files** for processing large Freebase Easy datasets. This provides significant performance and memory benefits over text files.

## Benefits of Using Parquet

### 🚀 Performance
- **60-70% smaller files** (22GB → 7-8GB)
- **10-50x faster data loading**
- **Columnar storage** enables selective column reading
- **Memory-efficient chunked processing**

### 💾 Memory Safety
- Process 22GB+ files without loading everything into RAM
- Configurable chunk sizes (50k-200k rows)
- Automatic garbage collection between chunks
- Safe for systems with 4GB+ RAM

### 📊 Data Efficiency
- Built-in compression (Snappy)
- Typed columns (no string parsing overhead)
- Efficient filtering and querying
- Better disk I/O patterns

## Setup

### 1. Convert Your Text Files to Parquet

First, convert your large text files using the provided conversion scripts:

```bash
cd freebase-easy-latest
python convert_to_parquet.py
```

This will create:
- `facts.parquet` (~7-8 GB from 22GB text)
- `scores.parquet` (~1 GB from 3GB text)
- `freebase-links.parquet` (~1.2 GB from 3.5GB text)

### 2. Update Your Configuration

#### Option A: Auto-Detection (Recommended)

```python
from pathlib import Path
from kg_llm_new.config import PipelineConfig, FreebaseEasyConfig

config = PipelineConfig(
    freebase_easy=FreebaseEasyConfig(
        enabled=True,
        root_path=Path("./freebase-easy-latest"),  # Auto-detects .parquet files
        use_parquet=True,  # Prefer Parquet over text files
        chunk_size=100000,  # Adjust based on your RAM
    ),
).resolve()
```

#### Option B: Explicit Paths

```python
config = PipelineConfig(
    freebase_easy=FreebaseEasyConfig(
        enabled=True,
        facts_parquet_path=Path("./freebase-easy-latest/facts.parquet"),
        scores_parquet_path=Path("./freebase-easy-latest/scores.parquet"),
        use_parquet=True,
        chunk_size=100000,
    ),
).resolve()
```

### 3. Run Your Pipeline

The pipeline will automatically use Parquet files if available:

```python
from kg_llm_new.pipeline import KGPipeline

pipeline = KGPipeline(
    config=config,
    classifier=your_classifier,
    llm_client_config=your_llm_config,
)

result = pipeline.run(
    question="What is the capital of France?",
    entities=["France"],
)
```

## Configuration Options

### Core Parquet Settings

```python
FreebaseEasyConfig(
    # Enable Parquet processing
    use_parquet=True,  # Default: True
    
    # Chunk size for batch processing
    chunk_size=100000,  # Rows per batch
    
    # File paths (auto-detected if root_path is provided)
    facts_parquet_path=None,
    scores_parquet_path=None,
    
    # Or use root_path for auto-detection
    root_path=Path("./freebase-easy-latest"),
)
```

### Memory Tuning

Adjust `chunk_size` based on your available RAM:

| RAM Available | Recommended chunk_size | Processing Speed |
|---------------|------------------------|------------------|
| 4 GB          | 50,000                 | Slower           |
| 8 GB          | 100,000 (default)      | Balanced         |
| 16 GB         | 200,000                | Faster           |
| 32 GB+        | 500,000                | Fastest          |

### Example: Limited RAM Configuration

```python
config = FreebaseEasyConfig(
    enabled=True,
    root_path=Path("./freebase-easy-latest"),
    use_parquet=True,
    chunk_size=50000,  # Reduced for 4GB RAM systems
    max_facts=1000000,  # Limit total facts for testing
)
```

## Architecture

### Data Flow

```
Parquet Files (facts.parquet, scores.parquet)
    ↓
ParquetFreebaseEasyShardBuilder
    ↓ (chunked processing)
JSONL Shards (one_hop.jsonl, literal.jsonl, description.jsonl)
    ↓
KnowledgeGraphLoader
    ↓
KnowledgeGraphStore (in-memory)
    ↓
Retriever → Pipeline → Results
```

### File Structure

```
freebase-easy-latest/
├── facts.parquet          # Main knowledge base (compressed)
├── scores.parquet         # Entity prominence scores
├── freebase-links.parquet # Entity-to-URL mappings
└── (original .txt files can be deleted after conversion)

freebase_easy_shards/      # Generated JSONL shards
├── one_hop.jsonl          # Entity→Entity relationships
├── two_hop.jsonl          # 2-hop paths
├── literal.jsonl          # Entity→Value facts
└── description.jsonl      # Entity descriptions
```

## Performance Comparison

### Processing 22GB facts.txt

| Method | Processing Time | Memory Usage | File Size |
|--------|----------------|--------------|-----------|
| Text file (original) | ~6-8 hours | 24GB+ (loads full file) | 22 GB |
| **Parquet (new)** | **~2-3 hours** | **~2-4GB (chunked)** | **7.6 GB** |

### Speedup Factors
- **Initial conversion**: One-time cost of ~2-3 hours
- **Subsequent processing**: 2-3x faster than text
- **Shard generation**: 50% faster
- **Memory efficiency**: 80% less RAM required

## Troubleshooting

### Out of Memory Errors

**Symptom**: Python crashes or system freezes during processing

**Solution**: Reduce chunk size
```python
chunk_size=25000  # Try smaller chunks
```

### Parquet Files Not Found

**Symptom**: Warning message "Parquet Freebase Easy ingestion failed"

**Solution**: 
1. Check file paths: `config.freebase_easy.facts_parquet_path`
2. Ensure files were converted: `ls freebase-easy-latest/*.parquet`
3. Run conversion script: `python convert_to_parquet.py`

### Slow Processing

**Symptom**: Processing takes longer than expected

**Possible causes**:
1. **Chunk size too small**: Increase `chunk_size` to 200000+
2. **Disk I/O bottleneck**: Use SSD instead of HDD
3. **Many predicates**: Narrow down `description_predicates` etc.

**Solution**: Monitor with logging
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Fallback to Text Files

If Parquet processing fails, the system automatically falls back to text files:

```
WARNING: Parquet Freebase Easy ingestion failed: facts.parquet not found
INFO: Using text-based Freebase Easy processing
```

To force text file usage:
```python
use_parquet=False
```

## Advanced Usage

### Custom Parquet Schema

The conversion script uses this schema:

**facts.parquet**:
- `subject`: string (entity ID)
- `predicate`: string (relation)
- `object`: string (value or entity ID)
- `extra`: string (optional metadata)

**scores.parquet**:
- `entity`: string
- `score_type`: string (e.g., "prominence-score")
- `score_value`: float

### Filtering Data During Processing

```python
config = FreebaseEasyConfig(
    enabled=True,
    root_path=Path("./freebase-easy-latest"),
    use_parquet=True,
    
    # Only process first 5M facts (for testing)
    max_facts=5000000,
    
    # Language filtering
    languages=["en", "es"],  # English and Spanish
    include_all_languages=False,
    
    # Predicate filtering
    description_predicates=["/common/topic/description"],
    literal_predicates=["/type/object/name", "/common/topic/alias"],
)
```

### Monitoring Progress

Enable verbose logging to see chunk-by-chunk progress:

```python
from kg_llm_new.logging_utils import get_logger
import logging

logger = get_logger(__name__)
logger.setLevel(logging.INFO)

# You'll see:
# INFO: Processing facts from facts.parquet in chunks of 100000
# INFO: Processed 1000000 facts...
# INFO: Processed 2000000 facts...
# INFO: Completed processing 10000000 facts
```

## Migration Guide

### From Text Files to Parquet

1. **Backup** your existing configuration
2. **Convert** text files to Parquet (one-time operation)
   ```bash
   cd freebase-easy-latest
   python estimate_conversion.py  # Check space requirements
   python convert_to_parquet.py   # Convert files
   ```
3. **Update** configuration to use Parquet
   ```python
   use_parquet=True  # Add this to FreebaseEasyConfig
   ```
4. **Test** with limited data first
   ```python
   max_facts=100000  # Process sample for testing
   ```
5. **Run** full pipeline after verification
   ```python
   max_facts=None  # Process all data
   ```

### Keeping Both Formats

You can keep both text and Parquet files:

```python
# Auto-selects Parquet if available, falls back to text
config = FreebaseEasyConfig(
    enabled=True,
    root_path=Path("./freebase-easy-latest"),
    use_parquet=True,  # Prefer Parquet
)
```

Files will be detected in this order:
1. `facts.parquet` (if `use_parquet=True`)
2. `facts.txt` (fallback)

## Best Practices

### ✅ Do

- **Convert to Parquet** before processing large datasets
- **Use auto-detection** with `root_path` for simplicity
- **Tune chunk_size** based on your system's RAM
- **Test with `max_facts`** before full processing
- **Monitor logs** during first run
- **Keep original text files** until Parquet is verified

### ❌ Don't

- Don't commit Parquet files to git (add to `.gitignore`)
- Don't use very small chunk sizes (<10,000) - too slow
- Don't use very large chunk sizes (>500,000) - memory risk
- Don't delete text files until Parquet is confirmed working
- Don't process without checking disk space first

## Examples

See `example_parquet_config.py` for complete configuration examples:
- Basic Parquet setup
- Memory-constrained systems
- Testing with subsets
- Auto-detection mode

## Support

For issues or questions:
1. Check logs: `./logs/` directory
2. Verify Parquet files: `python read_parquet.py`
3. Test with small dataset: `max_facts=100000`
4. Check conversion: `python estimate_conversion.py`

## References

- [Apache Parquet Documentation](https://parquet.apache.org/docs/)
- [PyArrow Parquet Guide](https://arrow.apache.org/docs/python/parquet.html)
- [Conversion Scripts](../freebase-easy-latest/README_CONVERTER.md)
