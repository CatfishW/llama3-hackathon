"""
Example configuration for using Parquet files with KG-LLM-NEW.

This configuration shows how to use the converted Parquet files
instead of the large text files for faster and more memory-efficient processing.
"""

from pathlib import Path
from kg_llm_new.config import PipelineConfig, FreebaseEasyConfig, StorageConfig

# Example 1: Using Parquet files (recommended for large datasets)
def get_parquet_config():
    """Configuration using Parquet files for Freebase Easy data."""
    
    config = PipelineConfig(
        storage=StorageConfig(
            base_dir=Path("./storage"),
            kg_path=Path("./freebase_easy_shards"),  # Where JSONL shards will be saved
        ),
        freebase_easy=FreebaseEasyConfig(
            enabled=True,
            # Point to the directory containing your Parquet files
            root_path=Path("./freebase-easy-latest"),
            # Or specify individual files explicitly:
            # facts_parquet_path=Path("./freebase-easy-latest/facts.parquet"),
            # scores_parquet_path=Path("./freebase-easy-latest/scores.parquet"),
            
            # Use Parquet files (default: True)
            use_parquet=True,
            
            # Chunk size for processing (adjust based on your RAM)
            chunk_size=100000,  # Process 100k rows at a time (safe for 8GB+ RAM)
            # chunk_size=50000,  # Use for 4GB RAM
            # chunk_size=200000, # Use for 16GB+ RAM
            
            # Output directory for processed JSONL shards
            output_dir=Path("./freebase_easy_shards"),
            
            # Optional: Limit number of facts for testing
            # max_facts=1000000,  # Process only first 1M facts
            max_facts=None,  # Process all facts
            
            # Language filtering
            languages=["en"],  # Only English
            include_all_languages=False,
            
            # Include prominence scores
            include_scores=True,
            
            # Predicate classification
            description_predicates=["/common/topic/description"],
            name_predicates=["/type/object/name"],
            alias_predicates=["/common/topic/alias"],
        ),
    )
    
    return config.resolve()


# Example 2: Fallback to text files (if Parquet not available)
def get_text_config():
    """Configuration using original text files (slower, more memory intensive)."""
    
    config = PipelineConfig(
        storage=StorageConfig(
            base_dir=Path("./storage"),
            kg_path=Path("./freebase_easy_shards"),
        ),
        freebase_easy=FreebaseEasyConfig(
            enabled=True,
            root_path=Path("./freebase-easy-latest"),
            use_parquet=False,  # Disable Parquet, use text files
            output_dir=Path("./freebase_easy_shards"),
            max_facts=None,
            languages=["en"],
            include_scores=True,
        ),
    )
    
    return config.resolve()


# Example 3: Testing with limited data
def get_test_config():
    """Configuration for testing with a subset of data."""
    
    config = PipelineConfig(
        storage=StorageConfig(
            base_dir=Path("./storage_test"),
            kg_path=Path("./freebase_easy_test"),
        ),
        freebase_easy=FreebaseEasyConfig(
            enabled=True,
            root_path=Path("./freebase-easy-latest"),
            use_parquet=True,
            chunk_size=50000,
            output_dir=Path("./freebase_easy_test"),
            max_facts=500000,  # Only process first 500k facts for quick testing
            languages=["en"],
            include_scores=False,  # Skip scores for faster testing
        ),
    )
    
    return config.resolve()


# Example 4: Using with automatic detection
def get_auto_config():
    """Configuration that auto-detects available files (Parquet or text)."""
    
    config = PipelineConfig(
        storage=StorageConfig(
            base_dir=Path("./storage"),
        ),
        freebase_easy=FreebaseEasyConfig(
            enabled=True,
            # Just point to the directory - it will auto-detect .parquet or .txt files
            root_path=Path("./freebase-easy-latest"),
            use_parquet=True,  # Prefer Parquet if available
            chunk_size=100000,
            output_dir=Path("./freebase_easy_shards"),
        ),
    )
    
    return config.resolve()


if __name__ == "__main__":
    # Example usage
    print("Example 1: Parquet Configuration")
    print("=" * 80)
    config = get_parquet_config()
    print(f"Facts Parquet: {config.freebase_easy.facts_parquet_path}")
    print(f"Scores Parquet: {config.freebase_easy.scores_parquet_path}")
    print(f"Output Dir: {config.freebase_easy.output_dir}")
    print(f"Chunk Size: {config.freebase_easy.chunk_size}")
    print()
    
    print("Example 2: Auto-Detection Configuration")
    print("=" * 80)
    config = get_auto_config()
    print(f"Use Parquet: {config.freebase_easy.use_parquet}")
    print(f"Root Path: {config.freebase_easy.root_path}")
    print(f"Facts Parquet: {config.freebase_easy.facts_parquet_path}")
    print(f"Facts Text: {config.freebase_easy.facts_path}")
