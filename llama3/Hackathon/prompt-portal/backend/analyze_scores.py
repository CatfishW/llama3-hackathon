"""
Analyze scoring data to identify any mixing between Maze Game and Driving Game.
This is a read-only analysis script (makes no changes).
"""
import sqlite3
import sys
from pathlib import Path

def analyze_scores():
    """Analyze scoring data"""
    db_path = Path(__file__).parent / "app.db"
    
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("SCORING SYSTEMS ANALYSIS")
    print("=" * 70)
    print()
    
    # Overall statistics
    print("[1] Overall Score Distribution:")
    cursor.execute("""
        SELECT mode, COUNT(*) as count
        FROM scores
        GROUP BY mode
        ORDER BY count DESC
    """)
    stats = cursor.fetchall()
    
    total_scores = sum(count for _, count in stats)
    for mode, count in stats:
        pct = (count / total_scores * 100) if total_scores > 0 else 0
        print(f"   {mode or 'NULL':15} : {count:4} scores ({pct:5.1f}%)")
    print(f"   {'TOTAL':15} : {total_scores:4} scores")
    print()
    
    # Driving Game analysis
    print("[2] Driving Game Scores Analysis:")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM scores 
        WHERE mode = 'driving_game'
    """)
    driving_total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM scores 
        WHERE mode = 'driving_game'
          AND driving_game_consensus_reached IS NOT NULL
          AND driving_game_message_count IS NOT NULL
    """)
    driving_valid = cursor.fetchone()[0]
    
    print(f"   Total Driving Game scores: {driving_total}")
    print(f"   Valid (with proper metrics): {driving_valid}")
    print(f"   Invalid (missing metrics): {driving_total - driving_valid}")
    
    if driving_total - driving_valid > 0:
        print()
        print("   [WARNING] Found Driving Game scores without proper metrics!")
        cursor.execute("""
            SELECT id, session_id, new_score, created_at
            FROM scores 
            WHERE mode = 'driving_game'
              AND (driving_game_consensus_reached IS NULL 
                   OR driving_game_message_count IS NULL)
            ORDER BY created_at DESC
            LIMIT 10
        """)
        invalid = cursor.fetchall()
        print("   Latest invalid entries:")
        for score_id, session_id, new_score, created_at in invalid:
            print(f"      ID={score_id}, score={new_score}, "
                  f"session={session_id[:12]}..., time={created_at}")
    print()
    
    # Maze Game analysis
    print("[3] Maze Game Scores Analysis:")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM scores 
        WHERE mode IN ('lam', 'manual')
    """)
    maze_total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM scores 
        WHERE mode IN ('lam', 'manual')
          AND driving_game_message_count IS NOT NULL
    """)
    maze_contaminated = cursor.fetchone()[0]
    
    print(f"   Total Maze scores: {maze_total}")
    print(f"   Clean (no Driving metrics): {maze_total - maze_contaminated}")
    print(f"   Contaminated (with Driving metrics): {maze_contaminated}")
    
    if maze_contaminated > 0:
        print()
        print("   [WARNING] Found Maze scores with Driving Game metrics!")
    print()
    
    # Cross-contamination check
    print("[4] Cross-Contamination Check:")
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN mode = 'driving_game' AND total_steps IS NOT NULL THEN 1 ELSE 0 END) as driving_with_maze,
            SUM(CASE WHEN mode IN ('lam', 'manual') AND driving_game_message_count IS NOT NULL THEN 1 ELSE 0 END) as maze_with_driving
        FROM scores
    """)
    driving_with_maze, maze_with_driving = cursor.fetchone()
    
    print(f"   Driving Game scores with Maze metrics: {driving_with_maze}")
    print(f"   Maze scores with Driving Game metrics: {maze_with_driving}")
    
    if driving_with_maze == 0 and maze_with_driving == 0:
        print()
        print("   [OK] No cross-contamination detected!")
    else:
        print()
        print("   [WARNING] Cross-contamination detected!")
    print()
    
    # Detailed metrics breakdown
    print("[5] Metrics Breakdown by Mode:")
    for mode_val in ['driving_game', 'lam', 'manual']:
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total,
                COUNT(driving_game_message_count) as has_driving,
                COUNT(total_steps) as has_maze,
                AVG(new_score) as avg_score
            FROM scores
            WHERE mode = ?
        """, (mode_val,))
        total, has_driving, has_maze, avg_score = cursor.fetchone()
        
        if total > 0:
            print(f"   {mode_val:15} :")
            print(f"      Total: {total}")
            print(f"      With Driving metrics: {has_driving}")
            print(f"      With Maze metrics: {has_maze}")
            print(f"      Avg new_score: {avg_score:.1f if avg_score else 0}")
    
    conn.close()
    
    print()
    print("=" * 70)
    print("[DONE] Analysis complete!")
    print()
    
    # Recommendations
    if driving_total - driving_valid > 0 or maze_contaminated > 0:
        print("RECOMMENDATIONS:")
        print("- Run 'python cleanup_mixed_scores.py' to fix mixed data")
        print("- Or manually clean up invalid scores in the database")
    else:
        print("STATUS: All scores are properly separated! No action needed.")
    
    print("=" * 70)

if __name__ == "__main__":
    analyze_scores()

