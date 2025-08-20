#!/usr/bin/env bash
# Convenience wrapper for subgraph classification around a target entity.
#
# Examples:
#   bash scripts/kg_subgraph_classify.sh rogkg_triples.tsv.gz "Adventures by Disney"
#   bash scripts/kg_subgraph_classify.sh rogkg_triples.tsv.gz "Berlin" --max-display 5 --export berlin_subgraphs.json
#   bash scripts/kg_subgraph_classify.sh rogkg_triples.tsv.gz "Berlin" --alias rogkg_alias_map.json --search Ber
#
# Args:
#   1: triples path (*.tsv.gz)
#   2: entity name (can be '-') if you only want to --search
# Remaining args passed through to subgraph_classifier.py
#
set -euo pipefail
if [ $# -lt 2 ]; then
  echo "Usage: $0 <TRIPLES_PATH> <ENTITY|-> [extra subgraph_classifier.py args...]" >&2
  exit 1
fi
TRIPLES="$1"; shift
ENTITY="$1"; shift
EXTRA=("$@")
if [ "$ENTITY" = "-" ]; then
  python subgraph_classifier.py --triples "$TRIPLES" "${EXTRA[@]}"
else
  python subgraph_classifier.py --triples "$TRIPLES" --entity "$ENTITY" "${EXTRA[@]}"
fi
