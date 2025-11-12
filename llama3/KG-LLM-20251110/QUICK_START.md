# Quick Start Guide: Optimized WebQSP Testing

## TL;DR - Run This Now

```bash
cd z:\llama3_20250528\llama3\KG-LLM-20251110

# Install dependency (if needed)
pip install tqdm

# Quick test (2-3 minutes)
python test_webqsp_eperm_optimized.py 1
```

That's it! The script will:
- ✅ Load 10 samples
- ✅ Run optimized EPERM
- ✅ Show real-time progress
- ✅ Save results to `test_results/quick/`

---

## What Was Optimized?

### Before (Original)
```
30-45 seconds per question
4-6 LLM calls per question
Full test: 13-20 hours
```

### After (Optimized)
```
10-15 seconds per question
1-2 LLM calls per question
Full test: 4-7 hours (2-3x faster!)
```

### How?
1. **Heuristic candidate finding** - No LLM needed
2. **Batch path scoring** - Score all paths in 1 LLM call
3. **Direct answer extraction** - Extract from paths without LLM
4. **Smaller graphs** - 150 triples (vs 500)
5. **Checkpointing** - Never lose progress

---

## Testing Options

### 1️⃣ Quick Test (10 samples, 2-3 min)
```bash
python test_webqsp_eperm_optimized.py 1
```
Use this to verify everything works.

### 2️⃣ Medium Test (100 samples, 15-25 min)
```bash
python test_webqsp_eperm_optimized.py 2
```
Use this to estimate full test performance.

### 3️⃣ Full Test (1,639 samples, 4-7 hours)
```bash
python test_webqsp_eperm_optimized.py 3
```
The real deal. Run overnight.

### 4️⃣ Full Training (3,098 samples, 8-14 hours)
```bash
python test_webqsp_eperm_optimized.py 4
```
Even bigger dataset.

---

## During Testing

You'll see a progress bar:

```
Processing: 45%|████▌     | 450/1000 [1:15:30<1:32:20, acc=68.2%, avg_time=10.2s]
✓ Checkpoint saved: checkpoint_450.json
```

This shows:
- **45%** - Progress
- **450/1000** - Current sample / Total
- **1:15:30** - Time elapsed
- **1:32:20** - Estimated time remaining
- **acc=68.2%** - Current accuracy
- **avg_time=10.2s** - Average time per sample

---

## If Interrupted

Don't worry! The script auto-saves every 50 samples.

Just run the same command again:
```bash
python test_webqsp_eperm_optimized.py 3
```

It will detect the checkpoint:
```
Found checkpoint: checkpoint_450.json
Resume from checkpoint? (y/n): y
```

Press `y` and it continues from sample 451!

---

## View Results

### Quick Analysis
```bash
python analyze_results.py test_results/quick/final_results_10.json
```

Output:
```
📊 Overall Statistics:
   Total Samples:     10
   Correct:           7 (70.0%)
   Incorrect:         3 (30.0%)
   Errors:            0 (0.0%)

⏱️  Timing Statistics:
   Average time:      12.5s
   Total time:        2.1 minutes
   Est. full test:    5.7 hours
```

### List All Results
```bash
python analyze_results.py --list
```

### Compare Results
```bash
python analyze_results.py result1.json result2.json
```

---

## File Structure

```
test_results/
├── quick/                    # 10 sample test
│   └── final_results_10.json
├── medium/                   # 100 sample test
│   ├── checkpoint_20.json
│   ├── checkpoint_40.json
│   └── final_results_100.json
└── test_full/               # Full test set
    ├── checkpoint_50.json
    ├── checkpoint_100.json
    ├── checkpoint_150.json
    └── final_results_1639.json
```

---

## Expected Results

| Metric | Expected |
|--------|----------|
| **Accuracy** | 40-60% |
| **Coverage** | 85-95% find paths |
| **Avg Time** | 10-15s per sample |
| **Confidence** | 0.4-0.7 average |

Higher accuracy = Better LLM quality

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'tqdm'"
```bash
pip install tqdm
```

### "Connection timeout" or "LLM server error"
Check if server is running:
```bash
curl http://173.61.35.162:25565/v1/models
```

### Test is too slow
Edit `test_webqsp_eperm_optimized.py`:
```python
tester = OptimizedEPERMTester(
    max_kg_size=100,  # Reduce from 150
    ...
)
```

### Out of memory
Same as above - reduce `max_kg_size` to 50-100.

---

## Performance Tips

### Make It Even Faster

1. **Use fast config**:
   ```bash
   copy config_fast.py config.py
   ```

2. **Reduce KG size** in script:
   ```python
   max_kg_size=100  # or even 50
   ```

3. **Skip difficult questions**:
   Add early return for large KGs

### Monitor During Run

Watch the accuracy and avg_time in the progress bar:
- **Accuracy dropping?** Model might be struggling
- **Time increasing?** Later samples might be harder
- **Many errors?** Check LLM server

---

## What Each File Does

| File | Purpose |
|------|---------|
| `test_webqsp_eperm_optimized.py` | Main test script with progress tracking |
| `evidence_path_finder_fast.py` | Fast path finding (1 LLM call) |
| `answer_predictor_fast.py` | Fast answer prediction |
| `config_fast.py` | Optimized configuration |
| `analyze_results.py` | Result analysis tool |
| `quick_test.bat` | One-click quick test |

---

## Next Steps

1. **Run quick test** to verify setup:
   ```bash
   python test_webqsp_eperm_optimized.py 1
   ```

2. **Check results**:
   ```bash
   python analyze_results.py test_results/quick/final_results_10.json
   ```

3. **If good, run medium test**:
   ```bash
   python test_webqsp_eperm_optimized.py 2
   ```

4. **Then full test** (overnight):
   ```bash
   python test_webqsp_eperm_optimized.py 3
   ```

5. **Analyze final results**:
   ```bash
   python analyze_results.py test_results/test_full/final_results_1639.json
   ```

---

## Questions?

Check these docs:
- **OPTIMIZATION_README.md** - Detailed usage guide
- **OPTIMIZATION_SUMMARY.md** - Technical details
- **Original files** - `test_webqsp_eperm.py` for reference

---

## Summary

✅ **2-3x faster** than original
✅ **Auto-saves** progress every 50 samples
✅ **Resume** from any checkpoint
✅ **Real-time** progress tracking
✅ **Easy to use** - just run and wait

**Ready to test on full dataset!** 🚀
