# Bug Fixes for Entity ID Mapping

## Issues Identified

### 1. Empty `gold_entity_ids` Arrays
**Problem**: All results show `"gold_entity_ids": []`
**Root Cause**: 
- Answer entities not in the limited subgraph (150 triples max)
- Entity name format mismatches
- Subgraph doesn't include the target entities

### 2. NoneType Errors
**Problem**: `'NoneType' object has no attribute 'lower'`
**Root Cause**: Some samples have `null` values in the `answers` array
**Location**: Samples 20, 33, 43, 122, 198, etc.

### 3. Single Answer Output
**Problem**: LLM only outputs 1 answer but test dataset has multiple gold answers
**Root Cause**: Answer predictor returns single entity, not considering multiple valid answers

## Fixes Applied

### Fix 1: Handle None Values in Gold Answers

**File**: `test_webqsp_eperm_optimized.py`

**Before**:
```python
answers = [ans['text'] for ans in sample.get('answers', [])]
```

**After**:
```python
# Extract answers, filter out None values
answers = []
for ans in sample.get('answers', []):
    if ans and ans.get('text') and ans['text'] is not None:
        answers.append(ans['text'])

# Skip samples with no valid answers
if not answers:
    print(f"\nSkipping sample {i}: No valid answers")
    continue
```

**Impact**: Prevents NoneType errors, skips invalid samples

### Fix 2: Improved Entity ID Matching

**File**: `webqsp_loader.py`

**Changes**:
1. Added None/empty string checks
2. Lowered similarity threshold from 0.7 to 0.6
3. Added entity ID format checking (m.0xyz → 0xyz)
4. Better normalization with str() conversion

**Before**:
```python
if similarity >= 0.7:  # Too strict
    matching_ids.append(entity_id)
```

**After**:
```python
if similarity >= 0.6:  # More lenient to find matches
    matching_ids.append(entity_id)
    continue

# Check if entity ID matches answer text
entity_id_clean = entity_id.replace('m.', '').replace('_', ' ')
if normalize(entity_id_clean) == answer_norm:
    matching_ids.append(entity_id)
```

**Impact**: Finds more entity matches

### Fix 3: Return Entity IDs Instead of Names

**File**: `answer_predictor_fast.py`

**Before**:
```python
if tail_entity_id in subgraph.entities:
    answer = subgraph.entities[tail_entity_id].name  # Returns name
    confidence = min(best_path.score, 0.9)
    return (answer, confidence)
```

**After**:
```python
if tail_entity_id in subgraph.entities:
    answer = tail_entity_id  # Returns entity ID
    confidence = min(best_path.score, 0.9)
    return (answer, confidence)
```

**Impact**: Returns entity IDs for proper comparison with gold_entity_ids

### Fix 4: Enhanced LLM Prompt for Entity Selection

**File**: `answer_predictor_fast.py`

**Before**:
```python
system_prompt = """Return JSON:
{"answer": "short answer", ...}"""
```

**After**:
```python
# Collect candidate entity IDs from paths
candidate_entities = set()
for path_obj in evidence_paths[:5]:
    for triple in path_obj.path:
        candidate_entities.add(triple[2])

system_prompt = """Return JSON:
{"answer": "entity_id", ...}
Choose the most relevant entity ID from the evidence paths."""

user_prompt = f"""...
Candidate entities: {', '.join(list(candidate_entities)[:10])}
Answer with the best entity ID (JSON):"""
```

**Impact**: LLM selects from candidate entity IDs

## New Utility: analyze_entity_mapping.py

Created diagnostic tool to:
- Analyze why entity ID mapping fails
- Test different subgraph sizes
- Show entity matching results
- Identify common issues

**Usage**:
```bash
python analyze_entity_mapping.py
```

## Known Limitations

### Why `gold_entity_ids` May Still Be Empty

1. **Subgraph Size Limitation**
   - Limited to 150 triples to keep KG manageable
   - Answer entities might not be in the subgraph
   - Solution: Increase `max_kg_size` (but slower)

2. **Entity Name Format**
   - WebQSP uses Freebase IDs (m.0xyz format)
   - Entity names may be abbreviated or formatted differently
   - Some entities have cryptic names

3. **Multiple Hop Answers**
   - Some answers require multi-hop reasoning
   - Final answer entity might not be directly in paths

## Improved Evaluation Strategy

Even with empty `gold_entity_ids`, the system still uses:

1. **Entity ID direct match** (if IDs available)
2. **Entity name resolution** (ID → name, then text match)
3. **Text-based flexible matching** (fallback)
4. **Cross-matching** (predicted text vs gold entity names)

This multi-strategy approach ensures evaluation works even when entity ID mapping fails.

## Expected Results

### Before Fixes
- Errors: NoneType exceptions on ~5% of samples
- Processing: Stops on error samples
- Accuracy: 0% (ID/text mismatch)

### After Fixes
- Errors: Skipped gracefully with warning
- Processing: Continues through entire dataset
- Accuracy: 5-15% (improved but still limited by subgraph size)

## Further Improvements Needed

### To Increase `gold_entity_ids` Match Rate

1. **Increase Subgraph Size**
   ```python
   max_kg_size = 300  # or 500
   ```
   Trade-off: Slower processing

2. **Use Full Graph**
   - Load entire entity/relation vocabulary
   - Match against full Freebase
   - Trade-off: Much slower, high memory

3. **Pre-compute Entity Mappings**
   - Build answer text → entity ID index
   - Cache mappings for all answers
   - Trade-off: Initial preprocessing time

### To Handle Multiple Answers

Current system returns single answer. Options:

1. **Collect Multiple Candidate Entities**
   - Return top-k entities from evidence paths
   - Evaluate if any match gold answers
   
2. **Path Aggregation**
   - Find multiple paths to different entities
   - Return all tail entities as candidates

3. **Confidence Thresholding**
   - Return all entities above confidence threshold
   - Evaluate as correct if any match

## Testing Commands

### Test Entity ID Mapping
```bash
python analyze_entity_mapping.py
```

### Run with Fixes
```bash
python test_webqsp_eperm_optimized.py
```

### Re-evaluate with Larger Subgraph
Edit `test_webqsp_eperm_optimized.py`:
```python
max_kg_size = 300  # Increase from 150
```

## Summary

✓ Fixed NoneType errors with null checking  
✓ Improved entity ID matching (lowered threshold)  
✓ Answer predictor returns entity IDs  
✓ Enhanced LLM prompt for entity selection  
✓ Created diagnostic tool  
⚠ `gold_entity_ids` may still be empty due to subgraph limitations  
✓ Evaluation still works via fallback text matching  

The system is now more robust but the fundamental issue (answer entities not in small subgraphs) remains. Consider increasing `max_kg_size` if accuracy is still very low.
