#!/usr/bin/env python3
"""Build a deduplicated textual knowledge graph from RoG/WebQSP parquet shards.

Steps:
 1. Scan all .parquet files under an input directory.
 2. Extract each row's `graph` column (list/array of 3-item triples: [subject, predicate, object]).
 3. First pass: harvest alias / label candidates for opaque IDs like m.xxxxx, g.xxxxx.
 4. Second pass: re-emit triples replacing IDs with textual labels when available.
 5. Deduplicate and write out:
      - <output_prefix>_triples.tsv.gz  (tab: subject, predicate, object)
      - <output_prefix>_alias_map.json  (ID -> chosen textual label)
      - <optional> <output_prefix>_triples.jsonl.gz (one JSON object per triple) if --jsonl

Heuristics for labeling IDs:
  * If subject is an ID and object is plain text and predicate contains any of:
      name, label, title, alias, description, medal, country, gender
    then object is a candidate label for subject.
  * If object is an ID and subject is plain text and predicate contains: country, affiliation, athlete, gender
    then subject is a candidate label for object.
  * Shortest non-empty candidate wins (ties: earliest encountered).

If no textual label is found for an ID, we keep the raw ID.

This is a best-effort normalization without external KB lookups.

Usage (PowerShell):
  python .\build_knowledge_graph.py --input_dir Z:\llama3_20250528\llama3\RoGWebQSPData --output_prefix rogkg --jsonl

Requires: pandas, pyarrow (installed already if you used load_parquet.py)
"""
from __future__ import annotations
import argparse
import json
import gzip
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Set
import math

try:
    import pandas as pd
except ImportError:
    print("Missing pandas. Install with: pip install pandas pyarrow")
    sys.exit(1)

ID_RE = re.compile(r"^(m|g)\.[0-9a-z]+$")
LABEL_PRED_KEYWORDS_SUBJECT = ["name","label","title","alias","description","medal","country","gender"]
LABEL_PRED_KEYWORDS_OBJECT  = ["country","affiliation","athlete","gender"]

# Faster lowercase matching set
SUBJECT_KEYS = set(LABEL_PRED_KEYWORDS_SUBJECT)
OBJECT_KEYS = set(LABEL_PRED_KEYWORDS_OBJECT)

def is_id(x: str) -> bool:
    return bool(ID_RE.match(x))

def is_plain_text(x: str) -> bool:
    return not is_id(x)

def predicate_has_any(pred: str, keywords: Set[str]) -> bool:
    lp = pred.lower()
    return any(k in lp for k in keywords)

def iter_parquet_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob('*.parquet')):
        if p.is_file():
            yield p

def harvest_aliases(pq_files: List[Path], graph_column: str = 'graph') -> Dict[str, str]:
    """First pass: build alias map for IDs using heuristics."""
    alias: Dict[str, str] = {}

    def consider(id_: str, candidate: str):
        if not candidate:
            return
        # prefer shortest label (often canonical) or first if new
        prev = alias.get(id_)
        if prev is None or len(candidate) < len(prev):
            alias[id_] = candidate

    for idx, fp in enumerate(pq_files, 1):
        try:
            df = pd.read_parquet(fp, columns=[graph_column])
        except Exception as e:
            print(f"[WARN] Skipping {fp}: {e}")
            continue
        for graphs in df[graph_column]:
            # Skip empty / NaN rows
            if graphs is None or (isinstance(graphs, float) and math.isnan(graphs)):
                continue
            for triple in graphs:
                # Some backends give numpy arrays; avoid ambiguous truth-value tests
                if triple is None:
                    continue
                try:
                    if len(triple) != 3:
                        continue
                except Exception:
                    continue
                s, p, o = map(str, triple)
                # Subject ID -> textual object label
                if is_id(s) and is_plain_text(o) and predicate_has_any(p, SUBJECT_KEYS):
                    consider(s, o.strip())
                # Object ID -> textual subject label
                if is_id(o) and is_plain_text(s) and predicate_has_any(p, OBJECT_KEYS):
                    consider(o, s.strip())
        if idx % 10 == 0:
            print(f"[alias pass] Processed {idx} parquet files, aliases so far: {len(alias)}")
    print(f"Alias harvesting complete. Total aliases: {len(alias)}")
    return alias

