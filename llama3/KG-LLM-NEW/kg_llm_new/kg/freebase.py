"""Processing utilities for the Freebase Easy dump."""

from __future__ import annotations

import json
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple

from kg_llm_new.logging_utils import get_logger

LOGGER = get_logger(__name__)


@dataclass
class FreebaseEasyBuildResult:
    """Summary of shard creation."""

    paths: Dict[str, Path]
    counts: Dict[str, int]


class FreebaseEasyShardBuilder:
    """Convert the Freebase Easy TSV files into JSONL shards."""

    def __init__(
        self,
        facts_path: Path,
        output_dir: Path,
        *,
        scores_path: Optional[Path] = None,
        languages: Sequence[str] = ("en",),
        include_all_languages: bool = False,
        description_predicates: Sequence[str] = ("/common/topic/description",),
        name_predicates: Sequence[str] = ("/type/object/name",),
        alias_predicates: Sequence[str] = ("/common/topic/alias",),
        literal_predicates: Sequence[str] = (),
        include_scores: bool = True,
        score_relation: str = "__score__",
        max_facts: Optional[int] = None,
    ) -> None:
        self.facts_path = Path(facts_path)
        self.output_dir = Path(output_dir)
        self.scores_path = Path(scores_path) if scores_path else None
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

    def build(self) -> FreebaseEasyBuildResult:
        if not self.facts_path.exists():
            raise FileNotFoundError(f"facts.txt not found at {self.facts_path}")

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

            with self.facts_path.open("r", encoding="utf-8") as facts_file:
                for idx, raw_line in enumerate(facts_file):
                    if self.max_facts is not None and idx >= self.max_facts:
                        break
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) < 3:
                        continue
                    subject, predicate, obj = parts[0], parts[1], parts[2]
                    shard_key, payload = self._convert_fact(subject, predicate, obj)
                    if not shard_key:
                        continue
                    json.dump(payload, handles[shard_key], ensure_ascii=False)
                    handles[shard_key].write("\n")
                    counts[shard_key] += 1

            if self.include_scores and self.scores_path and self.scores_path.exists():
                literal_handle = handles["literal"]
                for payload in self._iter_scores():
                    json.dump(payload, literal_handle, ensure_ascii=False)
                    literal_handle.write("\n")
                    counts["literal"] += 1
            elif self.include_scores and self.scores_path and not self.scores_path.exists():
                LOGGER.warning("Scores file %s missing; skipping", self.scores_path)

        LOGGER.info(
            "Freebase Easy shards written to %s | counts=%s",
            self.output_dir,
            dict(counts),
        )
        return FreebaseEasyBuildResult(paths=shard_paths, counts=dict(counts))

    def _convert_fact(self, subject: str, predicate: str, obj: str) -> Tuple[Optional[str], Dict[str, object]]:
        subject = subject.strip()
        predicate = predicate.strip()
        obj = obj.strip()
        if not subject or not predicate or not obj:
            return None, {}

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

        if predicate in self.literal_predicates:
            payload = {
                "entity": subject,
                "relation": predicate,
                "value": obj,
            }
            return "literal", payload

        if obj.startswith("/"):
            payload = {
                "entity": subject,
                "head": subject,
                "relation": predicate,
                "tail": obj,
            }
            return "one_hop", payload

        payload = {
            "entity": subject,
            "relation": predicate,
            "value": obj,
        }
        return "literal", payload

    def _parse_string_literal(self, raw: str) -> Tuple[Optional[str], Optional[str]]:
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
        # Datatype is ignored for now but could be surfaced if needed
        return text, lang

    def _split_literal(self, token: str) -> Tuple[str, str]:
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
        if self.include_all_languages:
            return True
        if not lang:
            return True
        return lang in set(self.languages)

    def _iter_scores(self) -> Iterable[Dict[str, object]]:
        if not self.scores_path:
            return []
        with self.scores_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                entity, score_value = parts[0], parts[1]
                payload: Dict[str, object] = {
                    "entity": entity,
                    "relation": self.score_relation,
                }
                try:
                    payload["value"] = float(score_value)
                except ValueError:
                    payload["value"] = score_value
                yield payload