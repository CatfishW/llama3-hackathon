#!/usr/bin/env bash
# Lightweight helper to load a knowledge graph and perform simple queries.
# Wraps kg_loader.py CLI.
#
# Examples:
#   bash scripts/kg_query.sh rogkg_triples.tsv.gz --show-triples 5
#   bash scripts/kg_query.sh rogkg_triples.tsv.gz --search Berlin
#   bash scripts/kg_query.sh rogkg_triples.tsv.gz --alias rogkg_alias_map.json --search "blood"
#
# Required first arg: path to *_triples.tsv.gz
# Remaining args are passed through.
#
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "Usage: $0 <TRIPLES_PATH> [extra kg_loader.py args...]" >&2
  exit 1
fi
TRIPLES="$1"; shift
python kg_loader.py --triples "$TRIPLES" "$@"
