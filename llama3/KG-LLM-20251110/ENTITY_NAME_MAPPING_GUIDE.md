# Entity Name Mapping Guide

This guide explains how to use the comprehensive entity name mapping system to make knowledge graphs more human-readable.

## Overview

The WebQSP dataset contains entity IDs (Freebase IDs like `m.03_r3`) and their corresponding human-readable names (like "Jamaica") in the answer fields. We extract these mappings from all dataset files to create a comprehensive mapping file.

## Files

- **`build_entity_name_map.py`** - Extracts kb_id→text mappings from all WebQSP files
- **`data/webqsp/entity_name_map.json`** - The comprehensive mapping file (38,184+ entities)
- **`test_entity_name_map.py`** - Demonstrates the functionality

## Building the Mapping File

Run the builder script to create/update the mapping file:

```bash
python build_entity_name_map.py
```

This will:
1. Read `train_simple.json`, `dev_simple.json`, and `test_simple.json`
2. Extract all kb_id→text pairs from the answer fields
3. Save to `data/webqsp/entity_name_map.json`

**Result:** 38,184+ unique entity mappings extracted from the entire dataset.

## Using the Mapping

### Method 1: Load mapping into KnowledgeGraph

```python
from knowledge_graph import KnowledgeGraph

# Create or load a knowledge graph
kg = KnowledgeGraph()
# ... add entities and relations ...

# Load the comprehensive mapping
kg.load_entity_name_map("data/webqsp/entity_name_map.json")

# Convert to text with human-readable names
print(kg.to_text())
```

### Method 2: Using with WebQSP Loader

```python
from webqsp_loader import WebQSPLoader

loader = WebQSPLoader()

# Load a sample
sample = loader.load_sample("data/webqsp/test_simple.json", 0)

# Create KG
kg = loader.sample_to_kg(sample, limit_size=100)

# Load comprehensive mapping
kg.load_entity_name_map()

# Now to_text() will use human-readable names
text = kg.to_text()
```

### Method 3: Automatic with qa_dataset

The WebQSPLoader already extracts answer-based mappings when creating QA datasets:

```python
qa_dataset = loader.create_qa_dataset(
    "data/webqsp/test_simple.json",
    num_samples=10
)

# Each KG has entity_name_map from answers
for qa_item in qa_dataset:
    kg = qa_item['kg']
    # Optionally load comprehensive mapping for better coverage
    kg.load_entity_name_map()
    print(kg.to_text())
```

## Benefits

### Before (without mapping):
```
Entities:
  - 03_r3 (Entity)
  - 0160w (Entity)
  - 0kbws (Entity)

Relations:
  - 03_r3 --[location.location.adjoin_s]--> 0160w
```

### After (with mapping):
```
Entities:
  - Jamaica [kb_id: m.03_r3] (Entity)
  - Bahamas [kb_id: m.0160w] (Entity)
  - 2008 Summer Olympics [kb_id: m.0kbws] (Entity)

Relations:
  - Jamaica --[location.location.adjoin_s]--> Bahamas
```

## Coverage Statistics

- **Total unique entities mapped:** 38,184
- **Average text length:** 27.6 characters
- **Coverage in typical KG:** 10-25% of entities (varies by question)

The mapping covers the most important entities (answers and related entities), making knowledge graphs significantly more interpretable.

## Updating the Mapping

If you add new data files or modify existing ones:

```bash
python build_entity_name_map.py
```

This will rebuild the mapping file with all available data.

## Technical Details

### Mapping Priority

When multiple texts exist for the same kb_id, the builder keeps the **longest text** to ensure maximum information.

### Fallback Behavior

The `to_text()` method gracefully handles missing mappings:
1. First tries `entity_name_map[kb_id]`
2. Falls back to `entity.name`
3. Falls back to `entity.id` if entity not found

### Integration with EPERM System

The entity name mapping integrates seamlessly with:
- Evidence path formatting
- LLM prompt generation
- Answer prediction
- Result analysis

Just call `kg.load_entity_name_map()` before any text conversion operations.
