#!/usr/bin/env bash
# Wrapper for question_retrieval.py to inspect KG question→entity/predicate retrieval.
#
# Examples:
#   bash scripts/kg_question_retrieval.sh rogkg_triples.tsv.gz "Who founded Berlin?"
#   bash scripts/kg_question_retrieval.sh rogkg_triples.tsv.gz "What country is Berlin in?" --top-n-related 25
#   bash scripts/kg_question_retrieval.sh rogkg_triples.tsv.gz "What is the population of Berlin?" --json
#
# Args:
#   1: triples path (*.tsv.gz)
#   2: quoted natural language question
# Remaining args passed through; use --alias rogkg_alias_map.json etc.
#
set -euo pipefail
if [ $# -lt 2 ]; then
  echo "Usage: $0 <TRIPLES_PATH> <QUESTION> [question_retrieval.py args...]" >&2
  exit 1
fi
TRIPLES="$1"; shift
QUESTION="$1"; shift
python question_retrieval.py --triples "$TRIPLES" --question "$QUESTION" "$@"
