"""End-to-end pipeline orchestrating the KG-enhanced LLM workflow."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence

from kg_llm_new.logging_utils import get_logger

from .classification.question_classifier import QuestionClassifier, QuestionType
from .config import PipelineConfig
from .kg.firebase import FirebaseDownloadConfig, FirebaseDownloader, FirebaseProcessor
from .kg.freebase import FreebaseEasyShardBuilder
from .kg.freebase_parquet import ParquetFreebaseEasyShardBuilder
from .kg.loader import KnowledgeGraphLoader
from .llm.client import LLMClient, LLMClientConfig
from .prompt import PromptBuilder
from .retrieval.retriever import RetrievalRequest, Retriever

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
    ) -> None:
        self.config = config
        self.classifier = classifier
        self.prompt_builder = PromptBuilder(config.prompt.system_prompt)
        self._prepare_knowledge()
        self.store = KnowledgeGraphLoader(config.storage.kg_path or config.storage.base_dir).load()
        self.retriever = Retriever(
            store=self.store,
            lexical_weight=config.retriever.lexical_weight,
            semantic_weight=config.retriever.semantic_weight,
        )
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
        budgets = self._derive_budgets(classification.active_labels)
        retrieval_request = RetrievalRequest(
            question=question,
            entities=entities,
            active_labels=classification.active_labels,
            budgets=budgets,
        )
        retrieval_result = self.retriever.retrieve(retrieval_request)
        prompt_bundle = self.prompt_builder.build(
            question=question,
            shards=retrieval_result.shards,
            label_probabilities=classification.probabilities,
        )
        answer = self.llm_client.generate(
            messages=prompt_bundle.messages,
            temperature=temperature or self.config.default_temperature,
            top_p=top_p or self.config.default_top_p,
            max_tokens=max_tokens or self.config.retriever.budget.max_tokens,
        )
        latency_ms = (time.time() - start_time) * 1000
        if self.config.enable_latency_logging:
            LOGGER.info(
                "Pipeline completed in %.1f ms | labels=%s | evidence_tokens=%d",
                latency_ms,
                [label.name for label in classification.active_labels],
                prompt_bundle.evidence_tokens,
            )
        return PipelineOutput(
            answer=answer,
            latency_ms=latency_ms,
            evidence_tokens=prompt_bundle.evidence_tokens,
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
            scale = max(1, len(active_labels))
            return {label: max(1, mapping[label] // scale) for label in active_labels}
        return mapping

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
