"""Check what columns actually exist in the scores table"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("CHECKING SCORES TABLE SCHEMA")
print("=" * 70)
print()

cursor.execute("PRAGMA table_info(scores)")
existing_columns = cursor.fetchall()

print("Existing columns:")
for col in existing_columns:
    print(f"  {col[1]:40} {col[2]:15} {'NOT NULL' if col[3] else 'NULL'}")

print()
print("=" * 70)
print("Expected columns that should exist:")
expected = [
    'id', 'user_id', 'template_id', 'session_id',
    'score', 'new_score', 'survival_time', 'oxygen_collected', 'germs',
    'mode', 'total_steps', 'optimal_steps', 'backtrack_count',
    'collision_count', 'dead_end_entries', 'avg_latency_ms',
    'driving_game_consensus_reached', 'driving_game_message_count',
    'driving_game_duration_seconds', 'driving_game_player_option',
    'driving_game_agent_option', 'created_at'
]

existing_names = [col[1] for col in existing_columns]
missing = [col for col in expected if col not in existing_names]

if missing:
    print("\nMISSING COLUMNS:")
    for col in missing:
        print(f"  ✗ {col}")
else:
    print("\n✓ All expected columns exist!")

conn.close()
print("=" * 70)

