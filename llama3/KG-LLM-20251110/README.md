# EPERM: Evidence Path Enhanced Reasoning Model

Implementation of the EPERM framework for Knowledge Graph Question Answering using local LLM API.

## Overview

This system implements the three-module architecture:

1. **Subgraph Retriever**: Extracts question-related subgraphs from knowledge graphs
2. **Evidence Path Finder**: Discovers and scores reasoning paths using LLM
3. **Answer Predictor**: Generates final answers based on weighted evidence paths

## Architecture

```
Question → Subgraph Retriever → Evidence Path Finder → Answer Predictor → Answer
              ↓                         ↓                      ↓
         KG Database              LLM Engine            LLM Engine
```

## Setup

1. Ensure your local LLM API is running (configured in `config.py`)
2. Install dependencies:
   ```bash
   pip install openai networkx numpy
   ```

3. Prepare your knowledge graph data (see `data/` folder)

## Usage

### Basic Example

```python
from eperm_system import EPERMSystem

# Initialize system
system = EPERMSystem()

# Load knowledge graph
system.load_knowledge_graph("data/sample_kg.json")

# Ask a question
answer = system.answer_question("Who is the founder of Microsoft?")
print(answer)
```

### WebQSP Dataset (Benchmark)

```bash
# Quick test with WebQSP data
python quick_webqsp_test.py

# Full WebQSP integration test
python test_webqsp_eperm.py
```

**WebQSP Features:**
- 3,000+ benchmark questions from Freebase
- Automatic KG conversion from subgraphs
- Evaluation metrics (accuracy, confidence)
- See `WEBQSP_INTEGRATION.md` for details

### Running Tests

```bash
# Test with sample KG
python test_eperm.py

# Test with WebQSP benchmark
python test_webqsp_eperm.py
```

## Configuration

Edit `config.py` to configure:
- LLM API endpoint
- Model parameters
- Retrieval settings
- Scoring weights

## Components

### Core System
- `config.py`: Configuration settings
- `knowledge_graph.py`: KG data structure and operations
- `subgraph_retriever.py`: Subgraph retrieval module
- `evidence_path_finder.py`: Evidence path discovery and scoring
- `answer_predictor.py`: Final answer generation
- `llm_client.py`: LLM API client wrapper
- `eperm_system.py`: Main orchestration system

### Testing & Examples
- `test_eperm.py`: Basic test suite with sample KG
- `example_usage.py`: Interactive demo
- `webqsp_loader.py`: WebQSP dataset loader
- `test_webqsp_eperm.py`: WebQSP integration tests
- `quick_webqsp_test.py`: Quick WebQSP test script

### Data
- `data/sample_kg.json`: Example knowledge graph
- `data/webqsp/`: WebQSP benchmark dataset (1.4M entities, 6K relations)

## Knowledge Graph Format

JSON format:
```json
{
  "entities": [
    {"id": "e1", "name": "Microsoft", "type": "Company"},
    {"id": "e2", "name": "Bill Gates", "type": "Person"}
  ],
  "relations": [
    {"head": "e2", "relation": "founded", "tail": "e1"}
  ]
}
```
