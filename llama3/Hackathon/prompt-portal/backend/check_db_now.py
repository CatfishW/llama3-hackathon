"""Quick check of database state RIGHT NOW"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("DATABASE STATE CHECK")
print("=" * 70)

# Count by mode
cursor.execute("""
    SELECT mode, COUNT(*) as count
    FROM scores
    GROUP BY mode
    ORDER BY mode
""")

print("Scores by mode:")
total = 0
for mode, count in cursor.fetchall():
    print(f"  {mode or 'NULL':20} : {count:5}")
    total += count
print(f"  {'TOTAL':20} : {total:5}")
print()

# Check driving_game specifically
cursor.execute("SELECT COUNT(*) FROM scores WHERE mode = 'driving_game'")
dg_count = cursor.fetchone()[0]
print(f"Driving Game scores: {dg_count}")

if dg_count > 0:
    print("\nDriving Game entries (sample):")
    cursor.execute("""
        SELECT id, new_score, driving_game_message_count, created_at
        FROM scores
        WHERE mode = 'driving_game'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  ID:{row[0]}, Score:{row[1]}, Messages:{row[2]}, Time:{row[3][:16]}")

conn.close()
print("=" * 70)

