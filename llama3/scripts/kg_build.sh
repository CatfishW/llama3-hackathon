#!/usr/bin/env bash
# Build a textual knowledge graph (triples + alias map) from RoG/WebQSP parquet shards.
#
# Usage examples:
#   bash scripts/kg_build.sh data/rogsplits rogkg
#   bash scripts/kg_build.sh Z:/llama3_20250528/llama3/RoGWebQSPData rogkg --jsonl
#
# Positional args:
#   1: INPUT_DIR  Directory containing parquet shards
#   2: OUTPUT_PREFIX  Output file prefix (no extension)
# Remaining args are passed through to build_knowledge_graph.py
#
# Outputs:
#   <OUTPUT_PREFIX>_triples.tsv.gz
#   <OUTPUT_PREFIX>_alias_map.json
#   (optional) <OUTPUT_PREFIX>_triples.jsonl.gz (if --jsonl passed)
#
# Environment:
#   Uses the active Python environment; ensure requirements installed:
#     pip install -r requirements.txt pandas pyarrow
#
set -euo pipefail
if [ $# -lt 2 ]; then
  echo "Usage: $0 <INPUT_DIR> <OUTPUT_PREFIX> [extra build_knowledge_graph.py args...]" >&2
  exit 1
fi
INPUT_DIR="$1"; shift
OUT_PREFIX="$1"; shift
python build_knowledge_graph.py --input_dir "$INPUT_DIR" --output_prefix "$OUT_PREFIX" "$@"
