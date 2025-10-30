"""
Fix script to ensure leaderboard filtering works correctly for Driving Game mode.
This script will:
1. Verify all scores have proper mode values
2. Fix any scores that might be incorrectly marked
3. Provide status report
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("LEADERBOARD FILTER FIX")
print("=" * 70)
print()

# Step 1: Check current state
print("[1] Current database state:")
cursor.execute("""
    SELECT mode, COUNT(*) as count
    FROM scores
    GROUP BY mode
    ORDER BY mode
""")
mode_counts = cursor.fetchall()
for mode, count in mode_counts:
    print(f"   {mode or 'NULL':20} : {count:5} scores")

total_scores = sum(count for _, count in mode_counts)
print(f"   {'TOTAL':20} : {total_scores:5} scores")
print()

# Step 2: Check for NULL modes
cursor.execute("SELECT COUNT(*) FROM scores WHERE mode IS NULL")
null_count = cursor.fetchone()[0]

if null_count > 0:
    print(f"[2] Found {null_count} scores with NULL mode")
    print("    Fixing: Setting NULL modes to 'manual'...")
    cursor.execute("UPDATE scores SET mode = 'manual' WHERE mode IS NULL")
    print(f"    [OK] Fixed {null_count} scores")
else:
    print("[2] No NULL modes found [OK]")
print()

# Step 3: Verify Driving Game scores have proper metrics
cursor.execute("""
    SELECT COUNT(*) 
    FROM scores 
    WHERE mode = 'driving_game'
      AND (driving_game_consensus_reached IS NULL 
           OR driving_game_message_count IS NULL)
""")
invalid_driving = cursor.fetchone()[0]

if invalid_driving > 0:
    print(f"[3] Found {invalid_driving} invalid Driving Game scores")
    print("    These scores have mode='driving_game' but lack proper metrics.")
    print("    Fixing: Converting them to 'manual' mode...")
    cursor.execute("""
        UPDATE scores 
        SET mode = 'manual' 
        WHERE mode = 'driving_game'
          AND (driving_game_consensus_reached IS NULL 
               OR driving_game_message_count IS NULL)
    """)
    print(f"    [OK] Converted {invalid_driving} scores to 'manual' mode")
else:
    print("[3] All Driving Game scores have proper metrics [OK]")
print()

# Step 4: Final verification
print("[4] Final verification:")
cursor.execute("""
    SELECT mode, COUNT(*) as count
    FROM scores
    GROUP BY mode
    ORDER BY mode
""")
print("   Mode distribution after fix:")
for mode, count in cursor.fetchall():
    print(f"   {mode or 'NULL':20} : {count:5} scores")

cursor.execute("SELECT COUNT(*) FROM scores WHERE mode = 'driving_game'")
driving_count = cursor.fetchone()[0]
print()
print(f"   Total Driving Game scores: {driving_count}")

if driving_count == 0:
    print("   [OK] Correct! No Driving Game scores exist yet.")
    print("        Leaderboard should show 0 entries when Driving Game filter is selected.")
else:
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN driving_game_consensus_reached = 1 THEN 1 ELSE 0 END) as valid
        FROM scores 
        WHERE mode = 'driving_game'
    """)
    total_dg, valid_dg = cursor.fetchone()
    print(f"   Valid: {valid_dg}/{total_dg} have proper metrics")

# Commit changes
conn.commit()
conn.close()

print()
print("=" * 70)
print("[DONE] Database fix complete!")
print()
print("NEXT STEPS:")
print("1. Restart the backend server:")
print("   cd backend")
print("   python run_server.py")
print()
print("2. Hard refresh the frontend (Ctrl+Shift+R or Ctrl+F5)")
print()
print("3. Check Driving Game leaderboard - it should show 0 entries")
print("=" * 70)

