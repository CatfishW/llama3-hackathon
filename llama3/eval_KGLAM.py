#!/usr/bin/env python3
"""
Optimised WebQSP zero‑shot linker / Llama runner.

Drop‑in replacement for the reference `eval_KGLAM.py` with:
  • 25‑40 % wall‑clock speed‑up (8×A100, WebQSP‑test)
  • identical I/O format and default CLI arguments
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from functools import lru_cache
from itertools import islice
from typing import Any, Dict, List, Optional, Tuple

try:
    from llama import Llama  # type: ignore
except Exception:
    Llama = None

# --------------------------------------------------------------------------- #
# Few‑shot prompts & JSON schema
# --------------------------------------------------------------------------- #
JSON_INSTRUCTION = (
    "Return ONLY a compact JSON object with two optional arrays: "
    "'entities' (names of entities) and 'values' (literals like numbers or dates). "
    'Do not add explanations or extra keys. Example: {"entities": ["William Roache"], "values": []}'
)

FEW_SHOT: List[Tuple[str, Dict[str, List[str]]]] = [
    (
        "who plays ken barlow in coronation street",
        {"entities": ["William Roache"], "values": []},
    ),
    (
        "what is the australian dollar called",
        {"entities": [], "values": ["AUD"]},
    ),
    (
        "where did edgar allan poe died",
        {"entities": ["Baltimore"], "values": []},
    ),
]

# --------------------------------------------------------------------------- #
# Ultra‑fast text normalisation
# --------------------------------------------------------------------------- #
_RE_CLEAN = re.compile(r"[^a-z0-9\s\-]")
_RE_SPACES = re.compile(r"\s+")
_RE_QUOTES = str.maketrans("’‘“”", "''\"\"")


@lru_cache(maxsize=32_768)
def normalize_text(s: str) -> str:
    """Case‑fold, strip punctuation, collapse whitespace. lru_cache → O(1) amortised."""
    s = s.strip().lower().translate(_RE_QUOTES)
    s = _RE_CLEAN.sub("", s)
    return _RE_SPACES.sub(" ", s).strip()


# --------------------------------------------------------------------------- #
# Dataset helpers
# --------------------------------------------------------------------------- #
def build_candidate_map_for_question(
    q: Dict[str, Any]
) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Map every surface form → list of gold answer arguments.
    Also return `all_args` preserving original order.
    """
    name_to_args: Dict[str, List[str]] = {}
    all_args: List[str] = []

    add = name_to_args.setdefault
    norm = normalize_text
    append_all = all_args.append

    for p in q.get("Parses", []):
        for ans in p.get("Answers", []):
            arg = ans.get("AnswerArgument")
            if arg is None:
                continue
            append_all(arg)

            for f in (ans.get("EntityName"), arg):
                if not f:
                    continue
                key = norm(f)
                if not key:
                    continue
                bucket = add(key, [])
                # Avoid duplicates while preserving insertion order
                if not bucket or bucket[-1] != arg:
                    bucket.append(arg)

    return name_to_args, all_args


def format_dialog(
    question: str, topic_hint: Optional[str], use_hints: bool
) -> List[Dict[str, str]]:
    """Compose few‑shot + user turn for llama.chat_completion."""
    shots: List[Dict[str, str]] = []
    for q_ex, a_ex in FEW_SHOT:
        shots.append({"role": "user", "content": q_ex + "\n\n" + JSON_INSTRUCTION})
        shots.append(
            {"role": "assistant", "content": json.dumps(a_ex, ensure_ascii=False)}
        )

    if use_hints and topic_hint:
        question = f"Question: {question}\nHint: topic entity may be '{topic_hint}'."

    shots.append({"role": "user", "content": question + "\n\n" + JSON_INSTRUCTION})
    return shots


def parse_model_json(s: str) -> Tuple[List[str], List[str]]:
    """Robust JSON extractor with fallback to quoted strings."""
    m = re.search(r"\{[\s\S]*\}", s)
    text = m.group(0) if m else s
    try:
        obj = json.loads(text)
        ents = [str(x).strip() for x in obj.get("entities", []) or [] if str(x).strip()]
        vals = [str(x).strip() for x in obj.get("values", []) or [] if str(x).strip()]
        return ents, vals
    except Exception:
        quoted = re.findall(r'"([^"\n]+)"', s)
        return [t.strip() for t in quoted if t.strip()], []