def build_triples(pq_files: List[Path], alias: Dict[str, str], graph_column: str = 'graph') -> Set[Tuple[str,str,str]]:
    triples: Set[Tuple[str,str,str]] = set()
    for idx, fp in enumerate(pq_files, 1):
        try:
            df = pd.read_parquet(fp, columns=[graph_column])
        except Exception as e:
            print(f"[WARN] Skipping {fp}: {e}")
            continue
        for graphs in df[graph_column]:
            if graphs is None or (isinstance(graphs, float) and math.isnan(graphs)):
                continue
            for triple in graphs:
                if triple is None:
                    continue
                try:
                    if len(triple) != 3:
                        continue
                except Exception:
                    continue
                s, p, o = map(str, triple)
                # Replace IDs with aliases if known
                if is_id(s) and s in alias:
                    s = alias[s]
                if is_id(o) and o in alias:
                    o = alias[o]
                if not s or not p or not o:
                    continue
                if s == o and '.' not in p:
                    continue
                triples.add((s, p, o))
        if idx % 10 == 0:
            print(f"[triple pass] Processed {idx} files. Unique triples: {len(triples)}")
    print(f"Triple building complete. Total unique triples: {len(triples)}")
    return triples

def write_outputs(triples: Set[Tuple[str,str,str]], alias: Dict[str,str], output_prefix: Path, write_jsonl: bool):
    tsv_path = output_prefix.with_name(output_prefix.name + '_triples.tsv.gz')
    print(f"Writing TSV triples to {tsv_path}")
    with gzip.open(tsv_path, 'wt', encoding='utf-8') as gz:
        for s,p,o in sorted(triples):
            gz.write(f"{s}\t{p}\t{o}\n")

    alias_path = output_prefix.with_name(output_prefix.name + '_alias_map.json')
    print(f"Writing alias map to {alias_path}")
    with alias_path.open('w', encoding='utf-8') as f:
        json.dump(alias, f, ensure_ascii=False, indent=2)

    if write_jsonl:
        jsonl_path = output_prefix.with_name(output_prefix.name + '_triples.jsonl.gz')
        print(f"Writing JSONL triples to {jsonl_path}")
        with gzip.open(jsonl_path, 'wt', encoding='utf-8') as gz:
            for s,p,o in sorted(triples):
                gz.write(json.dumps({'subject': s, 'predicate': p, 'object': o}, ensure_ascii=False) + '\n')

    print("Done.")

def main():
    ap = argparse.ArgumentParser(description='Build textual KG from RoG/WebQSP parquet graph column.')
    ap.add_argument('--input_dir', required=True, type=Path, help='Directory containing parquet shards')
    ap.add_argument('--graph_column', default='graph', help='Column name holding list of triples')
    ap.add_argument('--output_prefix', default='knowledge_graph', type=Path, help='Output file prefix (no extension)')
    ap.add_argument('--jsonl', action='store_true', help='Also emit JSONL triples')
    args = ap.parse_args()

    if not args.input_dir.is_dir():
        print(f"Input dir not found: {args.input_dir}")
        sys.exit(1)

    pq_files = list(iter_parquet_files(args.input_dir))
    if not pq_files:
        print('No parquet files found.')
        sys.exit(1)
    print(f"Found {len(pq_files)} parquet files.")

    alias = harvest_aliases(pq_files, graph_column=args.graph_column)
    triples = build_triples(pq_files, alias, graph_column=args.graph_column)
    write_outputs(triples, alias, args.output_prefix, write_jsonl=args.jsonl)

if __name__ == '__main__':
    main()
#python build_knowledge_graph.py --input_dir Z:\llama3_20250528\llama3\RoGWebQSPData --output_prefix rogkg --jsonl