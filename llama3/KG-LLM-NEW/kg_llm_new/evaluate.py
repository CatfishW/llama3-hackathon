"""Evaluation utilities for running the KG-LLM pipeline on benchmark datasets."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from kg_llm_new.cli import build_pipeline
from kg_llm_new.llm.client import LLMMode
from kg_llm_new.logging_utils import get_logger

LOGGER = get_logger(__name__)


@dataclass
class GoldExample:
    """Container holding WebQSP example data for evaluation."""

    question_id: str
    question: str
    answers: Sequence[str]
    seed_entities: Sequence[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate KG-LLM pipeline on WebQSP test set")
    parser.add_argument("--dataset", type=Path, default=Path("./WebQSP/data/WebQSP.test.json"))
    parser.add_argument("--classifier-head", type=Path)
    parser.add_argument("--mode", choices=[mode.value for mode in LLMMode], default="http")
    parser.add_argument("--server-url")
    parser.add_argument("--mqtt-broker")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--mqtt-username")
    parser.add_argument("--mqtt-password")
    parser.add_argument("--project")
    parser.add_argument("--session-id")
    parser.add_argument("--client-id")
    parser.add_argument("--model-name", default="default")
    parser.add_argument("--kg-path", type=Path)
    parser.add_argument("--no-kg", action="store_true")
    parser.add_argument("--no-classifier", action="store_true")
    parser.add_argument("--limit", type=int, help="Limit number of questions evaluated")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N questions")
    parser.add_argument("--output", type=Path, default=Path("./webqsp_predictions.json"))
    parser.add_argument("--summary", type=Path, help="Optional path for evaluation summary JSON")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between queries")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if not args.no_classifier and not args.classifier_head:
        parser.error("--classifier-head is required unless --no-classifier is set")
    return args


def load_webqsp_examples(path: Path) -> List[GoldExample]:
    data = json.loads(path.read_text(encoding="utf-8"))
    examples: List[GoldExample] = []
    for entry in data.get("Questions", []):
        question_id = str(entry.get("QuestionId", "")).strip()
        question = (
            entry.get("ProcessedQuestion")
            or entry.get("RawQuestion")
            or entry.get("Question")
            or ""
        ).strip()
        if not question_id or not question:
            continue

        valid_parses = [
            parse
            for parse in entry.get("Parses", [])
            if _is_valid_parse(parse)
        ]
        if not valid_parses:
            continue

        answers = _collect_answer_strings(valid_parses)
        seed_entities = _collect_seed_entities(valid_parses)
        examples.append(
            GoldExample(
                question_id=question_id,
                question=question,
                answers=answers,
                seed_entities=seed_entities,
            )
        )
    LOGGER.info("Loaded %d evaluable WebQSP examples", len(examples))
    return examples


def _is_valid_parse(parse: dict) -> bool:
    annot = parse.get("AnnotatorComment") or {}
    return (
        annot.get("QuestionQuality") == "Good"
        and annot.get("ParseQuality") == "Complete"
    )


def _collect_answer_strings(parses: Sequence[dict]) -> List[str]:
    answers = []
    seen = set()
    for parse in parses:
        for answer in parse.get("Answers", []) or []:
            candidate = answer.get("EntityName") or answer.get("AnswerArgument")
            if not candidate:
                continue
            candidate = str(candidate).strip()
            if candidate and candidate.lower() not in seen:
                answers.append(candidate)
                seen.add(candidate.lower())
    return answers


def _collect_seed_entities(parses: Sequence[dict]) -> List[str]:
    seeds: List[str] = []
    seen = set()
    for parse in parses:
        for key in ("TopicEntityName", "TopicEntityMid"):
            value = parse.get(key)
            if not value:
                continue
            value_str = str(value).strip()
            if value_str and value_str.lower() not in seen:
                seeds.append(value_str)
                seen.add(value_str.lower())
    return seeds


def normalize_text(text: str) -> str:
    clean = re.sub(r"[^0-9a-z]+", " ", text.lower())
    return re.sub(r"\s+", " ", clean).strip()


def normalize_digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def evaluate_predictions(
    gold: Sequence[GoldExample],
    predictions: Sequence[Tuple[str, str]],
) -> dict:
    gold_by_id = {example.question_id: example for example in gold}
    matched = 0
    metrics = []
    for question_id, answer in predictions:
        example = gold_by_id.get(question_id)
        if not example:
            continue
        success = match_answer(answer, example.answers)
        metrics.append(1.0 if success else 0.0)
        if success:
            matched += 1
    total = len(metrics)
    accuracy = statistics.mean(metrics) if metrics else 0.0
    return {
        "total": total,
        "matched": matched,
        "accuracy": accuracy,
    }


def match_answer(prediction: str, gold_answers: Sequence[str]) -> bool:
    if not gold_answers:
        return not prediction.strip()
    normalized_prediction = normalize_text(prediction)
    digit_signature = normalize_digits(prediction)
    for gold in gold_answers:
        norm_gold = normalize_text(gold)
        if norm_gold and norm_gold in normalized_prediction:
            return True
        if norm_gold and normalized_prediction in norm_gold:
            return True
        if digit_signature and digit_signature == normalize_digits(gold):
            return True
    return False


def main() -> None:
    args = parse_args()

    examples = load_webqsp_examples(args.dataset)
    if args.offset:
        examples = examples[args.offset :]
    if args.limit is not None:
        examples = examples[: args.limit]

    if not examples:
        LOGGER.error("No examples available for evaluation")
        raise SystemExit(1)

    args.question = ""
    args.entities = []

    pipeline = build_pipeline(args)

    predictions: List[dict] = []
    matched_flags: List[bool] = []

    try:
        for idx, example in enumerate(examples, start=1):
            start = time.time()
            try:
                result = pipeline.run(
                    question=example.question,
                    entities=list(example.seed_entities),
                    temperature=args.temperature,
                    top_p=args.top_p,
                    max_tokens=args.max_tokens,
                )
                answer_text = result.answer.strip()
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                LOGGER.error("Error processing %s: %s", example.question_id, exc)
                answer_text = f"ERROR: {exc}"

            matched = match_answer(answer_text, example.answers)
            matched_flags.append(matched)

            predictions.append(
                {
                    "QuestionId": example.question_id,
                    "Question": example.question,
                    "GoldAnswers": list(example.answers),
                    "Prediction": answer_text,
                    "Matched": matched,
                    "LatencyMs": (time.time() - start) * 1000,
                }
            )

            if args.sleep:
                time.sleep(args.sleep)

            if idx % 5 == 0 or idx == len(examples):
                LOGGER.info(
                    "Processed %d/%d | Rolling accuracy: %.3f",
                    idx,
                    len(examples),
                    sum(matched_flags) / len(matched_flags),
                )
    finally:
        pipeline.llm_client.close()

    args.output.write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    LOGGER.info("Saved predictions to %s", args.output)

    evaluation = evaluate_predictions(examples, [(p["QuestionId"], p["Prediction"]) for p in predictions])
    LOGGER.info(
        "Evaluation summary | total=%d matched=%d accuracy=%.3f",
        evaluation["total"],
        evaluation["matched"],
        evaluation["accuracy"],
    )

    summary_path = args.summary or args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    LOGGER.info("Saved evaluation summary to %s", summary_path)


if __name__ == "__main__":
    main()