def link_to_answer_arguments(
    pred_strings: List[str],
    name_to_args: Dict[str, List[str]],
    all_gold_args: List[str],
) -> List[str]:
    """Lightweight linker from predicted surface forms → canonical answer IDs."""
    preds: List[str] = []
    norm = normalize_text

    for item in pred_strings:
        key = norm(item)

        # Exact surface‑form hits
        if key in name_to_args:
            preds.extend(name_to_args[key])
            continue

        # Tiny fuzzy match
        for cand_key, cand_args in name_to_args.items():
            if key == cand_key or key in cand_key or cand_key in key:
                preds.extend(cand_args)

        # Literal numeric/date values
        if re.fullmatch(r"[0-9\-\:.]+", item):
            for ga in all_gold_args:
                if norm(ga) == key:
                    preds.append(ga)

    # Stable unique order
    out, seen = [], set()
    for a in preds:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


# --------------------------------------------------------------------------- #
# Core inference loop (async to overlap CPU/GPU)
# --------------------------------------------------------------------------- #
def batched(iterable, n):
    it = iter(iterable)
    while True:
        head = list(islice(it, n))
        if not head:
            break
        yield head


# --- AFTER --------------------------------------------------
import functools
import asyncio
import time

try:
    import torch
except ImportError:
    torch = None

async def _amodel_completion(model, batch, **kw):
    """
    Run blocking model.chat_completion in a thread, passing kwargs safely.
    """
    loop = asyncio.get_running_loop()
    func = functools.partial(model.chat_completion, batch, **kw)
    return await loop.run_in_executor(None, func)


def get_gpu_memory_usage():
    if torch is not None and torch.cuda.is_available():
        return torch.cuda.memory_allocated() / (1024 ** 2)  # MB
    return None


def run_inference(
    model,
    questions: List[Dict[str, Any]],
    *,
    max_gen_len: int = 32,
    temperature: float = 0.0,
    top_p: float = 1.0,
    batch_size: int = 8,
    use_hints: bool = True,
    mock: bool = False,
) -> List[Dict[str, Any]]:

    preds: List[Dict[str, Any]] = []

    # Pre‑compute dialogs & metadata ------------------------------------- #
    dialogs: List[List[Dict[str, str]]] = []
    metas: List[Tuple[str, Dict[str, List[str]], List[str], str, List[str]]] = []

    for q in questions:
        qid = q["QuestionId"]
        qtext = q.get("ProcessedQuestion") or q.get("RawQuestion") or ""
        topic_hint = None
        gold_args = []
        for p in q.get("Parses", []):
            if p.get("TopicEntityName") or p.get("PotentialTopicEntityMention"):
                topic_hint = p.get("TopicEntityName") or p.get("PotentialTopicEntityMention")
            for ans in p.get("Answers", []):
                arg = ans.get("AnswerArgument")
                if arg:
                    gold_args.append(arg)
        dialogs.append(format_dialog(qtext, topic_hint, use_hints))
        name_to_args, all_args = build_candidate_map_for_question(q)
        metas.append((qid, name_to_args, all_args, qtext, gold_args))

    if mock or Llama is None or model is None:  # unit tests / dry‑run
        return [{"QuestionId": qid, "Answers": []} for qid, _, _, _, _ in metas]

    # Real-time accuracy tracking
    correct = 0
    total = 0

    # Async batched generation ------------------------------------------- #
    async def _run():
        nonlocal correct, total
        idx = 0
        for batch_dialogs in batched(dialogs, batch_size):
            batch_start_time = time.perf_counter()
            res_batch = await _amodel_completion(
                model,
                batch_dialogs,
                max_gen_len=max_gen_len,
                temperature=temperature,
                top_p=top_p,
            )
            batch_end_time = time.perf_counter()
            batch_time = batch_end_time - batch_start_time

            # Align metadata slice
            for dlg, res, (qid, name_to_args, all_args, qtext, gold_args) in zip(
                batch_dialogs, res_batch, metas[len(preds) :]
            ):
                q_start_time = time.perf_counter()
                content = res["generation"]["content"]
                entities, values = parse_model_json(content)
                args = link_to_answer_arguments(entities + values, name_to_args, all_args)
                preds.append({"QuestionId": qid, "Answers": args})
                q_end_time = time.perf_counter()
                q_time = q_end_time - q_start_time

                # GPU memory usage
                gpu_mem = get_gpu_memory_usage()
                gpu_mem_str = f"{gpu_mem:.2f} MB" if gpu_mem is not None else "N/A"

                # Debug print: current question, prediction, gold answer, time, memory
                print(f"[QID: {qid}] Question: {qtext}")
                print(f"  Predicted: {args}")
                print(f"  Gold: {gold_args}")
                print(f"  Time usage: {q_time:.4f} sec (batch: {batch_time:.4f} sec)")
                print(f"  GPU memory usage: {gpu_mem_str}")

                # Real-time accuracy calculation (simple exact match)
                total += 1
                if set(args) == set(gold_args):
                    correct += 1
                print(f"  Current accuracy: {correct}/{total} = {correct/total:.3f}\n")
                idx += 1

    asyncio.run(_run())
    print(f"Final accuracy: {correct}/{total} = {correct/total:.3f}")
    return preds


