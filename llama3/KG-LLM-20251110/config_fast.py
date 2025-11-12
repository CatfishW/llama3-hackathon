"""Fast configuration for optimized testing.

This config reduces:
- Subgraph sizes
- Path lengths
- Number of paths
- LLM temperature (faster, more consistent)
"""

import os

# LLM API Configuration
LLM_CONFIG = {
    "api_key": os.getenv("TEST_API_KEY", "sk-local-abc"),
    "base_url": os.getenv("TEST_BASE_URL", "http://173.61.35.162:25565/v1"),
    "model": os.getenv("TEST_MODEL", "qwen3-30b-a3b-instruct"),
    "temperature": 0.2,  # Lower for faster, more consistent responses
    "max_tokens": 1000,  # Reduced for faster generation
}

# Subgraph Retriever Configuration
RETRIEVER_CONFIG = {
    "max_subgraph_size": 30,  # Reduced for speed
    "max_hops": 2,
    "min_relevance_score": 0.3,
}

# Evidence Path Finder Configuration (Fast)
PATH_FINDER_CONFIG = {
    "max_paths": 5,  # Reduced from 10
    "max_path_length": 3,  # Reduced from 5
    "score_weights": {
        "relevance": 0.4,
        "confidence": 0.3,
        "coherence": 0.3,
    }
}

# Answer Predictor Configuration (Fast)
PREDICTOR_CONFIG = {
    "top_k_paths": 3,  # Reduced from 5
    "min_confidence": 0.5,
}

# System Configuration (Performance Mode)
SYSTEM_CONFIG = {
    "verbose": False,  # Disabled for batch processing
    "cache_enabled": True,  # Keep cache for efficiency
    "timeout": 15,  # Shorter timeout
}
