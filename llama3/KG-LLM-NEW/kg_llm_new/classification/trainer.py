"""Training utilities for multi-label question classifier head."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sentence_transformers import SentenceTransformer

from kg_llm_new.classification.dataset import ClassificationExample
from kg_llm_new.classification.question_classifier import QuestionType
from kg_llm_new.logging_utils import get_logger

LOGGER = get_logger(__name__)


@dataclass
class TrainingConfig:
    """Hyper-parameters for classifier head training."""

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    learning_rate: float = 0.0  # Placeholder for compatibility
    max_iter: int = 1000
    c: float = 1.0
    seed: int = 42


@dataclass
class TrainingArtifacts:
    """Artifacts produced by training."""

    weights: np.ndarray  # shape: (num_labels, embedding_dim)
    bias: np.ndarray  # shape: (num_labels,)

    def save_json(self, path: Path) -> None:
        payload = {
            "weights": self.weights.tolist(),
            "bias": self.bias.tolist(),
        }
        Path(path).write_text(json.dumps(payload), encoding="utf-8")


def encode_examples(model: SentenceTransformer, examples: Sequence[ClassificationExample]) -> np.ndarray:
    texts = [ex.text for ex in examples]
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=True)


def train_head(
    examples: Sequence[ClassificationExample],
    config: TrainingConfig | None = None,
    validation_examples: Sequence[ClassificationExample] | None = None,
    output_path: Path | None = None,
) -> TrainingArtifacts:
    config = config or TrainingConfig()
    model = SentenceTransformer(config.model_name)
    embeddings = encode_examples(model, examples)

    label_sequences = [[label.name for label in ex.labels] for ex in examples]
    mlb = MultiLabelBinarizer(classes=[label.name for label in QuestionType])
    targets = mlb.fit_transform(label_sequences)

    classifier = OneVsRestClassifier(
        LogisticRegression(
            max_iter=config.max_iter,
            C=config.c,
            class_weight="balanced",
            random_state=config.seed,
        )
    )
    classifier.fit(embeddings, targets)

    weights = np.vstack([estimator.coef_ for estimator in classifier.estimators_])
    bias = np.array([estimator.intercept_[0] for estimator in classifier.estimators_])
    artifacts = TrainingArtifacts(weights=weights, bias=bias)

    if output_path:
        artifacts.save_json(output_path)
        LOGGER.info("Saved classifier head to %s", output_path)

    if validation_examples:
        evaluate_head(model, artifacts, validation_examples)

    return artifacts


def evaluate_head(
    model: SentenceTransformer,
    artifacts: TrainingArtifacts,
    examples: Sequence[ClassificationExample],
) -> dict:
    embeddings = encode_examples(model, examples)
    logits = embeddings @ artifacts.weights.T + artifacts.bias
    probabilities = 1 / (1 + np.exp(-logits))
    predictions = (probabilities >= 0.5).astype(int)

    label_sequences = [[label.name for label in ex.labels] for ex in examples]
    mlb = MultiLabelBinarizer(classes=[label.name for label in QuestionType])
    targets = mlb.fit_transform(label_sequences)

    true_positive = (predictions & targets).sum(axis=0)
    predicted_positive = predictions.sum(axis=0)
    actual_positive = targets.sum(axis=0)

    precision = np.divide(true_positive, predicted_positive, out=np.zeros_like(true_positive, dtype=float), where=predicted_positive != 0)
    recall = np.divide(true_positive, actual_positive, out=np.zeros_like(true_positive, dtype=float), where=actual_positive != 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(precision, dtype=float), where=(precision + recall) != 0)

    metrics = {
        "precision": precision.tolist(),
        "recall": recall.tolist(),
        "f1": f1.tolist(),
        "support": actual_positive.tolist(),
        "macro_f1": float(f1.mean()),
    }
    LOGGER.info("Validation macro-F1: %.3f", metrics["macro_f1"])
    return metrics
