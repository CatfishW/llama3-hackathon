"""Processing utilities for Parquet-based Freebase Easy dumps."""

from __future__ import annotations

import json
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple

import pyarrow.parquet as pq

from kg_llm_new.logging_utils import get_logger

LOGGER = get_logger(__name__)


@dataclass
class ParquetFreebaseEasyBuildResult:
    """Summary of shard creation from Parquet files."""

    paths: Dict[str, Path]
    counts: Dict[str, int]


class ParquetFreebaseEasyShardBuilder:
    """Convert Parquet Freebase Easy files into JSONL shards."""

    def __init__(
        self,
        facts_parquet_path: Path,
        output_dir: Path,
        *,
        scores_parquet_path: Optional[Path] = None,
        languages: Sequence[str] = ("en",),
        include_all_languages: bool = False,
        description_predicates: Sequence[str] = ("/common/topic/description",),
        name_predicates: Sequence[str] = ("/type/object/name",),
        alias_predicates: Sequence[str] = ("/common/topic/alias",),
        literal_predicates: Sequence[str] = (),
        include_scores: bool = True,
        score_relation: str = "__score__",
        max_facts: Optional[int] = None,
        chunk_size: int = 100000,
    ) -> None:
        self.facts_parquet_path = Path(facts_parquet_path)
        self.output_dir = Path(output_dir)
        self.scores_parquet_path = Path(scores_parquet_path) if scores_parquet_path else None
        self.languages = tuple(languages)
        self.include_all_languages = include_all_languages
        self.description_predicates = set(description_predicates)
        self.name_predicates = set(name_predicates)
        self.alias_predicates = set(alias_predicates)
        forced_literals = set(literal_predicates)
        forced_literals.update(self.name_predicates)
        forced_literals.update(self.alias_predicates)
        self.literal_predicates = forced_literals
        self.include_scores = include_scores
        self.score_relation = score_relation
        self.max_facts = max_facts
        self.chunk_size = chunk_size

    def build(self) -> ParquetFreebaseEasyBuildResult:
        """Build JSONL shards from Parquet files."""
        if not self.facts_parquet_path.exists():
            raise FileNotFoundError(f"facts.parquet not found at {self.facts_parquet_path}")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        shard_paths = {
            "one_hop": self.output_dir / "one_hop.jsonl",
            "two_hop": self.output_dir / "two_hop.jsonl",
            "literal": self.output_dir / "literal.jsonl",
            "description": self.output_dir / "description.jsonl",
        }
        counts: Counter[str] = Counter()

        with ExitStack() as stack:
            handles = {
                "one_hop": stack.enter_context(shard_paths["one_hop"].open("w", encoding="utf-8")),
                "literal": stack.enter_context(shard_paths["literal"].open("w", encoding="utf-8")),
                "description": stack.enter_context(shard_paths["description"].open("w", encoding="utf-8")),
            }
            shard_paths["two_hop"].touch(exist_ok=True)

            # Process Parquet file in chunks
            LOGGER.info("Processing facts from %s in chunks of %d", self.facts_parquet_path, self.chunk_size)
            parquet_file = pq.ParquetFile(self.facts_parquet_path)
            total_processed = 0

            for batch in parquet_file.iter_batches(batch_size=self.chunk_size):
                if self.max_facts is not None and total_processed >= self.max_facts:
                    break

                # Convert batch to pandas for easier processing
                df = batch.to_pandas()
                
                for idx, row in df.iterrows():
                    if self.max_facts is not None and total_processed >= self.max_facts:
                        break
                    
                    # Extract subject, predicate, object from row
                    subject = str(row.get('subject', '')).strip()
                    predicate = str(row.get('predicate', '')).strip()
                    obj = str(row.get('object', '')).strip()
                    
                    if not subject or not predicate or not obj:
                        continue
                    
                    shard_key, payload = self._convert_fact(subject, predicate, obj)
                    if not shard_key:
                        continue
                    
                    json.dump(payload, handles[shard_key], ensure_ascii=False)
                    handles[shard_key].write("\n")
                    counts[shard_key] += 1
                    total_processed += 1
                
                # Log progress
                if total_processed % 1000000 == 0:
                    LOGGER.info("Processed %d facts...", total_processed)

            LOGGER.info("Completed processing %d facts", total_processed)

            # Process scores if available
            if self.include_scores and self.scores_parquet_path and self.scores_parquet_path.exists():
                LOGGER.info("Processing scores from %s", self.scores_parquet_path)
                literal_handle = handles["literal"]
                score_count = 0
                for payload in self._iter_scores_parquet():
                    json.dump(payload, literal_handle, ensure_ascii=False)
                    literal_handle.write("\n")
                    counts["literal"] += 1
                    score_count += 1
                LOGGER.info("Added %d score records", score_count)
            elif self.include_scores and self.scores_parquet_path and not self.scores_parquet_path.exists():
                LOGGER.warning("Scores file %s missing; skipping", self.scores_parquet_path)

        LOGGER.info(
            "Freebase Easy (Parquet) shards written to %s | counts=%s",
            self.output_dir,
            dict(counts),
        )
        return ParquetFreebaseEasyBuildResult(paths=shard_paths, counts=dict(counts))

    def _convert_fact(self, subject: str, predicate: str, obj: str) -> Tuple[Optional[str], Dict[str, object]]:
        """Convert a fact triple into appropriate shard format."""
        subject = subject.strip()
        predicate = predicate.strip()
        obj = obj.strip()
        if not subject or not predicate or not obj:
            return None, {}

        # Handle description predicates
        if predicate in self.description_predicates:
            text, lang = self._parse_string_literal(obj)
            if text is None:
                return None, {}
            if not self._language_allowed(lang):
                return None, {}
            payload: Dict[str, object] = {
                "entity": subject,
                "text": text,
                "relation": predicate,
            }
            if lang:
                payload["lang"] = lang
            return "description", payload

        # Try to parse as string literal
        literal_value, lang = self._parse_string_literal(obj)
        if literal_value is not None:
            if not self._language_allowed(lang):
                return None, {}
            payload = {
                "entity": subject,
                "relation": predicate,
                "value": literal_value,
            }
            if lang:
                payload["lang"] = lang
            return "literal", payload

        # Force literal for specific predicates
        if predicate in self.literal_predicates:
            payload = {
                "entity": subject,
                "relation": predicate,
                "value": obj,
            }
            return "literal", payload

        # Entity-to-entity relationship (starts with /)
        if obj.startswith("/"):
            payload = {
                "entity": subject,
                "head": subject,
                "relation": predicate,
                "tail": obj,
            }
            return "one_hop", payload

        # Default to literal
        payload = {
            "entity": subject,
            "relation": predicate,
            "value": obj,
        }
        return "literal", payload

    def _parse_string_literal(self, raw: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse a string literal with optional language tag."""
        token = raw.strip()
        if not token.startswith('"'):
            return None, None
        value_token, tail = self._split_literal(token)
        try:
            text = json.loads(value_token)
        except json.JSONDecodeError:
            text = value_token.strip('"')
        lang = None
        tail = tail.strip()
        if tail.startswith("@"):
            lang_token, _, remainder = tail[1:].partition("^^")
            lang = lang_token.strip() or None
            tail = f"^^{remainder}" if remainder else ""
        return text, lang

    def _split_literal(self, token: str) -> Tuple[str, str]:
        """Split a quoted literal from its suffix."""
        escaped = False
        for idx in range(1, len(token)):
            char = token[idx]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                return token[: idx + 1], token[idx + 1 :]
        return token, ""

    def _language_allowed(self, lang: Optional[str]) -> bool:
        """Check if a language is allowed."""
        if self.include_all_languages:
            return True
        if not lang:
            return True
        return lang in set(self.languages)

    def _iter_scores_parquet(self) -> Iterable[Dict[str, object]]:
        """Iterate over scores from Parquet file."""
        if not self.scores_parquet_path:
            return []
        
        LOGGER.info("Loading scores from %s", self.scores_parquet_path)
        parquet_file = pq.ParquetFile(self.scores_parquet_path)
        
        for batch in parquet_file.iter_batches(batch_size=self.chunk_size):
            df = batch.to_pandas()
            
            for idx, row in df.iterrows():
                entity = str(row.get('entity', '')).strip()
                score_value = row.get('score_value', '')
                
                if not entity:
                    continue
                
                payload: Dict[str, object] = {
                    "entity": entity,
                    "relation": self.score_relation,
                }
                
                try:
                    payload["value"] = float(score_value)
                except (ValueError, TypeError):
                    payload["value"] = str(score_value)
                
                yield payload
