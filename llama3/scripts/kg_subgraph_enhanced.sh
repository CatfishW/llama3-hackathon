#!/usr/bin/env bash
# Wrapper for enhanced_subgraph_classifier.py to run rich analyses & batch jobs.
#
# Examples:
#   bash scripts/kg_subgraph_enhanced.sh rogkg_triples.tsv.gz --entity "Berlin" --similarity 1
#   bash scripts/kg_subgraph_enhanced.sh rogkg_triples.tsv.gz --batch-top 20 --report subgraph_report.json
#   bash scripts/kg_subgraph_enhanced.sh rogkg_triples.tsv.gz --batch-top 50 --csv subgraph_stats.csv
#   bash scripts/kg_subgraph_enhanced.sh rogkg_triples.tsv.gz --predicate-analysis --max-display 15
#
# First arg: triples path.
# Remaining args forwarded.
#
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "Usage: $0 <TRIPLES_PATH> [enhanced_subgraph_classifier.py args...]" >&2
  exit 1
fi
TRIPLES="$1"; shift
python enhanced_subgraph_classifier.py --triples "$TRIPLES" "$@"
