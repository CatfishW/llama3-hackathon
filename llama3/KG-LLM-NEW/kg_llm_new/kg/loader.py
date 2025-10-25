"""Utilities for loading and constructing knowledge graph shards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from kg_llm_new.logging_utils import get_logger

from .structures import (
    KGDescription,
    KGLiteral,
    KGPath2,
    KGTriple,
    KnowledgeGraphStore,
)

LOGGER = get_logger(__name__)


class KnowledgeGraphLoader:
    """Load KG resources from JSONL/JSON dumps."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = Path(base_path)

    def load(self) -> KnowledgeGraphStore:
        store = KnowledgeGraphStore()
        loaders = [
            ("one_hop.jsonl", self._load_one_hop, store.add_one_hop),
            ("two_hop.jsonl", self._load_two_hop, store.add_two_hop),
            ("literal.jsonl", self._load_literal, store.add_literal),
            ("description.jsonl", self._load_description, store.add_description),
        ]
        for filename, parser, adder in loaders:
            path = self.base_path / filename
            if not path.exists():
                LOGGER.warning("KG shard %s missing; skipping", path)
                continue
            count = 0
            for entity, obj in parser(path):
                adder(entity, obj)
                count += 1
            LOGGER.info("Loaded %s items from %s", count, path)
        LOGGER.info("KG summary: %s", store.summary())
        return store

    def _iter_jsonl(self, path: Path) -> Iterable[Mapping[str, object]]:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def _load_one_hop(self, path: Path) -> Iterable[tuple[str, KGTriple]]:
        for record in self._iter_jsonl(path):
            entity = str(record["entity"])
            triple = KGTriple(
                head=str(record.get("head", entity)),
                relation=str(record["relation"]),
                tail=str(record["tail"]),
            )
            yield entity, triple

    def _load_two_hop(self, path: Path) -> Iterable[tuple[str, KGPath2]]:
        for record in self._iter_jsonl(path):
            entity = str(record["entity"])
            path_obj = KGPath2(
                head=str(record["head"]),
                relation1=str(record["relation1"]),
                middle=str(record["middle"]),
                relation2=str(record["relation2"]),
                tail=str(record["tail"]),
            )
            yield entity, path_obj

    def _load_literal(self, path: Path) -> Iterable[tuple[str, KGLiteral]]:
        for record in self._iter_jsonl(path):
            entity = str(record["entity"])
            literal = KGLiteral(
                entity=str(record.get("entity", entity)),
                relation=str(record["relation"]),
                value=str(record["value"]),
            )
            yield entity, literal

    def _load_description(self, path: Path) -> Iterable[tuple[str, KGDescription]]:
        for record in self._iter_jsonl(path):
            entity = str(record["entity"])
            description = KGDescription(
                entity=entity,
                text=str(record.get("text") or record.get("description", "")),
            )
            yield entity, description
