"""
Migration script to add Driving Game scoring columns to the scores table.
Run this script to add the new columns for tracking Driving Game metrics.
"""
import sqlite3
import sys
from pathlib import Path

def add_driving_game_columns():
    """Add Driving Game columns to the scores table"""
    db_path = Path(__file__).parent / "app.db"
    
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(scores)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    columns_to_add = [
        ("driving_game_consensus_reached", "BOOLEAN"),
        ("driving_game_message_count", "INTEGER"),
        ("driving_game_duration_seconds", "REAL"),
        ("driving_game_player_option", "VARCHAR(50)"),
        ("driving_game_agent_option", "VARCHAR(50)"),
    ]
    
    added_count = 0
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE scores ADD COLUMN {column_name} {column_type}")
                print(f"[OK] Added column: {column_name}")
                added_count += 1
            except sqlite3.OperationalError as e:
                print(f"[ERROR] Error adding column {column_name}: {e}")
        else:
            print(f"[SKIP] Column {column_name} already exists")
    
    conn.commit()
    conn.close()
    
    if added_count > 0:
        print(f"\n[SUCCESS] Added {added_count} new column(s) to the scores table")
    else:
        print("\n[INFO] No new columns were added (all already exist)")
    
    print("\n[DONE] Migration complete!")

if __name__ == "__main__":
    print("Adding Driving Game columns to scores table...")
    add_driving_game_columns()

