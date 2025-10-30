"""
Cleanup script to fix mixed scoring data between Maze Game and Driving Game.
This script identifies and fixes scores that were incorrectly submitted with
the wrong mode or mixed metrics.
"""
import sqlite3
import sys
from pathlib import Path

def cleanup_mixed_scores():
    """Clean up mixed scoring data"""
    db_path = Path(__file__).parent / "app.db"
    
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("SCORING SYSTEMS CLEANUP")
    print("=" * 70)
    print()
    
    # 1. Find Driving Game scores without proper metrics
    print("[1] Checking for invalid Driving Game scores...")
    cursor.execute("""
        SELECT id, session_id, mode, 
               driving_game_consensus_reached, 
               driving_game_message_count,
               total_steps
        FROM scores 
        WHERE mode = 'driving_game'
    """)
    driving_scores = cursor.fetchall()
    
    invalid_driving = []
    for row in driving_scores:
        score_id, session_id, mode, consensus, msg_count, total_steps = row
        if consensus is None or msg_count is None:
            invalid_driving.append((score_id, session_id))
            print(f"   [!] Invalid Driving Game score: ID={score_id}, session={session_id[:12]}...")
    
    if invalid_driving:
        print(f"\n   Found {len(invalid_driving)} invalid Driving Game scores")
        print("   These scores claim to be 'driving_game' but lack required metrics.")
        print()
        print("   Options:")
        print("   1. Delete them (recommended)")
        print("   2. Convert to 'manual' mode")
        print("   3. Skip (do nothing)")
        choice = input("\n   Your choice (1/2/3): ").strip()
        
        if choice == "1":
            for score_id, _ in invalid_driving:
                cursor.execute("DELETE FROM scores WHERE id = ?", (score_id,))
            print(f"   [OK] Deleted {len(invalid_driving)} invalid scores")
        elif choice == "2":
            for score_id, _ in invalid_driving:
                cursor.execute("UPDATE scores SET mode = 'manual' WHERE id = ?", (score_id,))
            print(f"   [OK] Converted {len(invalid_driving)} scores to 'manual' mode")
        else:
            print("   [SKIP] No changes made")
    else:
        print("   [OK] All Driving Game scores have proper metrics")
    
    print()
    
    # 2. Find Maze scores with Driving Game metrics
    print("[2] Checking for Maze scores with Driving Game metrics...")
    cursor.execute("""
        SELECT id, session_id, mode,
               driving_game_message_count,
               total_steps
        FROM scores 
        WHERE mode IN ('lam', 'manual')
          AND driving_game_message_count IS NOT NULL
    """)
    maze_with_driving = cursor.fetchall()
    
    if maze_with_driving:
        print(f"   [!] Found {len(maze_with_driving)} Maze scores with Driving Game metrics")
        for score_id, session_id, mode, msg_count, steps in maze_with_driving:
            print(f"      ID={score_id}, mode={mode}, session={session_id[:12]}...")
        
        print("\n   Clearing Driving Game metrics from Maze scores...")
        cursor.execute("""
            UPDATE scores 
            SET driving_game_consensus_reached = NULL,
                driving_game_message_count = NULL,
                driving_game_duration_seconds = NULL,
                driving_game_player_option = NULL,
                driving_game_agent_option = NULL
            WHERE mode IN ('lam', 'manual')
              AND driving_game_message_count IS NOT NULL
        """)
        print(f"   [OK] Cleared Driving Game metrics from {len(maze_with_driving)} Maze scores")
    else:
        print("   [OK] No Maze scores have Driving Game metrics")
    
    print()
    
    # 3. Statistics
    print("[3] Score statistics by mode:")
    cursor.execute("""
        SELECT mode, COUNT(*) as count
        FROM scores
        GROUP BY mode
        ORDER BY count DESC
    """)
    stats = cursor.fetchall()
    
    for mode, count in stats:
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN driving_game_message_count IS NOT NULL THEN 1 END) as with_driving,
                COUNT(CASE WHEN total_steps IS NOT NULL THEN 1 END) as with_maze
            FROM scores
            WHERE mode = ?
        """, (mode,))
        with_driving, with_maze = cursor.fetchone()
        
        print(f"   {mode:15} : {count:4} scores  "
              f"({with_driving} with Driving metrics, {with_maze} with Maze metrics)")
    
    print()
    
    # 4. Commit changes
    conn.commit()
    conn.close()
    
    print("=" * 70)
    print("[DONE] Cleanup complete!")
    print()
    print("Summary:")
    print("- Driving Game scores now have ONLY Driving Game metrics")
    print("- Maze scores (LAM/Manual) have ONLY Maze metrics")
    print("- Invalid/mixed scores have been removed or corrected")
    print("=" * 70)

if __name__ == "__main__":
    print("\nThis script will clean up mixed scoring data.")
    print("Make sure you have a backup of app.db before proceeding!\n")
    
    confirm = input("Continue? (yes/no): ").strip().lower()
    if confirm == "yes":
        cleanup_mixed_scores()
    else:
        print("Aborted.")

