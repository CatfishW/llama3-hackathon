#!/usr/bin/env python3
"""
label_webqsp_textonly.py

Text-only labeling for questions when no parses/answers are available.
Labels:
- boolean
- literal
- description
- single_hop
- multi_hop

Also estimates hop count with text heuristics:
- HopCount: 1, 2, or 3 (3 means 3 or more)
- HopBucket: "1-hop", "2-hop", "3+-hop"

Input formats (auto-detected by extension):
- .json : WebQSP-style {"Questions":[{"QuestionId":..., "RawQuestion":..., "ProcessedQuestion":...}, ...]}
- .jsonl/.ndjson : lines of {"id": "...", "question": "..."}
- .txt : one question per line (id is line number)

Usage:
  python label_webqsp_textonly.py --input questions.json --out labels.csv
  python label_webqsp_textonly.py --input questions.txt --out labels.jsonl --format jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

BOOL_Q_PREFIXES = (
    "is", "are", "was", "were", "do", "does", "did",
    "can", "could", "has", "have", "had", "will", "would", "should",
    "may", "might", "must"
)

LITERAL_NUMERIC_PATTERNS = (
    r"\bhow many\b",
    r"\bhow much\b",
    r"\bhow long\b",
    r"\bhow far\b",
    r"\bhow tall\b",
    r"\bhow high\b",
    r"\bhow deep\b",
    r"\bwhat(?:'s| is)? the (?:population|area|size|length|height|age|gdp|distance|speed|price|cost|rank)\b",
    r"\bpopulation of\b",
    r"\barea of\b",
    r"\blength of\b",
    r"\bheight of\b",
    r"\bdistance (?:to|from|between)\b",
    r"\bkm\b|\bkilometers?\b|\bmiles?\b|\bmeters?\b",
    r"\bage\b|\byears? old\b",
)

LITERAL_TEMPORAL_PATTERNS = (
    r"\bwhen\b",
    r"\bwhat year\b",
    r"\bwhat date\b",
    r"\bin which year\b",
    r"\bwhich year\b",
)

DESCRIPTION_HINTS = (
    r"\bwhat is\b",
    r"\bwho is\b",
    r"\bwhat are\b",
    r"\bwho are\b",
    r"\btell me about\b",
    r"\bdefine\b|\bdefinition of\b|\bmeaning of\b|\bstand[s]? for\b|\bacronym\b|\babbreviation\b|\bfull form\b",
    r"\bexplain\b",
    r"\bbiography of\b|\bhistory of\b",
)

# Signals that a "what/who is" is relational (not an open-ended definition)
RELATIONAL_CUES = (
    r"\bof\b", r"\bin\b", r"\bat\b", r"\bfrom\b", r"\bfor\b", r"\bwith\b", r"\bby\b",
    r"\bcalled\b", r"\bnamed\b", r"\bname of\b", r"\bcapital of\b", r"\bpopulation of\b",
)

COMPARATIVE_SUPERLATIVE = (
    r"\bbefore\b", r"\bafter\b", r"\bearliest\b", r"\blatest\b",
    r"\bfirst\b", r"\blast\b", r"\boldest\b", r"\byoungest\b",
    r"\bmost\b", r"\bleast\b", r"\bbiggest\b", r"\bsmallest\b",
    r"\blargest\b", r"\bhighest\b", r"\blowest\b", r"\blongest\b", r"\bshortest\b",
    r"\btop\b", r"\bbest\b", r"\bworst\b"
)

RELATIONAL_TOKENS = (
    " of ", " in ", " at ", " from ", " for ", " with ", " by ", " to ", " near ", " between ", " within ",
)

RELATIVE_CLAUSE_TOKENS = (
    " that ", " which ", " whose ", " who ", " where ", " when ",
)


def norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def any_regex(patterns: Iterable[str], text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def is_boolean(qtext: str) -> bool:
    q = norm(qtext)
    if q.startswith(("what", "who", "when", "where", "why", "how", "which")):
        return False
    return any(q.startswith(p + " ") for p in BOOL_Q_PREFIXES) or q.startswith("is ") or q.startswith("are ")


def is_literal(qtext: str) -> bool:
    q = " " + norm(qtext) + " "
    if any_regex(LITERAL_NUMERIC_PATTERNS, q) or any_regex(LITERAL_TEMPORAL_PATTERNS, q):
        return True
    # Heuristic: questions starting with "how" often seek a measure (except "how many/much/long..." already covered)
    # We'll keep it conservative:
    return False


def is_description(qtext: str) -> bool:
    q = " " + norm(qtext) + " "
    if any_regex(DESCRIPTION_HINTS, q):
        # If it also has clear relational cues, treat as non-description (likely entity lookup)
        if any_regex(RELATIONAL_CUES, q):
            return False
        return True
    return False


def estimate_hops(qtext: str) -> int:
    """
    Very rough, text-only hop estimate:
      - Start at 1
      - +1 if we see comparative/superlative or a relative clause ("that/which/who...") beyond the leading 'who/what'
      - +1 if there are >=2 relational tokens (e.g., multiple 'of/in/from' chains)
      - Cap at 3 (3 means 3 or more)
    """
    q = " " + norm(qtext) + " "

    hop = 1

    # Count relational tokens
    rel_count = sum(q.count(tok) for tok in RELATIONAL_TOKENS)

    # Relative clause presence (excluding leading interrogative "who/what/where/when" at start)
    rel_clause = any(tok in q for tok in RELATIVE_CLAUSE_TOKENS)

    comp = any_regex(COMPARATIVE_SUPERLATIVE, q)

    if rel_count >= 2 or rel_clause:
        hop += 1
    if comp or rel_count >= 3:
        hop += 1

    return max(1, min(hop, 3))


def coarse_label(qtext: str) -> str:
    """
    Decide one of: boolean, literal, description, single_hop, multi_hop
    """
    if is_boolean(qtext):
        return "boolean"
    if is_literal(qtext):
        return "literal"
    if is_description(qtext):
        return "description"
    # hop-based decision
    hops = estimate_hops(qtext)
    return "single_hop" if hops == 1 else "multi_hop"


def hop_bucket(n: int) -> str:
    if n <= 1:
        return "1-hop"
    if n == 2:
        return "2-hop"
    return "3+-hop"


def load_questions(path: Path) -> List[Tuple[str, str]]:
    """
    Returns list of (qid, question_text)
    Supports:
      - WebQSP JSON: {"Questions":[{"QuestionId":..., "RawQuestion":..., "ProcessedQuestion":...}, ...]}
      - JSONL/NDJSON: each line {"id": "...", "question": "..."}
      - TXT: one question per line, id = line number (0-based)
    """
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        qs = []
        for q in data.get("Questions", []):
            qid = q.get("QuestionId") or q.get("Id") or q.get("id") or ""
            text = q.get("ProcessedQuestion") or q.get("RawQuestion") or q.get("question") or ""
            if text:
                qs.append((str(qid) if qid else str(len(qs)), text))
        return qs

    if path.suffix.lower() in (".jsonl", ".ndjson"):
        qs = []
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                obj = json.loads(line)
                qid = obj.get("id", str(i))
                text = obj.get("question") or obj.get("text") or ""
                if text:
                    qs.append((str(qid), text))
        return qs

    if path.suffix.lower() == ".txt":
        qs = []
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                text = line.strip()
                if text:
                    qs.append((str(i), text))
        return qs

    raise ValueError(f"Unsupported input format: {path.suffix}")


def save_outputs(rows: List[Dict[str, Any]], path: Path, fmt: str = "csv") -> None:
    fmt = fmt.lower()
    if fmt == "csv":
        fieldnames = ["QuestionId", "Question", "PredictedLabel", "HopCount", "HopBucket", "Debug"]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow(r)
    elif fmt in ("jsonl", "ndjson"):
        with path.open("w", encoding="utf-8") as f:
            for r in rows:
                obj = r.copy()
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def main():
    ap = argparse.ArgumentParser(description="Text-only labeling for questions (no parses/answers).")
    ap.add_argument("--input", required=True, help="Path to questions file (.json WebQSP, .jsonl, or .txt).")
    ap.add_argument("--out", required=True, help="Output path (csv or jsonl).")
    ap.add_argument("--format", default="csv", choices=["csv", "jsonl", "ndjson"], help="Output format.")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.out)

    pairs = load_questions(in_path)

    rows: List[Dict[str, Any]] = []
    for qid, qtext in pairs:
        label = coarse_label(qtext)
        hops = estimate_hops(qtext)
        rows.append({
            "QuestionId": qid,
            "Question": qtext,
            "PredictedLabel": label,
            "HopCount": hops,
            "HopBucket": hop_bucket(hops),
            "Debug": json.dumps({
                "boolean": is_boolean(qtext),
                "literal": is_literal(qtext),
                "description": is_description(qtext),
                "heuristics": "text-only"
            }, ensure_ascii=False)
        })

    save_outputs(rows, out_path, fmt=args.format)
    print(f"Labeled {len(rows)} questions -> {out_path}")


if __name__ == "__main__":
    main()
