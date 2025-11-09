"""End-to-end pipeline orchestrating the KG-enhanced LLM workflow."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from kg_llm_new.logging_utils import get_logger

from .classification.question_classifier import QuestionClassifier, QuestionType
from .config import PipelineConfig
from .kg.firebase import FirebaseDownloadConfig, FirebaseDownloader, FirebaseProcessor
from .kg.freebase import FreebaseEasyShardBuilder
from .kg.freebase_parquet import ParquetFreebaseEasyShardBuilder
from .kg.loader import KnowledgeGraphLoader
from .kg.structures import (
    KGDescription,
    KGLiteral,
    KGPath2,
    KGSubgraphShard,
    KGTriple,
    ShardType,
)
from .llm.client import LLMClient, LLMClientConfig, LLMMode
from .prompt import PromptBuilder
from .retrieval.retriever import RetrievalRequest, RetrievalResult, Retriever

LOGGER = get_logger(__name__)


@dataclass
class PipelineOutput:
    """Container for pipeline results."""

    answer: str
    latency_ms: float
    evidence_tokens: int
    active_labels: Sequence[QuestionType]


class KGPipeline:
    """Top-level orchestrator for KG-enhanced reasoning."""

    def __init__(
        self,
        config: PipelineConfig,
        classifier: QuestionClassifier,
        llm_client_config: LLMClientConfig,
        use_kg: bool = True,
        rebalance_budgets: bool = True,
    ) -> None:
        self.config = config
        self.classifier = classifier
        self.use_kg = use_kg
        self.mode = llm_client_config.mode
        self.rebalance_budgets = rebalance_budgets
        if self.mode == LLMMode.KG_ONLY and not self.use_kg:
            raise ValueError("KG-only mode requires knowledge retrieval; disable --no-kg")
        self.prompt_builder = PromptBuilder(config.prompt.system_prompt)
        if self.use_kg:
            self._prepare_knowledge()
            base_path = config.storage.kg_path or config.storage.base_dir
            self.store = KnowledgeGraphLoader(base_path).load()
            self.retriever = Retriever(
                store=self.store,
                lexical_weight=config.retriever.lexical_weight,
                semantic_weight=config.retriever.semantic_weight,
            )
        else:
            self.store = None
            self.retriever = None
        self.llm_client = LLMClient(llm_client_config)

    def run(
        self,
        question: str,
        entities: Sequence[str],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
    ) -> PipelineOutput:
        start_time = time.time()
        classification = self.classifier.predict(question)
        retrieval_result: Optional[RetrievalResult] = None
        prompt_bundle = None
        if self.use_kg and self.retriever is not None:
            budgets = self._derive_budgets(classification.active_labels)
            retrieval_request = RetrievalRequest(
                question=question,
                entities=entities,
                active_labels=classification.active_labels,
                budgets=budgets,
            )
            retrieval_result = self.retriever.retrieve(retrieval_request)
            if self.mode != LLMMode.KG_ONLY:
                prompt_bundle = self.prompt_builder.build(
                    question=question,
                    shards=retrieval_result.shards,
                    label_probabilities=classification.probabilities,
                )
        if prompt_bundle is None and self.mode != LLMMode.KG_ONLY:
            prompt_bundle = self.prompt_builder.build_simple(
                question=question,
                label_probabilities=classification.probabilities,
            )
        if self.mode == LLMMode.KG_ONLY:
            answer, evidence_tokens = self._build_kg_only_answer(question, retrieval_result)
        else:
            answer = self.llm_client.generate(
                messages=prompt_bundle.messages,
                temperature=temperature or self.config.default_temperature,
                top_p=top_p or self.config.default_top_p,
                max_tokens=max_tokens or self.config.retriever.budget.max_tokens,
            )
            evidence_tokens = prompt_bundle.evidence_tokens
        latency_ms = (time.time() - start_time) * 1000
        if self.config.enable_latency_logging:
            LOGGER.info(
                "Pipeline completed in %.1f ms | labels=%s | evidence_tokens=%d | use_kg=%s",
                latency_ms,
                [label.name for label in classification.active_labels],
                evidence_tokens,
                self.use_kg,
            )
        return PipelineOutput(
            answer=answer,
            latency_ms=latency_ms,
            evidence_tokens=evidence_tokens,
            active_labels=classification.active_labels,
        )

    def _derive_budgets(self, active_labels: Sequence[QuestionType]) -> Mapping[QuestionType, int]:
        budget = self.config.retriever.budget
        mapping = {
            QuestionType.ONE_HOP: budget.one_hop,
            QuestionType.TWO_HOP: budget.two_hop,
            QuestionType.LITERAL: budget.literal,
            QuestionType.DESCRIPTION: budget.description,
        }
        # Simple rebalancing: divide budget among active labels if > 0
        if active_labels:
            if self.rebalance_budgets:
                scale = max(1, len(active_labels))
                return {label: max(1, mapping[label] // scale) for label in active_labels}
            return {label: mapping[label] for label in active_labels}
        return mapping

    def _build_kg_only_answer(
        self,
        question: str,
        retrieval_result: Optional[RetrievalResult],
    ) -> Tuple[str, int]:
        """Compose a KG-only response by ranking textualized shard items."""
        if not self.use_kg:
            return ("KG-only mode requested but knowledge retrieval is disabled.", 0)
        if retrieval_result is None or not retrieval_result.shards:
            return (f"No knowledge retrieved for question: {question}", 0)

        question_tokens = set(self._tokenize(question))
        candidates: List[dict[str, object]] = []
        for shard in retrieval_result.shards:
            lines = shard.textualize()
            for idx, line in enumerate(lines):
                tokens = self._tokenize(line)
                token_set = set(tokens)
                overlap = len(question_tokens & token_set) if question_tokens else 0
                score = float(overlap) * self._kg_type_bonus(shard.shard_type)
                candidates.append(
                    {
                        "score": score,
                        "overlap": overlap,
                        "shard_type": shard.shard_type,
                        "item": shard.items[idx],
                        "text": line,
                        "tokens": tokens,
                    }
                )

        if not candidates:
            return (f"Retrieved shards contained no textual evidence for question: {question}", 0)

        candidates.sort(
            key=lambda entry: (
                float(entry["score"]),
                int(entry["overlap"]),
                - len(entry["tokens"]),
            ),
            reverse=True,
        )

        best = candidates[0]
        primary_line = self._render_item_text(best["shard_type"], best["item"])
        best_score = float(best["score"])
        if best_score <= 0:
            main_answer = (
                "KG-only mode could not align evidence directly with the question. "
                "Most relevant snippet:\n"
                + primary_line
            )
        else:
            main_answer = self._render_primary_answer(best["shard_type"], best["item"])

        support_limit = min(5, len(candidates))
        seen_lines: set[str] = set()
        token_total = 0
        support_lines: List[str] = []
        for entry in candidates[:support_limit]:
            formatted = self._render_item_text(entry["shard_type"], entry["item"])
            if formatted in seen_lines:
                continue
            seen_lines.add(formatted)
            token_total += len(entry["tokens"])
            if formatted == primary_line:
                continue
            support_lines.append(formatted)

        answer = main_answer
        if support_lines:
            support_block = "\n".join(f"- {line}" for line in support_lines)
            answer = f"{main_answer}\n\nSupporting evidence:\n{support_block}"

        return (answer, token_total)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[0-9A-Za-z_]+", text.lower())

    @staticmethod
    def _kg_type_bonus(shard_type: ShardType) -> float:
        if shard_type == ShardType.LITERAL:
            return 1.5
        if shard_type == ShardType.ONE_HOP:
            return 1.3
        if shard_type == ShardType.TWO_HOP:
            return 1.1
        return 1.0

    def _render_primary_answer(self, shard_type: ShardType, item: object) -> str:
        if isinstance(item, KGLiteral):
            entity = self._clean_text(item.entity)
            relation = self._clean_relation(item.relation)
            value = item.value.strip()
            pretty_value = self._clean_text(value)
            return f"KG-only answer: {pretty_value} (via {relation} of {entity})"
        if isinstance(item, KGTriple):
            head = self._clean_text(item.head)
            relation = self._clean_relation(item.relation)
            tail = self._clean_text(item.tail)
            return f"KG-only answer: {head} {relation} {tail}"
        if isinstance(item, KGPath2):
            head = self._clean_text(item.head)
            mid = self._clean_text(item.middle)
            tail = self._clean_text(item.tail)
            rel1 = self._clean_relation(item.relation1)
            rel2 = self._clean_relation(item.relation2)
            return (
                "KG-only answer: "
                f"{head} {rel1} {mid}; {mid} {rel2} {tail}"
            )
        if isinstance(item, KGDescription):
            entity = self._clean_text(item.entity)
            desc = self._truncate_text(item.text)
            return f"KG-only answer: {entity} — {desc}"
        return f"KG-only answer: {self._clean_text(str(item))}"

    def _render_item_text(self, shard_type: ShardType, item: object) -> str:
        if isinstance(item, KGLiteral):
            entity = self._clean_text(item.entity)
            relation = self._clean_relation(item.relation)
            value = self._clean_text(item.value)
            return f"{entity} {relation} {value}"
        if isinstance(item, KGTriple):
            head = self._clean_text(item.head)
            relation = self._clean_relation(item.relation)
            tail = self._clean_text(item.tail)
            return f"{head} {relation} {tail}"
        if isinstance(item, KGPath2):
            head = self._clean_text(item.head)
            mid = self._clean_text(item.middle)
            tail = self._clean_text(item.tail)
            rel1 = self._clean_relation(item.relation1)
            rel2 = self._clean_relation(item.relation2)
            return f"{head} {rel1} {mid}; {mid} {rel2} {tail}"
        if isinstance(item, KGDescription):
            entity = self._clean_text(item.entity)
            desc = self._truncate_text(item.text)
            return f"{entity}: {desc}"
        return self._clean_text(str(item))

    @staticmethod
    def _clean_text(value: str) -> str:
        replaced = value.replace("_", " ").strip()
        return " ".join(replaced.split())

    @staticmethod
    def _clean_relation(value: str) -> str:
        clean = value.rsplit("/", 1)[-1] if "/" in value else value
        return KGPipeline._clean_text(clean)

    @staticmethod
    def _truncate_text(value: str, limit: int = 196) -> str:
        text = value.strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _prepare_knowledge(self) -> None:
        if self._prepare_freebase_easy():
            return
        firebase_cfg = self.config.firebase
        if not firebase_cfg.enabled:
            return

        output_dir = firebase_cfg.output_dir
        shard_candidates = [
            output_dir / name
            for name in ("one_hop.jsonl", "two_hop.jsonl", "literal.jsonl", "description.jsonl")
        ]
        if all(path.exists() for path in shard_candidates):
            LOGGER.info("Using existing Firebase shard export at %s", output_dir)
            self.config.storage.kg_path = output_dir
            return

        if not firebase_cfg.credentials_path or not firebase_cfg.collection:
            LOGGER.warning(
                "Firebase ingestion enabled but credentials or collection missing; skipping download."
            )
            return

        filters = firebase_cfg.to_filters()
        download_config = FirebaseDownloadConfig(
            credentials_path=firebase_cfg.credentials_path,
            project_id=firebase_cfg.project_id,
            collection=firebase_cfg.collection,
            filters=filters,
            limit=firebase_cfg.limit,
            select_fields=firebase_cfg.select_fields,
        )
        LOGGER.info(
            "Downloading Firebase knowledge: collection=%s filters=%d limit=%s",
            firebase_cfg.collection,
            len(filters),
            firebase_cfg.limit,
        )
        downloader = FirebaseDownloader(download_config)
        documents = downloader.download()
        if not documents:
            LOGGER.warning("Firebase download returned no documents; skipping shard generation")
            return
        processor = FirebaseProcessor(output_dir)
        raw_path = processor.write_documents(documents, "firebase_raw.jsonl")
        LOGGER.info("Raw Firebase export saved to %s", raw_path)
        if firebase_cfg.process_shards:
            shard_paths = processor.process_to_shards(documents)
            LOGGER.info("Generated shard files: %s", {k: str(v) for k, v in shard_paths.items()})
            if shard_paths:
                self.config.storage.kg_path = output_dir

    def _prepare_freebase_easy(self) -> bool:
        cfg = self.config.freebase_easy
        if not cfg.enabled:
            return False

        output_dir = cfg.output_dir
        shard_candidates = [
            output_dir / name
            for name in ("one_hop.jsonl", "two_hop.jsonl", "literal.jsonl", "description.jsonl")
        ]
        if all(path.exists() for path in shard_candidates):
            LOGGER.info("Using existing Freebase Easy shard export at %s", output_dir)
            self.config.storage.kg_path = output_dir
            return True

        # Try Parquet files first
        if cfg.use_parquet and cfg.facts_parquet_path:
            LOGGER.info("Using Parquet-based Freebase Easy processing")
            builder = ParquetFreebaseEasyShardBuilder(
                facts_parquet_path=cfg.facts_parquet_path,
                output_dir=output_dir,
                scores_parquet_path=cfg.scores_parquet_path,
                languages=cfg.languages,
                include_all_languages=cfg.include_all_languages,
                description_predicates=cfg.description_predicates,
                name_predicates=cfg.name_predicates,
                alias_predicates=cfg.alias_predicates,
                literal_predicates=cfg.literal_predicates,
                include_scores=cfg.include_scores,
                score_relation=cfg.score_relation,
                max_facts=cfg.max_facts,
                chunk_size=cfg.chunk_size,
            )
            try:
                result = builder.build()
            except FileNotFoundError as exc:
                LOGGER.error("Parquet Freebase Easy ingestion failed: %s", exc)
                return False

            if result.paths:
                self.config.storage.kg_path = output_dir
                return True
            return False

        # Fallback to text files
        if not cfg.facts_path:
            LOGGER.warning("Freebase Easy enabled but no facts_path or facts_parquet_path provided; skipping")
            return False

        LOGGER.info("Using text-based Freebase Easy processing")
        builder = FreebaseEasyShardBuilder(
            facts_path=cfg.facts_path,
            output_dir=output_dir,
            scores_path=cfg.scores_path,
            languages=cfg.languages,
            include_all_languages=cfg.include_all_languages,
            description_predicates=cfg.description_predicates,
            name_predicates=cfg.name_predicates,
            alias_predicates=cfg.alias_predicates,
            literal_predicates=cfg.literal_predicates,
            include_scores=cfg.include_scores,
            score_relation=cfg.score_relation,
            max_facts=cfg.max_facts,
        )
        try:
            result = builder.build()
        except FileNotFoundError as exc:
            LOGGER.error("Freebase Easy ingestion failed: %s", exc)
            return False

        if result.paths:
            self.config.storage.kg_path = output_dir
            return True
        return False
