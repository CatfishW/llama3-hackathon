# Knowledge Graph Subgraph Classification

This repository contains scripts for classifying and analyzing subgraphs from knowledge graphs. The classification system identifies four types of subgraphs based on their structural and semantic properties.

## Subgraph Types

### 1. One-hop Subgraph
- **Definition**: Direct connections from a central entity
- **Characteristics**: All triples where the entity appears as either subject or object
- **Use case**: Understanding immediate relationships and properties

### 2. Two-hop Subgraph  
- **Definition**: Connections within 2 hops from a central entity
- **Characteristics**: Includes entities connected through one intermediate entity
- **Use case**: Exploring extended context and indirect relationships

### 3. Description Subgraph
- **Definition**: Subgraphs containing descriptive/narrative information
- **Characteristics**: Predicates indicating descriptions, summaries, abstracts, etc.
- **Use case**: Extracting textual descriptions and documentation

### 4. Literal Subgraph
- **Definition**: Subgraphs with literal values (strings, numbers, dates)
- **Characteristics**: Simple factual information, measurements, identifiers
- **Use case**: Extracting structured data and facts

## Files

### Core Components

- **`kg_loader.py`**: Knowledge graph loading and basic operations
- **`subgraph_classifier.py`**: Basic subgraph classification functionality
- **`enhanced_subgraph_classifier.py`**: Advanced classification with batch processing and analytics
- **`demo_subgraph_classification.py`**: Demonstration and interactive exploration

### Data Files
- **`rogkg_triples.tsv.gz`**: Compressed knowledge graph triples
- **`rogkg_alias_map.json`**: Entity alias mappings

## Usage Examples

### Basic Classification

```bash
# Analyze a specific entity
python subgraph_classifier.py --triples rogkg_triples.tsv.gz --alias rogkg_alias_map.json --entity "Berlin"

# Search for entities and analyze the first match
python subgraph_classifier.py --triples rogkg_triples.tsv.gz --search "Disney" --show-triples 5

# Limit data for quick testing
python subgraph_classifier.py --triples rogkg_triples.tsv.gz --limit 1000 --entity "Berlin"
```

### Enhanced Analytics

```bash
# Analyze top entities by degree
python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --batch-top 10

# Generate comprehensive report
python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --batch-top 5 --report analysis_report.json

# Export to CSV for spreadsheet analysis
python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --batch-top 10 --csv results.csv

# Analyze predicate distribution
python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --predicate-analysis

# Find entities with rich subgraphs
python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --rich-subgraphs

# Find similar entities
python enhanced_subgraph_classifier.py --triples rogkg_triples.tsv.gz --entity "Berlin" --similarity Berlin
```

### Interactive Exploration

```bash
# Run demo with all examples
python demo_subgraph_classification.py

# Interactive mode
python demo_subgraph_classification.py interactive
```

## Interactive Commands

In interactive mode, you can use these commands:

- `search <pattern>` - Search for entities matching pattern
- `analyze <entity>` - Analyze subgraphs for an entity
- `top [n]` - Show top n entities by degree
- `similar <entity>` - Find entities with similar subgraph patterns
- `help` - Show available commands
- `quit` - Exit

## Output Formats

### Console Output
- Statistical summaries for each subgraph type
- Sample triples with subject → predicate → object format
- Predicate distribution analysis
- Entity similarity scores

### JSON Report
```json
{
  "entity": "entity_name",
  "classifications": {
    "one_hop": {
      "triples": [...],
      "statistics": {...}
    },
    "two_hop": {...},
    "description": {...},
    "literal": {...}
  }
}
```

### CSV Export
Columns: entity, subgraph_type, total_triples, unique_predicates, unique_subjects, unique_objects, literal_objects, description_predicates, literal_predicates

## Classification Algorithms

### Literal Detection
- Numbers: Regular expressions for numeric patterns
- Dates: Pattern matching for date formats
- Simple strings: Short text without complex structure
- URLs: Web address patterns

### Description Detection
- Predicate keywords: description, summary, abstract, overview, note, comment
- Content indicators: caption, text, content, details, biography

### Literal Predicate Detection
- Attribute keywords: name, title, label, alias, id, code
- Measurement keywords: age, height, weight, price, value, amount
- Temporal keywords: date, time, year

### Path Analysis
- BFS-based shortest path finding
- Configurable maximum depth limits
- Cycle detection and prevention

## Advanced Features

### Similarity Analysis
- Vector-based entity signatures
- Cosine similarity calculation
- Subgraph pattern comparison

### Batch Processing
- Multiple entity analysis
- Progress tracking
- Memory-efficient processing

### Statistical Analysis
- Degree distribution
- Predicate frequency analysis
- Subgraph type distribution
- Coverage statistics

## Requirements

```bash
pip install pandas pyarrow
```

## Performance Notes

- Use `--limit` parameter for quick testing with large datasets
- Two-hop subgraphs have configurable size limits to prevent memory issues
- Batch processing includes progress indicators for large entity sets

## Examples of Use Cases

1. **Question Answering**: Use one-hop and two-hop subgraphs to find relevant information for entity-centric questions

2. **Knowledge Graph Summarization**: Extract description subgraphs to create entity summaries

3. **Data Quality Assessment**: Analyze literal subgraphs to identify data completeness and quality issues

4. **Entity Linking**: Use similarity analysis to find related entities for disambiguation

5. **Schema Analysis**: Examine predicate distributions to understand knowledge graph structure

## Customization

### Adding New Subgraph Types
Extend the `SubgraphClassifier` class and implement new classification methods following the existing pattern.

### Modifying Detection Patterns
Update the predicate keyword sets and regular expressions in the classifier initialization.

### Custom Similarity Metrics
Override the `_calculate_signature_similarity` method to implement alternative similarity measures.

## Troubleshooting

### Common Issues

1. **File not found**: Ensure data files are in the correct directory
2. **Memory issues**: Use `--limit` parameter to reduce dataset size
3. **Empty results**: Try different entity names or search patterns
4. **Encoding issues**: Files are expected to be UTF-8 encoded

### Performance Optimization

1. **Large datasets**: Process in batches and use appropriate limits
2. **Complex entities**: Set maximum display limits for output
3. **Memory constraints**: Process subsets and combine results

For more detailed examples and advanced usage, see the demo script output and interactive exploration mode.
