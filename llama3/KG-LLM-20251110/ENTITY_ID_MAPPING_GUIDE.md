# Entity ID Mapping for WebQSP Testing

## Problem

The WebQSP test results showed 0% accuracy because of a mismatch between:
- **Gold Answers**: Human-readable text (e.g., "Mobile", "Diamond", "Jamaican English")
- **Predicted Answers**: Entity IDs from the knowledge graph (e.g., "0gyh", "09c7w0", "05zppz")

This made it impossible to correctly evaluate the system's performance.

## Solution

The solution involves mapping gold answer texts to entity IDs from the knowledge graph, enabling proper comparison between predicted entity IDs and gold entity IDs.

### Key Changes

#### 1. `webqsp_loader.py`

Added `find_entity_ids_for_answer()` method:
- Takes a gold answer text and searches the knowledge graph
- Returns matching entity IDs using:
  - Exact text matching (normalized)
  - Partial text matching
  - Word overlap similarity (≥70% threshold)

Modified `create_qa_dataset()` to include `answer_entity_ids` field:
```python
qa_item = {
    'id': sample_id,
    'question': question,
    'answers': answers,  # Text format
    'answer_entity_ids': [...],  # NEW: Entity IDs
    'kg': kg,
    'kg_stats': kg.stats()
}
```

#### 2. `test_webqsp_eperm_optimized.py`

Enhanced `_flexible_match()` function:
- Now accepts `gold_entity_ids` and `kg` parameters
- Matches using multiple strategies:
  1. Direct entity ID match
  2. Entity name resolution (if predicted is an ID, resolve to name)
  3. Text-based flexible matching
  4. Cross-matching (predicted text vs. gold entity names)

Updated result format:
```python
result = {
    'id': sample_id,
    'question': question,
    'gold_answers': [...],  # Text format
    'gold_entity_ids': [...],  # NEW: Entity IDs
    'predicted_answer': "entity_id (entity_name)",  # Enhanced format
    'predicted_entity_id': entity_id,  # NEW: Separate ID field
    'confidence': 0.85,
    'correct': True/False,
    'time': 1.23,
    'num_paths': 3
}
```

#### 3. `reevaluate_with_entity_mapping.py` (NEW)

Created a utility script to re-evaluate existing checkpoint files:
- Loads existing checkpoint results
- Rebuilds knowledge graphs from original dataset
- Maps gold answers to entity IDs
- Re-evaluates correctness with new mapping
- Saves updated checkpoint with comparison

**Usage:**
```bash
python reevaluate_with_entity_mapping.py test_results/test_full/checkpoint_50.json data/webqsp/test_simple.json
```

## Matching Strategies

### 1. Direct Entity ID Match
```python
if predicted == gold_entity_id:
    return True
```

### 2. Entity Name Resolution
```python
if predicted in kg.entities:
    predicted_name = kg.entities[predicted].name
    # Then match predicted_name vs gold_answers
```

### 3. Text Normalization
```python
def _normalize_text(text):
    - Convert to lowercase
    - Remove accents/diacritics
    - Remove punctuation
    - Normalize whitespace
```

### 4. Flexible Text Matching
- Exact match (normalized)
- Substring match (either direction)
- Word overlap similarity (≥50% for matching)

### 5. Entity ID Discovery
- Search KG for entities matching answer text
- Use multiple matching criteria
- Higher threshold (70%) for entity discovery

## Example Results

### Before Entity ID Mapping
```json
{
  "question": "where is jamarcus russell from",
  "gold_answers": ["Mobile"],
  "predicted_answer": "0gyh",
  "correct": false  // ❌ Can't match "Mobile" with "0gyh"
}
```

### After Entity ID Mapping
```json
{
  "question": "where is jamarcus russell from",
  "gold_answers": ["Mobile"],
  "gold_entity_ids": ["0gyh"],
  "predicted_answer": "0gyh (mobile)",
  "predicted_entity_id": "0gyh",
  "correct": true  // ✓ Entity ID match!
}
```

## Testing Workflow

### For New Tests
```bash
# Run test with entity ID mapping enabled (automatic)
python test_webqsp_eperm_optimized.py
```

The script will automatically:
1. Load samples from WebQSP dataset
2. Build knowledge graphs
3. Map gold answers to entity IDs
4. Run predictions
5. Compare using entity IDs AND text
6. Save results with full mapping information

### For Existing Checkpoints
```bash
# Re-evaluate existing checkpoint
python reevaluate_with_entity_mapping.py \
    test_results/test_full/checkpoint_50.json \
    data/webqsp/test_simple.json \
    test_results/test_full/checkpoint_50_remapped.json
```

Output shows:
- Original accuracy vs. new accuracy
- Number of changed evaluations
- Examples of changes
- Detailed statistics

## Expected Impact

### Accuracy Improvement
- **Before**: Many false negatives (correct predictions marked wrong)
- **After**: Proper entity ID matching
- **Expected**: Significant accuracy improvement (10-30% typical)

### Better Debugging
- See both entity ID and human-readable name
- Track which gold entity IDs were found
- Identify matching strategy used

### More Accurate Evaluation
- Entity ID direct match (most reliable)
- Text matching as fallback
- Multiple matching strategies reduce false negatives

## Configuration

### Entity Discovery Threshold
In `webqsp_loader.py`:
```python
similarity_threshold = 0.7  # 70% word overlap for entity discovery
```

### Text Matching Threshold
In `test_webqsp_eperm_optimized.py`:
```python
similarity_threshold = 0.5  # 50% word overlap for answer matching
```

Adjust these values based on:
- Precision vs. recall trade-off
- Dataset characteristics
- Desired strictness

## Troubleshooting

### Issue: Gold entity IDs empty
**Cause**: Answer text doesn't match any entity in KG
**Solution**: 
- Check if answer entities are in the subgraph
- Lower similarity threshold
- Verify entity name formatting

### Issue: Still showing as incorrect
**Cause**: Predicted answer is text, not entity ID
**Solution**:
- Ensure answer predictor returns entity IDs
- Check answer extraction logic
- Verify entity resolution in predictor

### Issue: Too many false positives
**Cause**: Matching threshold too low
**Solution**:
- Increase similarity threshold
- Use stricter matching criteria
- Add entity type filtering

## Future Enhancements

1. **Entity Type Filtering**: Only match entities of expected type
2. **Relation Path Verification**: Ensure answer is reachable via valid paths
3. **Multiple Answer Aggregation**: Handle multi-hop answers better
4. **Confidence Calibration**: Adjust confidence based on matching strategy
5. **Caching**: Cache entity ID mappings for faster re-evaluation

## Files Modified

1. `webqsp_loader.py` - Added entity ID mapping
2. `test_webqsp_eperm_optimized.py` - Enhanced matching logic
3. `reevaluate_with_entity_mapping.py` - NEW: Re-evaluation utility

## Summary

This enhancement enables proper evaluation of the WebQSP-EPERM system by:
- Mapping gold answers to entity IDs
- Supporting both ID and text-based matching
- Providing tools to re-evaluate existing results
- Improving debugging with detailed information

The system now correctly evaluates predictions whether they are entity IDs or human-readable text, significantly improving evaluation accuracy.
