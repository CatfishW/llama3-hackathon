"""Knowledge graph shard data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Sequence, Tuple


class ShardType(str, Enum):
    """Supported shard granularities."""

    ONE_HOP = "one_hop"
    TWO_HOP = "two_hop"
    LITERAL = "literal"
    DESCRIPTION = "description"


@dataclass
class KGTriple:
    """Simple triple representation."""

    head: str
    relation: str
    tail: str

    def textualize(self) -> str:
        return f"{self.head} {self.relation} {self.tail}"


@dataclass
class KGLiteral:
    """Literal property triple."""

    entity: str
    relation: str
    value: str

    def textualize(self) -> str:
        return f"{self.entity} {self.relation} {self.value}"


@dataclass
class KGDescription:
    """Entity description snippet."""

    entity: str
    text: str

    def textualize(self) -> str:
        return f"{self.entity}: {self.text}"


@dataclass
class KGPath2:
    """Length-two relational path."""

    head: str
    relation1: str
    middle: str
    relation2: str
    tail: str

    def textualize(self) -> str:
        return f"{self.head} {self.relation1} {self.middle}; {self.middle} {self.relation2} {self.tail}"


@dataclass
class KGSubgraphShard:
    """Shard containing homogeneous knowledge items."""

    shard_type: ShardType
    items: Sequence[object] = field(default_factory=list)

    def textualize(self) -> List[str]:
        lines: List[str] = []
        for item in self.items:
            if hasattr(item, "textualize"):
                lines.append(item.textualize())
            else:
                lines.append(str(item))
        return lines


class KnowledgeGraphStore:
    """In-memory store for knowledge shards scoped by entity."""

    def __init__(self) -> None:
        self.one_hop: Dict[str, List[KGTriple]] = {}
        self.two_hop: Dict[str, List[KGPath2]] = {}
        self.literal: Dict[str, List[KGLiteral]] = {}
        self.description: Dict[str, List[KGDescription]] = {}

    def add_one_hop(self, entity: str, triple: KGTriple) -> None:
        self.one_hop.setdefault(entity, []).append(triple)

    def add_two_hop(self, entity: str, path: KGPath2) -> None:
        self.two_hop.setdefault(entity, []).append(path)

    def add_literal(self, entity: str, literal: KGLiteral) -> None:
        self.literal.setdefault(entity, []).append(literal)

    def add_description(self, entity: str, description: KGDescription) -> None:
        self.description.setdefault(entity, []).append(description)

    def get_shard(self, entity: str, shard_type: ShardType) -> KGSubgraphShard:
        if shard_type == ShardType.ONE_HOP:
            return KGSubgraphShard(ShardType.ONE_HOP, self.one_hop.get(entity, []))
        if shard_type == ShardType.TWO_HOP:
            return KGSubgraphShard(ShardType.TWO_HOP, self.two_hop.get(entity, []))
        if shard_type == ShardType.LITERAL:
            return KGSubgraphShard(ShardType.LITERAL, self.literal.get(entity, []))
        if shard_type == ShardType.DESCRIPTION:
            return KGSubgraphShard(ShardType.DESCRIPTION, self.description.get(entity, []))
        raise KeyError(f"Unsupported shard type: {shard_type}")

    def entities(self) -> Iterable[str]:
        seen = set(self.one_hop.keys())
        seen.update(self.two_hop.keys())
        seen.update(self.literal.keys())
        seen.update(self.description.keys())
        return seen

    def summary(self) -> Dict[str, int]:
        return {
            "one_hop": sum(len(v) for v in self.one_hop.values()),
            "two_hop": sum(len(v) for v in self.two_hop.values()),
            "literal": sum(len(v) for v in self.literal.values()),
            "description": sum(len(v) for v in self.description.values()),
        }
