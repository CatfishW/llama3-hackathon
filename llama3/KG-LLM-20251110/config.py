"""Configuration for EPERM system."""

import os

# LLM API Configuration
LLM_CONFIG = {
    "api_key": os.getenv("TEST_API_KEY", "sk-local-abc"),
    "base_url": os.getenv("TEST_BASE_URL", "http://173.61.35.162:25565/v1"),
    "model": os.getenv("TEST_MODEL", "qwen3-30b-a3b-instruct"),
    "temperature": 0.7,
    "max_tokens": 2000,
}

# Subgraph Retriever Configuration
RETRIEVER_CONFIG = {
    "max_subgraph_size": 50,  # Maximum number of nodes in subgraph
    "max_hops": 2,  # Maximum distance from seed entities
    "min_relevance_score": 0.3,  # Minimum relevance threshold
}

# Evidence Path Finder Configuration
PATH_FINDER_CONFIG = {
    "max_paths": 10,  # Maximum number of paths to consider
    "max_path_length": 5,  # Maximum length of reasoning paths
    "score_weights": {
        "relevance": 0.4,
        "confidence": 0.3,
        "coherence": 0.3,
    }
}

# Answer Predictor Configuration
PREDICTOR_CONFIG = {
    "top_k_paths": 5,  # Use top-k evidence paths for prediction
    "min_confidence": 0.5,  # Minimum confidence for answer
}

# System Configuration
SYSTEM_CONFIG = {
    "verbose": True,  # Print detailed logs
    "cache_enabled": True,  # Cache LLM responses
    "timeout": 30,  # Request timeout in seconds
}
