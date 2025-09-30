#!/usr/bin/env python3
"""
fix_db.py — Safe DB repair for Prompt Portal

Purpose:
  - Ensure the SQLite database has scores.mode column and its index.
  - Avoids Alembic complexity on servers with drifted migrations.

Behavior:
  - Backs up DB (only in the bash wrapper) before running, then:
    * If table 'scores' exists and column 'mode' is missing, add it with NOT NULL DEFAULT 'manual'.
    * Create index ix_scores_mode if it doesn't exist.
    * Fill any NULLs with 'manual' (paranoia if existing schema allowed NULLs).

Usage:
  python fix_db.py [path_to_db]
  Default DB path is ./app.db relative to this script's directory.
"""
import os
import sqlite3
import sys

def info(msg: str):
    print(f"[fix-db] {msg}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(script_dir, 'app.db')

    if not os.path.exists(db_path):
        info(f"Database not found at: {db_path} — nothing to fix.")
        return 0

    info(f"Opening database: {db_path}")
    con = sqlite3.connect(db_path)
    con.isolation_level = None  # autocommit mode for DDL
    try:
        cur = con.cursor()
        # Check scores table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scores'")
        row = cur.fetchone()
        if not row:
            info("Table 'scores' does not exist; nothing to fix.")
            return 0

        # Check for mode column
        cur.execute("PRAGMA table_info('scores')")
        cols = [r[1] for r in cur.fetchall()]
        if 'mode' not in cols:
            info("Adding scores.mode column (VARCHAR(10) NOT NULL DEFAULT 'manual')…")
            cur.execute("ALTER TABLE scores ADD COLUMN mode VARCHAR(10) NOT NULL DEFAULT 'manual'")
        else:
            info("scores.mode already exists.")

        # Set NULLs (defensive) and ensure default
        info("Normalizing NULL modes to 'manual' (if any)…")
        cur.execute("UPDATE scores SET mode='manual' WHERE mode IS NULL")

        # Create index if missing
        info("Ensuring index ix_scores_mode exists…")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_scores_mode ON scores (mode)")

        info("DB fix completed.")
        return 0
    finally:
        con.close()

if __name__ == '__main__':
    sys.exit(main())
