#!/bin/bash
# Safe DB repair wrapper for Prompt Portal (SQLite)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="${1:-$HERE/app.db}"

echo "[fix-db] Target DB: $DB_PATH"
if [ ! -f "$DB_PATH" ]; then
  echo "[fix-db] Database not found at $DB_PATH — nothing to do."; exit 0
fi

STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP="$DB_PATH.bak_$STAMP"
echo "[fix-db] Creating backup: $BACKUP"
cp -p "$DB_PATH" "$BACKUP"

echo "[fix-db] Running Python fixer…"
python3 "$HERE/fix_db.py" "$DB_PATH"
CODE=$?
if [ $CODE -eq 0 ]; then
  echo "[fix-db] Done. Backup kept at $BACKUP"
else
  echo "[fix-db] Fixer exited with code $CODE. Your DB is unchanged; see output."
  exit $CODE
fi
