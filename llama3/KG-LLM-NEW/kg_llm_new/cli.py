"""Command-line interface for KG-LLM pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from kg_llm_new.classification.question_classifier import QuestionClassifier, QuestionType
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
    parser.add_argument("--classifier-head", type=Path, required=True, help="Path to classifier head weights JSON")
    parser.add_argument("--kg-path", type=Path, help="Path to KG shards directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def build_pipeline(args: argparse.Namespace) -> KGPipeline:
    config = default_config()
    if args.kg_path:
        config.storage.kg_path = args.kg_path
        config.resolve()

    setup_logging(config.storage.logs_dir, level=(10 if args.debug else 20))
    LOGGER.info("Using config: %s", config)

    classifier = QuestionClassifier()
    classifier.load_head(args.classifier_head)

    llm_config = LLMClientConfig(mode=LLMMode(args.mode))
    if llm_config.mode == LLMMode.HTTP:
        llm_config.server_url = args.server_url
    else:
        llm_config.mqtt_broker = args.mqtt_broker
        llm_config.mqtt_port = args.mqtt_port
        llm_config.mqtt_username = args.mqtt_username
        llm_config.mqtt_password = args.mqtt_password

    return KGPipeline(config=config, classifier=classifier, llm_client_config=llm_config)


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
