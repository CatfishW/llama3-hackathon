"""Configuration models for the KG-LLM pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from kg_llm_new.kg.firebase import FirebaseFilter

DEFAULT_PROJECT_NAME = "kg_llm_new"


@dataclass
class StorageConfig:
    """Paths for persisted assets."""

    base_dir: Path = Path("./storage")
    kg_path: Optional[Path] = None
    cache_dir: Path = Path("./cache")
    logs_dir: Path = Path("./logs")

    def resolve(self) -> "StorageConfig":
        self.base_dir = self.base_dir.expanduser().resolve()
        self.cache_dir = (self.cache_dir or self.base_dir / "cache").expanduser().resolve()
        self.logs_dir = (self.logs_dir or self.base_dir / "logs").expanduser().resolve()
        if self.kg_path:
            self.kg_path = self.kg_path.expanduser().resolve()
        return self


@dataclass
class RetrievalBudget:
    """Budget allocation for each evidence granularity."""

    one_hop: int = 8
    two_hop: int = 6
    literal: int = 6
    description: int = 3
    max_tokens: int = 1536


@dataclass
class ClassificationThresholds:
    """Thresholds for activating composite labels."""

    one_hop: float = 0.35
    two_hop: float = 0.35
    literal: float = 0.30
    description: float = 0.25
    max_active_labels: int = 3


@dataclass
class RetrieverConfig:
    """Retriever hyper-parameters."""

    budget: RetrievalBudget = field(default_factory=RetrievalBudget)
    thresholds: ClassificationThresholds = field(default_factory=ClassificationThresholds)
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    semantic_weight: float = 0.4
    lexical_weight: float = 0.6
    enable_degree_penalty: bool = True
    enable_relation_prior: bool = True
    enable_type_compatibility: bool = True


@dataclass
class PromptConfig:
    """Prompt assembly configuration."""

    system_prompt: str = (
        "You are a grounded assistant. Use only supplied knowledge snippets to answer."
    )
    max_context_messages: int = 8
    token_allocation: Dict[str, int] = field(
        default_factory=lambda: {
            "instructions": 256,
            "question": 128,
            "evidence": 1024,
            "metadata": 128,
        }
    )


@dataclass
class FirebaseConfig:
    """Optional Firebase ingestion settings."""

    enabled: bool = False
    credentials_path: Optional[Path] = None
    project_id: Optional[str] = None
    collection: Optional[str] = None
    limit: Optional[int] = None
    select_fields: List[str] = field(default_factory=list)
    filters: List[Dict[str, object]] = field(default_factory=list)
    output_dir: Path = Path("./firebase_export")
    process_shards: bool = True

    def to_filters(self) -> List[FirebaseFilter]:
        parsed: List[FirebaseFilter] = []
        for item in self.filters:
            if not {"field", "op", "value"} <= set(item.keys()):
                continue
            parsed.append(
                FirebaseFilter(
                    field_path=str(item["field"]),
                    operator=str(item["op"]),
                    value=item["value"],
                )
            )
        return parsed

    def resolve(self) -> "FirebaseConfig":
        if self.credentials_path:
            self.credentials_path = self.credentials_path.expanduser().resolve()
        self.output_dir = self.output_dir.expanduser().resolve()
        return self


@dataclass
class FreebaseEasyConfig:
    """Optional Freebase Easy ingestion settings."""

    enabled: bool = False
    root_path: Optional[Path] = None
    facts_path: Optional[Path] = None
    scores_path: Optional[Path] = None
    # Parquet file paths (higher priority than .txt files)
    facts_parquet_path: Optional[Path] = None
    scores_parquet_path: Optional[Path] = None
    use_parquet: bool = True  # Prefer Parquet if available
    chunk_size: int = 100000  # Batch size for Parquet processing
    output_dir: Path = Path("./freebase_easy")
    max_facts: Optional[int] = None
    languages: List[str] = field(default_factory=lambda: ["en"])
    include_all_languages: bool = False
    description_predicates: List[str] = field(default_factory=lambda: ["/common/topic/description"])
    name_predicates: List[str] = field(default_factory=lambda: ["/type/object/name"])
    alias_predicates: List[str] = field(default_factory=lambda: ["/common/topic/alias"])
    literal_predicates: List[str] = field(default_factory=list)
    include_scores: bool = True
    score_relation: str = "__score__"

    def resolve(self) -> "FreebaseEasyConfig":
        root: Optional[Path] = None
        if self.root_path:
            root = self.root_path.expanduser().resolve()
            self.root_path = root
        
        # Try to find Parquet files first if use_parquet is True
        if self.use_parquet:
            if self.facts_parquet_path:
                self.facts_parquet_path = self.facts_parquet_path.expanduser().resolve()
            elif root:
                candidate = root / "facts.parquet"
                if candidate.exists():
                    self.facts_parquet_path = candidate
            
            if self.scores_parquet_path:
                self.scores_parquet_path = self.scores_parquet_path.expanduser().resolve()
            elif root:
                candidate = root / "scores.parquet"
                if candidate.exists():
                    self.scores_parquet_path = candidate
        
        # Fallback to .txt files
        if self.facts_path:
            self.facts_path = self.facts_path.expanduser().resolve()
        elif root and not self.facts_parquet_path:
            candidate = root / "facts.txt"
            if candidate.exists():
                self.facts_path = candidate
        
        if self.scores_path:
            self.scores_path = self.scores_path.expanduser().resolve()
        elif root and not self.scores_parquet_path:
            candidate = root / "scores.txt"
            if candidate.exists():
                self.scores_path = candidate
        
        self.output_dir = self.output_dir.expanduser().resolve()
        return self


@dataclass
class PipelineConfig:
    """Top-level pipeline configuration."""

    storage: StorageConfig = field(default_factory=StorageConfig)
    retriever: RetrieverConfig = field(default_factory=RetrieverConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    firebase: FirebaseConfig = field(default_factory=FirebaseConfig)
    freebase_easy: FreebaseEasyConfig = field(default_factory=FreebaseEasyConfig)
    project_name: str = DEFAULT_PROJECT_NAME
    enable_latency_logging: bool = True
    default_temperature: float = 0.1
    default_top_p: float = 0.9
    request_timeout: int = 120

    def resolve(self) -> "PipelineConfig":
        self.storage = self.storage.resolve()
        self.firebase = self.firebase.resolve()
        self.freebase_easy = self.freebase_easy.resolve()
        return self


@dataclass
class DatasetConfig:
    """Configuration stub for dataset splits."""

    name: str
    question_path: Path
    split: str = "test"


def default_config() -> PipelineConfig:
    """Return a resolved default configuration instance."""

    return PipelineConfig().resolve()
