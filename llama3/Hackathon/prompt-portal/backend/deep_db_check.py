"""
Deep check of database to see what's really there
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("DEEP DATABASE CHECK")
print("=" * 70)
print()

# Total count
cursor.execute("SELECT COUNT(*) FROM scores")
total = cursor.fetchone()[0]
print(f"TOTAL scores in database: {total}")
print()

# Count by mode (including NULL)
print("Breakdown by mode:")
cursor.execute("""
    SELECT 
        CASE WHEN mode IS NULL THEN 'NULL' ELSE mode END as mode_value,
        COUNT(*) as count
    FROM scores
    GROUP BY mode
    ORDER BY count DESC
""")

for mode, count in cursor.fetchall():
    print(f"  {mode:20} : {count:5}")

print()

# Check if any scores have NULL mode
cursor.execute("SELECT COUNT(*) FROM scores WHERE mode IS NULL")
null_count = cursor.fetchone()[0]
if null_count > 0:
    print(f"[WARNING] {null_count} scores have NULL mode!")
    print("These will NOT be filtered and might show in all views")
else:
    print("[OK] No NULL modes")

print()

# Check latest 10 scores
print("Latest 10 scores:")
cursor.execute("""
    SELECT id, mode, new_score, template_id, created_at
    FROM scores
    ORDER BY created_at DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  ID:{row[0]:4} mode:{row[1] or 'NULL':12} score:{row[2] or 0:6.0f} template:{row[3]:3} time:{row[4][:16]}")

conn.close()
print("=" * 70)

