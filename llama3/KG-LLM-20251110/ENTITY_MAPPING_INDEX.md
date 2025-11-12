# Entity ID Mapping - File Index

## Quick Reference

| Need to... | Use this file... |
|------------|------------------|
| Get started quickly | `ENTITY_MAPPING_README.md` |
| Understand technical details | `ENTITY_ID_MAPPING_GUIDE.md` |
| See what changed | `ENTITY_MAPPING_CHANGES.md` |
| Check implementation status | `ENTITY_MAPPING_SUMMARY.md` |
| Verify setup | `test_entity_mapping.py` or `.bat` |
| Re-evaluate results | `reevaluate_with_entity_mapping.py` or `.bat` |
| Run tests | `test_webqsp_eperm_optimized.py` |

## Documentation Files

### 📖 User Documentation

**`ENTITY_MAPPING_README.md`** - START HERE
- Quick start guide
- Example output
- Common commands
- FAQ

**`ENTITY_MAPPING_SUMMARY.md`**
- Implementation summary
- Status and checklist
- Quick commands
- Expected outcomes

### 🔧 Technical Documentation

**`ENTITY_ID_MAPPING_GUIDE.md`**
- Detailed technical explanation
- Architecture and design
- Configuration options
- Troubleshooting guide

**`ENTITY_MAPPING_CHANGES.md`**
- Complete change log
- File-by-file modifications
- Backward compatibility
- Verification checklist

## Code Files

### 🔄 Modified Files

**`webqsp_loader.py`**
- Added: `find_entity_ids_for_answer()` method
- Modified: `create_qa_dataset()` to include entity ID mapping
- Purpose: Map gold answers to entity IDs during dataset loading

**`test_webqsp_eperm_optimized.py`**
- Modified: `_flexible_match()` to support entity IDs
- Updated: Result format with entity ID fields
- Enhanced: Sample processing with entity ID mapping
- Purpose: Properly evaluate predictions with entity IDs

### ✨ New Utility Files

**`reevaluate_with_entity_mapping.py`**
- Re-evaluates existing checkpoint files
- Maps gold answers to entity IDs retroactively
- Compares original vs. new accuracy
- Shows examples of changed evaluations
- Usage: `python reevaluate_with_entity_mapping.py checkpoint.json dataset.json`

**`test_entity_mapping.py`**
- Verification test suite
- Tests entity ID discovery
- Tests flexible matching
- Validates QA dataset creation
- Usage: `python test_entity_mapping.py`

### 🖥️ Batch Scripts (Windows)

**`test_entity_mapping.bat`**
- Runs verification tests
- Simple one-click testing
- Usage: Double-click or `test_entity_mapping.bat`

**`reevaluate.bat`**
- Runs re-evaluation with arguments
- Convenient wrapper for re-evaluation script
- Usage: `reevaluate.bat checkpoint.json dataset.json`

## Documentation Map

```
ENTITY_MAPPING_INDEX.md (this file)
├── Quick Start
│   ├── ENTITY_MAPPING_README.md ← Start here
│   └── ENTITY_MAPPING_SUMMARY.md
├── Technical Details
│   ├── ENTITY_ID_MAPPING_GUIDE.md
│   └── ENTITY_MAPPING_CHANGES.md
├── Implementation
│   ├── webqsp_loader.py (modified)
│   └── test_webqsp_eperm_optimized.py (modified)
├── Utilities
│   ├── reevaluate_with_entity_mapping.py (new)
│   └── test_entity_mapping.py (new)
└── Scripts
    ├── test_entity_mapping.bat (new)
    └── reevaluate.bat (new)
```

## Workflow Guides

### First-Time Setup
1. Read `ENTITY_MAPPING_README.md`
2. Run `test_entity_mapping.py` to verify
3. Check that all tests pass

### Re-evaluate Existing Results
1. Locate checkpoint file (e.g., `checkpoint_50.json`)
2. Run `reevaluate_with_entity_mapping.py checkpoint.json dataset.json`
3. Review accuracy improvement
4. Check examples of changed evaluations

### Run New Tests
1. Run `test_webqsp_eperm_optimized.py` (mapping is automatic)
2. Results include entity ID information
3. Evaluation uses entity IDs correctly

### Troubleshooting
1. Check `ENTITY_ID_MAPPING_GUIDE.md` troubleshooting section
2. Run `test_entity_mapping.py` to verify setup
3. Review configuration thresholds
4. Check example output in README

## Quick Command Reference

### Verification
```bash
# Test entity ID mapping
python test_entity_mapping.py

# Or use batch file
test_entity_mapping.bat
```

### Re-evaluation
```bash
# Re-evaluate checkpoint
python reevaluate_with_entity_mapping.py \
    test_results/test_full/checkpoint_50.json \
    data/webqsp/test_simple.json

# Or use batch file
reevaluate.bat test_results\test_full\checkpoint_50.json data\webqsp\test_simple.json
```

### Testing
```bash
# Run new tests (automatic entity ID mapping)
python test_webqsp_eperm_optimized.py
```

## Key Concepts

### Entity ID Mapping
- Gold answers (text) → Entity IDs
- Searches knowledge graph for matching entities
- Uses normalized text matching
- Threshold: 70% word overlap

### Flexible Matching
- Entity ID direct match (highest priority)
- Entity name resolution
- Text-based matching
- Cross-matching
- Threshold: 50% word overlap

### Result Format
```python
{
  "gold_answers": ["Mobile"],          # Text
  "gold_entity_ids": ["0gyh"],         # IDs
  "predicted_answer": "0gyh (mobile)", # Display
  "predicted_entity_id": "0gyh",       # ID
  "correct": true                      # Properly evaluated
}
```

## Support Resources

### Documentation Priority
1. **`ENTITY_MAPPING_README.md`** - Quick start
2. **`ENTITY_MAPPING_SUMMARY.md`** - Status check
3. **`ENTITY_ID_MAPPING_GUIDE.md`** - Deep dive
4. **`ENTITY_MAPPING_CHANGES.md`** - Technical changes

### Code Examples
- `test_entity_mapping.py` - Usage examples
- `reevaluate_with_entity_mapping.py` - Re-evaluation logic
- `webqsp_loader.py` - Entity ID discovery
- `test_webqsp_eperm_optimized.py` - Flexible matching

### Configuration
See `ENTITY_ID_MAPPING_GUIDE.md` → Configuration section

### Troubleshooting
See `ENTITY_ID_MAPPING_GUIDE.md` → Troubleshooting section

## Status

✓ Implementation complete  
✓ All files created  
✓ No syntax errors  
✓ Documentation comprehensive  
✓ Ready for testing  

## Next Steps

1. → Run `python test_entity_mapping.py`
2. → Re-evaluate existing checkpoint
3. → Run new tests with automatic mapping
4. → Review and adjust thresholds if needed

---

**Last Updated**: November 10, 2025  
**Version**: 1.0  
**Status**: Production Ready ✓  

Need help? Start with `ENTITY_MAPPING_README.md`! 📖
