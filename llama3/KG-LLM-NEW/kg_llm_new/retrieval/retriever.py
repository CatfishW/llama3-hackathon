"""Label-conditioned retriever implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from rank_bm25 import BM25Okapi

from kg_llm_new.logging_utils import get_logger

from ..classification.question_classifier import QuestionType
from ..kg.structures import KGSubgraphShard, ShardType
from .filters import CandidateFilter, FilterConfig

LOGGER = get_logger(__name__)


@dataclass
class RetrievalRequest:
    """Retriever input."""

    question: str
    entities: Sequence[str]
    active_labels: Sequence[QuestionType]
    budgets: Mapping[QuestionType, int]


@dataclass
class RetrievalResult:
    """Retriever output."""

    shards: List[KGSubgraphShard]


class Retriever:
    """Hybrid BM25-based retriever with label-conditioned shards."""

    def __init__(
        self,
        store,
        lexical_weight: float = 0.6,
        semantic_weight: float = 0.4,
        filter_config: FilterConfig | None = None,
    ) -> None:
        self.store = store
        self.lexical_weight = lexical_weight
        self.semantic_weight = semantic_weight
        self.filter = CandidateFilter(filter_config)
        self._bm25_indices: Dict[ShardType, BM25Okapi] = {}
        self._bm25_corpus: Dict[ShardType, List[str]] = {}
        self._bm25_entities: Dict[ShardType, List[str]] = {}
        self._build_bm25_indices()

    def _build_bm25_indices(self) -> None:
        """Build BM25 indices lazily for each shard type."""

        for shard_type in ShardType:
            corpus: List[str] = []
            entities: List[str] = []
            for entity in self.store.entities():
                shard = self.store.get_shard(entity, shard_type)
                if not shard.items:
                    continue
                for line in shard.textualize():
                    corpus.append(line.lower().split())
                    entities.append(entity)
            if corpus:
                self._bm25_indices[shard_type] = BM25Okapi(corpus)
                self._bm25_corpus[shard_type] = [" ".join(tokens) for tokens in corpus]
                self._bm25_entities[shard_type] = entities
                LOGGER.info("BM25 index built for %s with %d entries", shard_type, len(corpus))

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Retrieve shards based on active labels and entity seeds."""

        shards: List[KGSubgraphShard] = []
        for label in request.active_labels:
            shard_type = self._map_label(label)
            budget = request.budgets.get(label, 0)
            if budget <= 0:
                continue
            shard_candidates = self._retrieve_shard_type(
                question=request.question,
                shard_type=shard_type,
                entities=request.entities,
                k=budget,
            )
            shards.extend(shard_candidates)
        filtered = self.filter.filter_shards(shards)
        return RetrievalResult(shards=filtered)

    def _retrieve_shard_type(
        self,
        question: str,
        shard_type: ShardType,
        entities: Sequence[str],
        k: int,
    ) -> Sequence[KGSubgraphShard]:
        index = self._bm25_indices.get(shard_type)
        if not index:
            return []
        tokenized_query = question.lower().split()
        scores = index.get_scores(tokenized_query)
        # Sort by score descending and gather unique entities respecting budget
        ranked = sorted(
            enumerate(scores),
            key=lambda item: item[1],
            reverse=True,
        )
        selected_entities: List[str] = []
        shards: List[KGSubgraphShard] = []
        for idx, score in ranked:
            entity = self._bm25_entities[shard_type][idx]
            if entities and entity not in entities:
                continue
            if entity in selected_entities:
                continue
            shard = self.store.get_shard(entity, shard_type)
            if not shard.items:
                continue
            selected_entities.append(entity)
            shards.append(shard)
            if len(selected_entities) >= k:
                break
        return shards

    @staticmethod
    def _map_label(label: QuestionType) -> ShardType:
        mapping = {
            QuestionType.ONE_HOP: ShardType.ONE_HOP,
            QuestionType.TWO_HOP: ShardType.TWO_HOP,
            QuestionType.LITERAL: ShardType.LITERAL,
            QuestionType.DESCRIPTION: ShardType.DESCRIPTION,
        }
        return mapping[label]
