"""
Quick diagnostic to check what's in the driving_game scores
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("DRIVING GAME SCORES DIAGNOSTIC")
print("=" * 70)
print()

# Check if mode column exists
cursor.execute("PRAGMA table_info(scores)")
columns = [row[1] for row in cursor.fetchall()]
print(f"Available columns: {', '.join(columns)}")
print()

# Count by mode
print("Score counts by mode:")
cursor.execute("""
    SELECT mode, COUNT(*) as count
    FROM scores
    GROUP BY mode
    ORDER BY count DESC
""")
for mode, count in cursor.fetchall():
    print(f"  {mode or 'NULL':20} : {count:5} scores")

print()

# Check what's in driving_game mode
cursor.execute("""
    SELECT COUNT(*) FROM scores WHERE mode = 'driving_game'
""")
driving_count = cursor.fetchone()[0]

print(f"Total scores with mode='driving_game': {driving_count}")
print()

if driving_count > 0:
    print("Sample driving_game entries:")
    cursor.execute("""
        SELECT id, mode, new_score, 
               driving_game_message_count, 
               driving_game_consensus_reached,
               total_steps,
               created_at
        FROM scores 
        WHERE mode = 'driving_game'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    print(f"{'ID':<6} {'Mode':<15} {'Score':<8} {'DG_Msgs':<10} {'DG_Cons':<10} {'Maze_Steps':<12} {'Created'}")
    print("-" * 90)
    for row in cursor.fetchall():
        score_id, mode, score, dg_msgs, dg_cons, steps, created = row
        print(f"{score_id:<6} {mode:<15} {score:<8.0f} {str(dg_msgs):<10} {str(dg_cons):<10} {str(steps):<12} {created[:16]}")
    
    print()
    print("PROBLEM DETECTED!")
    print("These scores have mode='driving_game' but may lack proper Driving Game metrics.")
    print()
    print("Solution: Run the fix script to correct these entries.")

else:
    print("✓ No scores with mode='driving_game' found.")
    print("  This is expected if no one has tested Driving Game prompts yet.")
    print()
    print("  The leaderboard should show 0 entries when Driving Game filter is selected.")

conn.close()
print("=" * 70)

