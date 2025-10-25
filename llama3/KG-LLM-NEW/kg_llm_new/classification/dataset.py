"""Dataset helpers for question classification training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from kg_llm_new.classification.question_classifier import QuestionType


@dataclass
class ClassificationExample:
    """Single training/evaluation example."""

    text: str
    labels: Sequence[QuestionType]
    id: str | None = None

    def to_targets(self) -> List[int]:
        targets = [0] * len(QuestionType)
        for label in self.labels:
            targets[label.value - 1] = 1  # Enum auto() starts at 1
        return targets


def load_examples(path: Path) -> List[ClassificationExample]:
    """Load examples from JSON/JSONL file."""

    entries: List[dict]
    if path.suffix == ".jsonl":
        entries = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
    else:
        entries = json.loads(Path(path).read_text(encoding="utf-8"))

    examples: List[ClassificationExample] = []
    for entry in entries:
        labels = [QuestionType.from_label(label) for label in entry["labels"]]
        examples.append(
            ClassificationExample(
                id=entry.get("id"),
                text=entry["question"],
                labels=labels,
            )
        )
    return examples


def save_examples(path: Path, rows: Iterable[dict]) -> None:
    """Persist rows to JSONL.

    Each row is expected to have at least ``question`` and ``labels`` fields.
    """

    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
