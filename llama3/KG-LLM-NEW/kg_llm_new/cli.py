"""Command-line interface for KG-LLM pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Sequence

from kg_llm_new.classification.question_classifier import (
    ClassificationResult,
    QuestionClassifier,
    QuestionType,
)
from kg_llm_new.config import PipelineConfig, default_config
from kg_llm_new.llm.client import LLMClientConfig, LLMMode
from kg_llm_new.logging_utils import get_logger, setup_logging
from kg_llm_new.pipeline import KGPipeline

LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KG-Enhanced LLM Pipeline")
    parser.add_argument("question", help="Question to answer")
    parser.add_argument("entities", nargs="*", help="Seed entities for retrieval")
    parser.add_argument("--mode", choices=[m.value for m in LLMMode], default="http")
    parser.add_argument("--server-url", help="HTTP llama.cpp server URL")
    parser.add_argument("--mqtt-broker", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-username")
    parser.add_argument("--mqtt-password")
    parser.add_argument("--project", help="Project/topic name for MQTT mode")
    parser.add_argument("--session-id", help="Override session identifier for MQTT mode")
    parser.add_argument("--client-id", help="Override MQTT client identifier")
    parser.add_argument("--model-name", default="default", help="Model name for HTTP chat completions")
    parser.add_argument("--classifier-head", type=Path, help="Path to classifier head weights JSON")
    parser.add_argument("--kg-path", type=Path, help="Path to KG shards directory")
    parser.add_argument("--no-kg", action="store_true", help="Disable KG retrieval and use pure LLM mode")
    parser.add_argument("--no-classifier", action="store_true", help="Skip loading the SentenceTransformer classifier and use default label priors")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def build_pipeline(args: argparse.Namespace) -> KGPipeline:
    config = default_config()
    if args.kg_path:
        config.storage.kg_path = args.kg_path
        config.resolve()

    if args.project:
        config.project_name = args.project

    setup_logging(config.storage.logs_dir, level=(10 if args.debug else 20))
    LOGGER.info("Using config: %s", config)

    classifier = _build_classifier(args)
    rebalance_budgets = not getattr(classifier, "is_fallback", False)

    llm_config = LLMClientConfig(mode=LLMMode(args.mode))
    llm_config.project = config.project_name
    llm_config.model_name = args.model_name
    if args.session_id:
        llm_config.session_id = args.session_id
    if args.client_id:
        llm_config.client_id = args.client_id
    if llm_config.mode == LLMMode.HTTP:
        if not args.server_url:
            raise SystemExit("--server-url is required when mode=http")
        llm_config.server_url = args.server_url
    elif llm_config.mode == LLMMode.MQTT:
        if not args.mqtt_broker:
            raise SystemExit("--mqtt-broker is required when mode=mqtt")
        llm_config.mqtt_broker = args.mqtt_broker
        llm_config.mqtt_port = args.mqtt_port
        llm_config.mqtt_username = args.mqtt_username
        llm_config.mqtt_password = args.mqtt_password
    else:
        if args.server_url or args.mqtt_broker:
            LOGGER.warning(
                "kg-only mode ignores HTTP/MQTT connection parameters. "
                "Use --no-classifier with mode=http or mode=mqtt to keep the LLM backend engaged."
            )
        if args.no_kg:
            raise SystemExit("--kg-only mode cannot be combined with --no-kg")

    return KGPipeline(
        config=config,
        classifier=classifier,
        llm_client_config=llm_config,
        use_kg=not args.no_kg,
        rebalance_budgets=rebalance_budgets,
    )


def _build_classifier(args: argparse.Namespace):
    if args.no_classifier:
        return _FallbackClassifier()

    if not args.classifier_head:
        raise SystemExit("--classifier-head is required unless --no-classifier is set")

    classifier = QuestionClassifier()
    classifier.load_head(args.classifier_head)
    setattr(classifier, "is_fallback", False)
    return classifier


class _FallbackClassifier:
    """Lightweight classifier that avoids SentenceTransformer dependency."""

    def __init__(self) -> None:
        self.is_fallback = True

    def load_head(self, weights_path: Path) -> None:
        LOGGER.warning("--no-classifier set; ignoring classifier head at %s", weights_path)

    def predict(self, question: str) -> ClassificationResult:
        priors = {qt: 1.0 / len(QuestionType) for qt in QuestionType}
        return ClassificationResult(probabilities=priors, active_labels=list(QuestionType))

    def predict_batch(self, questions: Sequence[str]) -> List[ClassificationResult]:
        return [self.predict(q) for q in questions]


def main() -> None:
    args = parse_args()
    pipeline = build_pipeline(args)
    try:
        result = pipeline.run(question=args.question, entities=args.entities)
        print("Answer:\n", result.answer)
        print("Latency (ms):", f"{result.latency_ms:.1f}")
        print("Active labels:", ", ".join(label.name for label in result.active_labels))
    finally:
        pipeline.llm_client.close()


if __name__ == "__main__":
    main()
