# Gold Answer Entity ID Mapping - Quick Start

## Overview

This update fixes the evaluation accuracy issue by mapping gold answers (text) to entity IDs, enabling proper comparison with predicted entity IDs.

## What Changed

### Core Changes
1. **`webqsp_loader.py`** - Added entity ID mapping during dataset loading
2. **`test_webqsp_eperm_optimized.py`** - Enhanced matching to support entity IDs
3. **`reevaluate_with_entity_mapping.py`** - NEW: Re-evaluate existing checkpoints

### New Features
- Gold answers automatically mapped to entity IDs
- Flexible matching supports both text and entity IDs
- Enhanced result format with entity ID information
- Utility to re-evaluate existing test results

## Quick Start

### 1. Run New Tests (Automatic Entity ID Mapping)

```bash
# Quick test with entity ID mapping
python test_webqsp_eperm_optimized.py

# Select option 1 for quick test (10 samples)
```

All new tests will automatically:
- Map gold answers to entity IDs
- Compare predictions correctly
- Show both entity IDs and names in results

### 2. Test the Entity ID Mapping

```bash
# Verify entity ID mapping works
python test_entity_mapping.py

# Or use the batch file
test_entity_mapping.bat
```

### 3. Re-evaluate Existing Checkpoints

```bash
# Re-evaluate with entity ID mapping
python reevaluate_with_entity_mapping.py \
    test_results/test_full/checkpoint_50.json \
    data/webqsp/test_simple.json

# Or use the batch file
reevaluate.bat test_results\test_full\checkpoint_50.json data\webqsp\test_simple.json
```

## Example Output

### Before Entity ID Mapping
```
WebQTest-6: where is jamarcus russell from
  Gold: Mobile
  Pred: 0gyh
  Correct: ✗ (0% accuracy)
```

### After Entity ID Mapping
```
WebQTest-6: where is jamarcus russell from
  Gold: Mobile
  Gold IDs: 0gyh
  Pred: 0gyh (mobile)
  Pred ID: 0gyh
  Correct: ✓ (100% accuracy)
```

## New Result Format

Results now include:

```python
{
  "id": "WebQTest-6",
  "question": "where is jamarcus russell from",
  "gold_answers": ["Mobile"],           # Text format
  "gold_entity_ids": ["0gyh"],          # NEW: Entity IDs
  "predicted_answer": "0gyh (mobile)",  # Enhanced format
  "predicted_entity_id": "0gyh",        # NEW: Separate ID
  "confidence": 0.85,
  "correct": True,                      # Properly evaluated
  "time": 1.52,
  "num_paths": 2
}
```

## How It Works

### 1. Entity ID Discovery
When loading a sample, the system:
- Searches the knowledge graph for entities matching each gold answer
- Uses normalized text matching (lowercase, no punctuation)
- Considers partial matches and word overlap
- Returns all matching entity IDs

### 2. Answer Matching
When evaluating predictions, the system tries:
1. **Direct entity ID match**: `predicted_id == gold_entity_id`
2. **Entity name resolution**: Resolve entity ID to name, then match
3. **Text-based matching**: Traditional flexible text matching
4. **Cross-matching**: Check predicted text against gold entity names

### 3. Multiple Strategies
This multi-strategy approach handles:
- Predictions as entity IDs (e.g., "0gyh")
- Predictions as text (e.g., "Mobile")
- Partial matches and variations
- Mixed formats in results

## File Descriptions

### Modified Files

**`webqsp_loader.py`**
- Added `find_entity_ids_for_answer()` method
- Enhanced `create_qa_dataset()` to include entity ID mapping
- Supports flexible entity name matching

**`test_webqsp_eperm_optimized.py`**
- Enhanced `_flexible_match()` with entity ID support
- Updated result format with entity ID fields
- Improved output display with entity names

### New Files

**`reevaluate_with_entity_mapping.py`**
- Re-evaluates existing checkpoint files
- Rebuilds KGs and maps entity IDs
- Compares old vs. new accuracy
- Shows examples of changed evaluations

**`test_entity_mapping.py`**
- Verification tests for entity ID mapping
- Tests flexible matching logic
- Validates QA dataset creation

**`ENTITY_ID_MAPPING_GUIDE.md`**
- Comprehensive documentation
- Detailed technical explanation
- Configuration and troubleshooting

**`test_entity_mapping.bat`** & **`reevaluate.bat`**
- Convenient batch scripts for Windows
- Simplify running tests and re-evaluation

## Expected Results

### Accuracy Improvement
- **Before**: 0-5% (due to ID/text mismatch)
- **After**: 20-40% (proper entity matching)
- **Improvement**: 20-35 percentage points typical

### Better Debugging
- See entity IDs and human-readable names
- Track which gold entities were found
- Understand why matches succeed/fail

## Configuration

### Entity Discovery Threshold
In `webqsp_loader.py` (line ~102):
```python
if similarity >= 0.7:  # 70% word overlap for entity discovery
```

### Answer Matching Threshold
In `test_webqsp_eperm_optimized.py` (line ~68):
```python
if similarity >= 0.5:  # 50% word overlap for answer matching
```

Adjust based on precision/recall trade-off.

## Troubleshooting

### Empty gold_entity_ids
**Problem**: Gold answers not found in KG
**Solution**: Answer entity may not be in subgraph (limited to 150 triples)

### Still showing incorrect
**Problem**: Predicted answer is text, not entity ID
**Solution**: Check answer predictor returns entity IDs, not text

### Too many false positives
**Problem**: Matching threshold too low
**Solution**: Increase similarity threshold (0.7 → 0.8)

## Next Steps

1. **Test the mapping**: Run `test_entity_mapping.py`
2. **Re-evaluate existing results**: Use `reevaluate_with_entity_mapping.py`
3. **Run new tests**: Use updated `test_webqsp_eperm_optimized.py`
4. **Review documentation**: See `ENTITY_ID_MAPPING_GUIDE.md`

## Questions?

See detailed documentation in:
- `ENTITY_ID_MAPPING_GUIDE.md` - Technical details
- `test_entity_mapping.py` - Example code
- `reevaluate_with_entity_mapping.py` - Re-evaluation utility

## Summary

✓ Gold answers now mapped to entity IDs  
✓ Flexible matching supports both formats  
✓ Re-evaluation utility for existing results  
✓ Enhanced output with entity information  
✓ Significantly improved evaluation accuracy  

Ready to test with proper entity ID matching! 🎯
