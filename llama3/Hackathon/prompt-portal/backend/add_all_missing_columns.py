"""
Add ALL missing columns to the scores table
"""
import sqlite3
import sys
from pathlib import Path

def add_missing_columns():
    db_path = Path(__file__).parent / "app.db"
    
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(scores)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    print("=" * 70)
    print("ADDING MISSING COLUMNS TO SCORES TABLE")
    print("=" * 70)
    print()
    
    # Define ALL columns that should exist
    columns_to_add = [
        # Comprehensive scoring system columns
        ("new_score", "FLOAT"),
        ("total_steps", "INTEGER"),
        ("optimal_steps", "INTEGER"),
        ("backtrack_count", "INTEGER"),
        ("collision_count", "INTEGER"),
        ("dead_end_entries", "INTEGER"),
        ("avg_latency_ms", "FLOAT"),
    ]
    
    added_count = 0
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE scores ADD COLUMN {column_name} {column_type}")
                print(f"[OK] Added column: {column_name} ({column_type})")
                added_count += 1
            except sqlite3.OperationalError as e:
                print(f"[ERROR] Error adding column {column_name}: {e}")
        else:
            print(f"[SKIP] Column {column_name} already exists")
    
    conn.commit()
    conn.close()
    
    print()
    print("=" * 70)
    if added_count > 0:
        print(f"[SUCCESS] Added {added_count} new column(s)")
    else:
        print("[INFO] No new columns were added (all already exist)")
    
    print()
    print("NEXT STEP: Restart the backend server!")
    print("  cd backend")
    print("  python run_server.py")
    print("=" * 70)

if __name__ == "__main__":
    print("Adding missing columns to scores table...")
    print()
    add_missing_columns()

