from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kg_llm_new.classification.question_classifier import ClassificationResult, QuestionType
from kg_llm_new.cli import _FallbackClassifier, _build_classifier
from kg_llm_new.config import PipelineConfig
from kg_llm_new.llm.client import LLMClientConfig, LLMMode
from kg_llm_new.pipeline import KGPipeline


class DummyClassifier:
    """Minimal classifier stub for tests."""

    def predict(self, question: str) -> ClassificationResult:
        probabilities = {qt: 0.05 for qt in QuestionType}
        probabilities[QuestionType.LITERAL] = 0.9
        return ClassificationResult(
            probabilities=probabilities,
            active_labels=[QuestionType.LITERAL],
        )


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


@pytest.fixture
def kg_config(tmp_path: Path) -> PipelineConfig:
    write_jsonl(
        tmp_path / "literal.jsonl",
        [
            {
                "entity": "Tom Hanks",
                "relation": "date_of_birth",
                "value": "1956-07-09",
            }
        ],
    )
    for name in ("one_hop.jsonl", "two_hop.jsonl", "description.jsonl"):
        (tmp_path / name).write_text("", encoding="utf-8")

    config = PipelineConfig()
    config.storage.base_dir = tmp_path
    config.storage.kg_path = tmp_path
    config.enable_latency_logging = False
    config.resolve()
    return config


def test_kg_only_returns_literal_value(kg_config: PipelineConfig) -> None:
    pipeline = KGPipeline(
        config=kg_config,
        classifier=DummyClassifier(),
        llm_client_config=LLMClientConfig(mode=LLMMode.KG_ONLY),
        use_kg=True,
    )

    result = pipeline.run(
        question="When was Tom Hanks born?",
        entities=["Tom Hanks"],
    )

    assert "1956-07-09" in result.answer
    assert "kg-only" in result.answer.lower()
    assert result.evidence_tokens > 0


def test_kg_only_handles_missing_evidence(kg_config: PipelineConfig) -> None:
    pipeline = KGPipeline(
        config=kg_config,
        classifier=DummyClassifier(),
        llm_client_config=LLMClientConfig(mode=LLMMode.KG_ONLY),
        use_kg=True,
    )

    result = pipeline.run(
        question="What is the capital of France?",
        entities=["France"],
    )

    assert result.answer.lower().startswith("no knowledge retrieved")
    assert result.evidence_tokens == 0


def test_kg_only_requires_retrieval(tmp_path: Path) -> None:
    config = PipelineConfig()
    config.storage.base_dir = tmp_path
    config.storage.kg_path = tmp_path
    config.resolve()

    with pytest.raises(ValueError):
        KGPipeline(
            config=config,
            classifier=DummyClassifier(),
            llm_client_config=LLMClientConfig(mode=LLMMode.KG_ONLY),
            use_kg=False,
        )


def test_fallback_classifier_uses_full_budgets(kg_config: PipelineConfig) -> None:
    fallback = _FallbackClassifier()
    pipeline = KGPipeline(
        config=kg_config,
        classifier=fallback,
        llm_client_config=LLMClientConfig(mode=LLMMode.KG_ONLY),
        use_kg=True,
        rebalance_budgets=False,
    )

    classification = fallback.predict("Check budgets")
    budgets = pipeline._derive_budgets(classification.active_labels)

    assert set(budgets.keys()) == set(classification.active_labels)
    assert budgets[QuestionType.ONE_HOP] == pipeline.config.retriever.budget.one_hop
    assert budgets[QuestionType.TWO_HOP] == pipeline.config.retriever.budget.two_hop
    assert budgets[QuestionType.LITERAL] == pipeline.config.retriever.budget.literal
    assert budgets[QuestionType.DESCRIPTION] == pipeline.config.retriever.budget.description


def test_build_classifier_requires_head_when_enabled() -> None:
    args = SimpleNamespace(no_classifier=False, classifier_head=None)
    with pytest.raises(SystemExit):
        _build_classifier(args)
