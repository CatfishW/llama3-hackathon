"""Filtering and scoring utilities for retrieved candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from kg_llm_new.logging_utils import get_logger

from ..kg.structures import KGSubgraphShard, ShardType

LOGGER = get_logger(__name__)


@dataclass
class FilterConfig:
    """Configuration for candidate filtering."""

    enable_degree_penalty: bool = True
    enable_relation_prior: bool = True
    enable_type_compatibility: bool = True
    max_items_per_type: int = 12


class CandidateFilter:
    """Apply lightweight filtering heuristics over shards."""

    def __init__(self, config: FilterConfig | None = None) -> None:
        self.config = config or FilterConfig()

    def filter_shards(self, shards: Sequence[KGSubgraphShard]) -> List[KGSubgraphShard]:
        """Apply heuristics to reduce redundant candidates."""

        filtered: List[KGSubgraphShard] = []
        for shard in shards:
            if not shard.items:
                continue
            items = list(shard.items)
            if self.config.max_items_per_type:
                items = items[: self.config.max_items_per_type]
            filtered.append(KGSubgraphShard(shard.shard_type, items))
        return filtered
