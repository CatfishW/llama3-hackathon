# Parquet Integration - Quick Reference Card

## 🚀 Quick Start (3 Commands)

```bash
# 1. Check what will happen
python freebase-easy-latest/estimate_conversion.py

# 2. Convert files (one-time, ~2-3 hours)
python freebase-easy-latest/convert_to_parquet.py

# 3. Test the integration
python test_parquet_integration.py
```

## 📦 Installation

```bash
pip install pyarrow pandas
```

## ⚙️ Configuration

### Auto-Detection (Recommended)
```python
from kg_llm_new.config import PipelineConfig, FreebaseEasyConfig

config = PipelineConfig(
    freebase_easy=FreebaseEasyConfig(
        enabled=True,
        root_path=Path("./freebase-easy-latest"),
        use_parquet=True,
    ),
).resolve()
```

### Memory Tuning
```python
chunk_size=50000   # 4GB RAM
chunk_size=100000  # 8GB RAM (default)
chunk_size=200000  # 16GB+ RAM
```

## 📊 Performance

| Metric | Text Files | Parquet Files | Improvement |
|--------|-----------|--------------|-------------|
| Size | 28 GB | 10 GB | **65% smaller** |
| Processing | 6-8 hrs | 2-3 hrs | **2-3x faster** |
| Memory | 24+ GB | 2-4 GB | **80% less** |

## 🛠️ Common Commands

### Conversion
```bash
cd freebase-easy-latest
python convert_to_parquet.py
```

### Browse Parquet
```bash
cd freebase-easy-latest
python read_parquet.py
```

### Estimate Before Converting
```bash
python estimate_conversion.py
```

### Test Integration
```bash
python test_parquet_integration.py
```

## 🔧 Troubleshooting

### Out of Memory
```python
chunk_size=25000  # Reduce chunk size
```

### Files Not Found
```bash
# Check files exist
ls freebase-easy-latest/*.parquet

# Or convert them
python freebase-easy-latest/convert_to_parquet.py
```

### Slow Processing
```python
chunk_size=200000  # Increase for faster processing (if RAM allows)
```

### Use Text Files Instead
```python
use_parquet=False  # Fallback to text files
```

## 📁 Files Created

After conversion:
```
freebase-easy-latest/
├── facts.parquet (7.6 GB)
├── scores.parquet (1.0 GB)
└── freebase-links.parquet (1.2 GB)
```

After pipeline run:
```
freebase_easy_shards/
├── one_hop.jsonl
├── two_hop.jsonl
├── literal.jsonl
└── description.jsonl
```

## 📚 Documentation

- **Full Guide**: `docs/PARQUET_INTEGRATION.md`
- **Converter Docs**: `freebase-easy-latest/README_CONVERTER.md`
- **Quick Start**: `freebase-easy-latest/QUICKSTART.md`
- **Examples**: `example_parquet_config.py`

## ✅ Checklist

Before running:
- [ ] Install pyarrow and pandas
- [ ] Check disk space (~10GB needed)
- [ ] Estimate conversion time
- [ ] Close memory-intensive programs

After conversion:
- [ ] Verify Parquet files exist
- [ ] Test with limited data first
- [ ] Run integration tests
- [ ] Update configuration

## 💡 Pro Tips

1. **Keep original files** until Parquet is verified
2. **Test with `max_facts=100000`** before full run
3. **Add `*.parquet` to `.gitignore`** (already done)
4. **Conversion is one-time** - worth the initial wait
5. **Use auto-detection** - simplest configuration

## 🆘 Need Help?

1. Check logs in `./logs/` directory
2. Run `python test_parquet_integration.py`
3. Verify files with `python read_parquet.py`
4. Review `docs/PARQUET_INTEGRATION.md`

---

**Ready?** Run: `python freebase-easy-latest/estimate_conversion.py`
