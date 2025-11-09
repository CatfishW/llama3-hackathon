"""Multi-label question type classifier."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence

import numpy as np

from kg_llm_new.logging_utils import get_logger


LOGGER = get_logger(__name__)


class QuestionType(Enum):
    """Supported question evidence granularities."""

    ONE_HOP = auto()
    TWO_HOP = auto()
    LITERAL = auto()
    DESCRIPTION = auto()

    @classmethod
    def from_label(cls, label: str) -> "QuestionType":
        mapping = {
            "one_hop": cls.ONE_HOP,
            "two_hop": cls.TWO_HOP,
            "literal": cls.LITERAL,
            "description": cls.DESCRIPTION,
        }
        try:
            return mapping[label]
        except KeyError as exc:
            raise ValueError(f"Unknown question label: {label}") from exc

    @classmethod
    def labels(cls) -> List[str]:
        return ["one_hop", "two_hop", "literal", "description"]


@dataclass
class ClassificationResult:
    """Classifier output containing probabilities and selected labels."""

    probabilities: Mapping[QuestionType, float]
    active_labels: Sequence[QuestionType]


class QuestionClassifier:
    """Multi-label classifier leveraging SentenceTransformers embeddings."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        thresholds: Mapping[QuestionType, float] | None = None,
        max_active_labels: int = 3,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "sentence-transformers is required for the default classifier. "
                "Install it via `pip install sentence-transformers` or use --no-classifier."
            ) from exc

        self.model = SentenceTransformer(model_name)
        self.thresholds = thresholds or {
            QuestionType.ONE_HOP: 0.35,
            QuestionType.TWO_HOP: 0.35,
            QuestionType.LITERAL: 0.30,
            QuestionType.DESCRIPTION: 0.25,
        }
        self.max_active_labels = max_active_labels
        self.classifier_head = None  # Placeholder for learned head weights
        self.is_fallback = False

    def load_head(self, weights_path: Path) -> None:
        """Load lightweight classifier head weights."""

        data = json.loads(Path(weights_path).read_text(encoding="utf-8"))
        self.classifier_head = {
            "weights": np.array(data["weights"], dtype=np.float32),
            "bias": np.array(data["bias"], dtype=np.float32),
        }
        LOGGER.info("Loaded classifier head weights from %s", weights_path)

    def predict(self, question: str) -> ClassificationResult:
        """Predict question types with sigmoid scoring."""

        if self.classifier_head is None:
            raise RuntimeError("Classifier head not loaded. Call load_head().")

        embedding = self.model.encode(question, convert_to_numpy=True)
        scores = embedding @ self.classifier_head["weights"].T + self.classifier_head["bias"]
        probabilities = 1.0 / (1.0 + np.exp(-scores))

        prob_map = {qt: float(probabilities[idx]) for idx, qt in enumerate(QuestionType)}
        active = [
            qt
            for qt in QuestionType
            if prob_map[qt] >= self.thresholds.get(qt, 0.5)
        ]
        # Select top-k labels if necessary
        if len(active) > self.max_active_labels:
            active = sorted(active, key=lambda qt: prob_map[qt], reverse=True)[: self.max_active_labels]

        return ClassificationResult(probabilities=prob_map, active_labels=active)

    def predict_batch(self, questions: Iterable[str]) -> List[ClassificationResult]:
        """Predict question types for a batch of questions."""

        if self.classifier_head is None:
            raise RuntimeError("Classifier head not loaded. Call load_head().")

        embeddings = self.model.encode(list(questions), convert_to_numpy=True)
        weights = self.classifier_head["weights"]
        bias = self.classifier_head["bias"]
        logits = embeddings @ weights.T + bias
        probabilities = 1.0 / (1.0 + np.exp(-logits))

        results: List[ClassificationResult] = []
        for row in probabilities:
            prob_map = {qt: float(row[idx]) for idx, qt in enumerate(QuestionType)}
            active = [
                qt
                for qt in QuestionType
                if prob_map[qt] >= self.thresholds.get(qt, 0.5)
            ]
            if len(active) > self.max_active_labels:
                active = sorted(active, key=lambda qt: prob_map[qt], reverse=True)[: self.max_active_labels]
            results.append(ClassificationResult(probabilities=prob_map, active_labels=active))
        return results

    def describe_thresholds(self) -> Mapping[str, float]:
        """Return thresholds keyed by label string."""

        return {qt.name.lower(): self.thresholds.get(qt, 0.0) for qt in QuestionType}