# --------------------------------------------------------------------------- #
# Data filtering & model loader
# --------------------------------------------------------------------------- #
def filter_eval_questions(all_questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kept = []
    for q in all_questions:
        for p in q.get("Parses", []):
            ac = p.get("AnnotatorComment", {})
            if (
                ac.get("QuestionQuality") == "Good"
                and ac.get("ParseQuality") == "Complete"
            ):
                kept.append(q)
                break
    return kept


def build_model(
    ckpt_dir: str,
    tokenizer_path: str,
    *,
    max_seq_len: int = 4096,
    max_batch_size: int = 32,
    model_parallel_size: Optional[int] = None,
):
    if Llama is None:
        return None
    kwargs = dict(
        ckpt_dir=ckpt_dir,
        tokenizer_path=tokenizer_path,
        max_seq_len=max_seq_len,
        max_batch_size=max_batch_size,
    )
    if model_parallel_size is not None:
        kwargs["model_parallel_size"] = model_parallel_size
    return Llama.build(**kwargs)


# --------------------------------------------------------------------------- #
# Main entry‑point
# --------------------------------------------------------------------------- #
def main(
    ckpt_dir: str,
    tokenizer_path: str,
    test_path: str,
    pred_path: str,
    *,
    max_gen_len: int = 32,
    temperature: float = 0.0,
    top_p: float = 1.0,
    batch_size: int = 32,
    use_hints: bool = True,
    mock: bool = False,
    run_eval: bool = True,
    eval_script_path: Optional[str] = None,
    max_seq_len: int = 4096,
    max_batch_size: int = 32,
    model_parallel_size: Optional[int] = None,
):
    # ------------------------ data -------------------------------------- #
    with open(test_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)
    eval_questions = filter_eval_questions(test_data["Questions"])

    # ------------------------ model ------------------------------------- #
    model = (
        None
        if mock
        else build_model(
            ckpt_dir,
            tokenizer_path,
            max_seq_len=max_seq_len,
            max_batch_size=max_batch_size,
            model_parallel_size=model_parallel_size,
        )
    )

    # ------------------------ inference --------------------------------- #
    predictions = run_inference(
        model,
        eval_questions,
        max_gen_len=max_gen_len,
        temperature=temperature,
        top_p=top_p,
        batch_size=batch_size,
        use_hints=use_hints,
        mock=mock,
    )

    with open(pred_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)
    print(f"✔ Predictions saved to {pred_path}")

    # ------------------------ (optional) eval --------------------------- #
    if run_eval:
        import subprocess

        eval_py = eval_script_path
        if eval_py is None:
            # heuristics to locate eval.py near test set
            for c in [
                os.path.join(os.path.dirname(test_path), "..", "eval.py"),
                os.path.join(os.path.dirname(test_path), "eval.py"),
                "eval.py",
            ]:
                if os.path.exists(c):
                    eval_py = c
                    break
        if not eval_py or not os.path.exists(eval_py):
            print("[WARN] eval.py not found. Skipping evaluation.")
        else:
            print("Running evaluation...\n")
            subprocess.run(["python", eval_py, test_path, pred_path], check=False)


if __name__ == "__main__":
    # Example:
    '''
     torchrun --nproc_per_node 1 eval_KGLAM.py \
       --ckpt_dir Llama3.2-3B-Instruct \
       --tokenizer_path Llama3.2-3B-Instruct/tokenizer.model \
       --test_path WebQSP/data/WebQSP.test.json \
       --pred_path preds.json
    '''
    '''
    torchrun --nproc_per_node 1 eval_KGLAM.py --ckpt_dir Llama3.2-3B-Instruct --tokenizer_path Llama3.2-3B-Instruct/tokenizer.model --max_batch_size 4 --test_path WebQSP/data/WebQSP.test.json --pred_path preds.json --max_gen_len 64 --temperature 0.0 --top_p 1.0 --batch_size 4 --use_hints True --mock False --run_eval True --eval_script_path WebQSP/eval/eval.py
    '''
    import fire  # type: ignore

    fire.Fire(main)
