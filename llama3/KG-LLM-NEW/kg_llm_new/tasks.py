"""Task-oriented CLI for data preparation and training."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence

from kg_llm_new.classification.dataset import load_examples, save_examples
from kg_llm_new.classification.question_classifier import QuestionClassifier, QuestionType
from kg_llm_new.classification.trainer import TrainingConfig, train_head
from kg_llm_new.kg import (
    FirebaseDownloadConfig,
    FirebaseDownloader,
    FirebaseFilter,
    FirebaseProcessor,
    FreebaseEasyShardBuilder,
)
from kg_llm_new.data.webqsp import load_webqsp_dataset, prepare_webqsp_examples
from kg_llm_new.logging_utils import get_logger, setup_logging

LOGGER = get_logger(__name__)


def cmd_prepare_webqsp(args: argparse.Namespace) -> None:
    examples = load_webqsp_dataset(args.input)
    rows = prepare_webqsp_examples(examples)
    save_examples(args.output, rows)
    label_counter = Counter()
    combo_counter = Counter()
    for row in rows:
        label_counter.update(row["labels"])
        combo_counter.update([tuple(sorted(row["labels"]))])
    LOGGER.info("Prepared %d classification rows", len(rows))
    LOGGER.info("Label distribution: %s", dict(label_counter))
    top_combos = combo_counter.most_common(5)
    LOGGER.info("Top label combinations: %s", top_combos)


def cmd_train_classifier(args: argparse.Namespace) -> None:
    train_examples = load_examples(args.train)
    val_examples = load_examples(args.val) if args.val else []
    config = TrainingConfig(model_name=args.model_name, max_iter=args.max_iter, c=args.c)
    train_head(
        train_examples,
        config=config,
        validation_examples=val_examples if val_examples else None,
        output_path=args.output,
    )


def cmd_evaluate_classifier(args: argparse.Namespace) -> None:
    classifier = QuestionClassifier(model_name=args.model_name)
    classifier.load_head(args.head)
    examples = load_examples(args.data)

    label_indices = {label: idx for idx, label in enumerate(QuestionType)}
    true_positive = [0] * len(QuestionType)
    predicted_positive = [0] * len(QuestionType)
    actual_positive = [0] * len(QuestionType)

    for example in examples:
        prediction = classifier.predict(example.text)
        predicted_set = set(prediction.active_labels)
        true_set = set(example.labels)
        for label in QuestionType:
            idx = label_indices[label]
            if label in predicted_set:
                predicted_positive[idx] += 1
            if label in true_set:
                actual_positive[idx] += 1
            if label in predicted_set and label in true_set:
                true_positive[idx] += 1

    metrics = {}
    f1_scores = []
    for label in QuestionType:
        idx = label_indices[label]
        precision = (
            true_positive[idx] / predicted_positive[idx]
            if predicted_positive[idx]
            else 0.0
        )
        recall = (
            true_positive[idx] / actual_positive[idx]
            if actual_positive[idx]
            else 0.0
        )
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        f1_scores.append(f1)
        metrics[label.name.lower()] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": actual_positive[idx],
        }

    metrics["macro_f1"] = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    LOGGER.info("Evaluation results: %s", metrics)


def _parse_where_clauses(where_args: Sequence[Sequence[str]] | None) -> Sequence[FirebaseFilter]:
    if not where_args:
        return []
    filters: List[FirebaseFilter] = []
    for field, op, raw_value in where_args:
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        filters.append(FirebaseFilter(field, op, value))
    return filters


def cmd_prepare_freebase_easy(args: argparse.Namespace) -> None:
    root_path = args.root.resolve() if args.root else None
    facts_path = args.facts.resolve() if args.facts else None
    if not facts_path and root_path:
        facts_path = root_path / "facts.txt"
    if not facts_path or not facts_path.exists():
        raise FileNotFoundError("facts.txt not found; provide --facts or --root with extracted files")

    scores_path = None
    if not args.skip_scores:
        if args.scores:
            scores_path = args.scores.resolve()
        elif root_path:
            candidate = root_path / "scores.txt"
            if candidate.exists():
                scores_path = candidate

    languages = args.languages if args.languages else ["en"]
    builder = FreebaseEasyShardBuilder(
        facts_path=facts_path,
        output_dir=args.output_dir.resolve(),
        scores_path=scores_path,
        languages=languages,
        include_all_languages=args.allow_all_languages,
        description_predicates=args.description_predicates or ["/common/topic/description"],
        name_predicates=args.name_predicates or ["/type/object/name"],
        alias_predicates=args.alias_predicates or ["/common/topic/alias"],
        literal_predicates=args.literal_predicates or [],
        include_scores=not args.skip_scores,
        score_relation=args.score_relation,
        max_facts=args.max_facts,
    )
    result = builder.build()
    LOGGER.info("Freebase Easy shard counts: %s", result.counts)
    LOGGER.info("Shard files: %s", {k: str(v) for k, v in result.paths.items()})


def cmd_download_firebase(args: argparse.Namespace) -> None:
    filters = _parse_where_clauses(args.where)
    config = FirebaseDownloadConfig(
        credentials_path=args.credentials,
        project_id=args.project,
        collection=args.collection,
        filters=filters,
        limit=args.limit,
        select_fields=args.select or (),
    )
    downloader = FirebaseDownloader(config)
    documents = downloader.download()
    processor = FirebaseProcessor(args.output_dir)

    if not args.no_raw:
        processor.write_documents(documents, args.raw_filename)

    if args.process_shards:
        paths = processor.process_to_shards(documents)
        LOGGER.info("Shard files written: %s", {k: str(v) for k, v in paths.items()})


def cmd_process_firebase(args: argparse.Namespace) -> None:
    raw_path = args.input
    documents: List[Dict[str, object]] = []
    with raw_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            documents.append(json.loads(line))
    processor = FirebaseProcessor(args.output_dir)
    paths = processor.process_to_shards(documents)
    LOGGER.info("Shard files written: %s", {k: str(v) for k, v in paths.items()})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KG-LLM tasks")
    subparsers = parser.add_subparsers(dest="command")

    prepare = subparsers.add_parser("prepare-webqsp", help="Convert WebQSP JSON to classification JSONL")
    prepare.add_argument("--input", type=Path, required=True, help="Path to WebQSP JSON file")
    prepare.add_argument("--output", type=Path, required=True, help="Output JSONL path")
    prepare.set_defaults(func=cmd_prepare_webqsp)

    prepare_fb_easy = subparsers.add_parser(
        "prepare-freebase-easy",
        help="Convert Freebase Easy TSV dumps into KG shard JSONL files",
    )
    prepare_fb_easy.add_argument("--root", type=Path, help="Directory containing the extracted Freebase Easy files")
    prepare_fb_easy.add_argument("--facts", type=Path, help="Path to facts.txt (overrides --root)")
    prepare_fb_easy.add_argument("--scores", type=Path, help="Path to scores.txt (overrides --root)")
    prepare_fb_easy.add_argument("--output-dir", type=Path, required=True, help="Directory where shard JSONL files will be written")
    prepare_fb_easy.add_argument("--max-facts", type=int, help="Limit the number of facts processed (useful for sampling)")
    prepare_fb_easy.add_argument("--languages", nargs="*", help="Languages to keep for textual literals (default: en)")
    prepare_fb_easy.add_argument(
        "--allow-all-languages",
        action="store_true",
        help="Keep literals regardless of the language tag",
    )
    prepare_fb_easy.add_argument(
        "--description-predicate",
        dest="description_predicates",
        action="append",
        help="Predicate to treat as description (repeatable)",
    )
    prepare_fb_easy.add_argument(
        "--name-predicate",
        dest="name_predicates",
        action="append",
        help="Predicate to treat as name literal (repeatable)",
    )
    prepare_fb_easy.add_argument(
        "--alias-predicate",
        dest="alias_predicates",
        action="append",
        help="Predicate to treat as alias literal (repeatable)",
    )
    prepare_fb_easy.add_argument(
        "--literal-predicate",
        dest="literal_predicates",
        action="append",
        help="Additional predicate to treat as literal (repeatable)",
    )
    prepare_fb_easy.add_argument(
        "--skip-scores",
        action="store_true",
        help="Skip ingesting scores.txt even if present",
    )
    prepare_fb_easy.add_argument(
        "--score-relation",
        default="__score__",
        help="Relation label to use when writing scores (default: __score__)",
    )
    prepare_fb_easy.set_defaults(func=cmd_prepare_freebase_easy)

    train = subparsers.add_parser("train-classifier", help="Train classifier head")
    train.add_argument("--train", type=Path, required=True, help="Training JSON/JSONL path")
    train.add_argument("--val", type=Path, help="Validation JSON/JSONL path")
    train.add_argument("--output", type=Path, required=True, help="Output classifier head JSON")
    train.add_argument("--model-name", default="sentence-transformers/all-MiniLM-L6-v2")
    train.add_argument("--max-iter", type=int, default=1000)
    train.add_argument("--c", type=float, default=1.0)
    train.set_defaults(func=cmd_train_classifier)

    evaluate = subparsers.add_parser("evaluate-classifier", help="Evaluate classifier head on labeled data")
    evaluate.add_argument("--head", type=Path, required=True, help="Classifier head JSON")
    evaluate.add_argument("--data", type=Path, required=True, help="Labeled JSON/JSONL dataset")
    evaluate.add_argument("--model-name", default="sentence-transformers/all-MiniLM-L6-v2")
    evaluate.set_defaults(func=cmd_evaluate_classifier)

    download_fb = subparsers.add_parser("download-firebase", help="Download Firestore documents to JSONL")
    download_fb.add_argument("--credentials", type=Path, required=True, help="Service account credentials JSON")
    download_fb.add_argument("--collection", required=True, help="Firestore collection path")
    download_fb.add_argument("--project", help="Firebase project ID (optional)")
    download_fb.add_argument("--output-dir", type=Path, required=True)
    download_fb.add_argument("--limit", type=int, help="Maximum number of documents to fetch")
    download_fb.add_argument(
        "--where",
        action="append",
        nargs=3,
        metavar=("FIELD", "OP", "VALUE"),
        help="Add Firestore where clause (value parsed as JSON when possible)",
    )
    download_fb.add_argument(
        "--select",
        action="append",
        help="Field to project in results (can be repeated)",
    )
    download_fb.add_argument(
        "--raw-filename",
        default="firebase_raw.jsonl",
        help="Filename for raw dump inside output directory",
    )
    download_fb.add_argument(
        "--no-raw",
        action="store_true",
        help="Skip writing the raw document dump",
    )
    download_fb.add_argument(
        "--process-shards",
        action="store_true",
        help="Immediately split documents into shard JSONL files",
    )
    download_fb.set_defaults(func=cmd_download_firebase)

    process_fb = subparsers.add_parser("process-firebase", help="Process raw Firebase dump into shard files")
    process_fb.add_argument("--input", type=Path, required=True, help="Raw firebase JSONL")
    process_fb.add_argument("--output-dir", type=Path, required=True, help="Output directory for shard files")
    process_fb.set_defaults(func=cmd_process_firebase)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return
    setup_logging(Path("./logs"), level=20)
    args.func(args)


if __name__ == "__main__":
    main()
