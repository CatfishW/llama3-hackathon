"""Prompt assembly utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Optional, Sequence

from kg_llm_new.logging_utils import get_logger

from .classification.question_classifier import QuestionType
from .kg.structures import KGSubgraphShard

LOGGER = get_logger(__name__)


@dataclass
class PromptBundle:
    """Structured prompt segments for LLM input."""

    system_prompt: str
    messages: List[Mapping[str, str]]
    evidence_tokens: int


class PromptBuilder:
    """Build prompts with evidence tables."""

    def __init__(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt

    def build(
        self,
        question: str,
        shards: Sequence[KGSubgraphShard],
        label_probabilities: Mapping[QuestionType, float],
    ) -> PromptBundle:
        evidence_sections: List[str] = []
        for shard in shards:
            header = shard.shard_type.value.replace("_", " ").title()
            lines = shard.textualize()
            if not lines:
                continue
            evidence_sections.append(header)
            evidence_sections.extend(f"- {line}" for line in lines[:12])
        evidence_text = "\n".join(evidence_sections)
        probability_text = " ".join(
            f"{qt.name.lower()}={label_probabilities.get(qt, 0.0):.2f}" for qt in QuestionType
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    "Answer the question using only the provided knowledge.\n"
                    "Question: "
                    f"{question}\n"
                    "Evidence granularity scores: "
                    f"{probability_text}\n"
                    "Knowledge:\n"
                    f"{evidence_text}"
                ),
            },
        ]
        return PromptBundle(
            system_prompt=self.system_prompt,
            messages=messages,
            evidence_tokens=len(evidence_text.split()),
        )

    def build_simple(
        self,
        question: str,
        label_probabilities: Optional[Mapping[QuestionType, float]] = None,
    ) -> PromptBundle:
        """Construct a direct prompt when no KG context is available."""

        probability_text = None
        if label_probabilities:
            probability_text = " ".join(
                f"{qt.name.lower()}={label_probabilities.get(qt, 0.0):.2f}" for qt in QuestionType
            )

        user_lines = [
            "Answer the question accurately. If you do not know, state that explicitly.",
            f"Question: {question}",
        ]
        if probability_text:
            user_lines.append(f"Reasoning cues: {probability_text}")

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": "\n".join(user_lines)},
        ]

        return PromptBundle(
            system_prompt=self.system_prompt,
            messages=messages,
            evidence_tokens=0,
        )
