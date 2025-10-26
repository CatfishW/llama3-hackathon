#!/usr/bin/env python3
"""
Migration script to add new_score and comprehensive metrics columns to scores table.
This preserves old scores and allows the new scoring system to coexist.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.database import engine

def add_new_score_columns():
    """Add new_score and metrics columns to scores table"""
    
    with engine.connect() as conn:
        print("Adding new_score and metrics columns to scores table...")
        
        # Add new_score column (nullable since existing scores won't have this)
        try:
            conn.execute(text("""
                ALTER TABLE scores 
                ADD COLUMN new_score FLOAT NULL
            """))
            print("✓ Added new_score column")
        except Exception as e:
            print(f"Note: new_score column might already exist: {e}")
        
        # Add comprehensive metrics columns
        metrics_columns = [
            ("total_steps", "INTEGER"),
            ("optimal_steps", "INTEGER"),
            ("backtrack_count", "INTEGER"),
            ("collision_count", "INTEGER"),
            ("dead_end_entries", "INTEGER"),
            ("avg_latency_ms", "FLOAT"),
        ]
        
        for col_name, col_type in metrics_columns:
            try:
                conn.execute(text(f"""
                    ALTER TABLE scores 
                    ADD COLUMN {col_name} {col_type} NULL
                """))
                print(f"✓ Added {col_name} column")
            except Exception as e:
                print(f"Note: {col_name} column might already exist: {e}")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("Note: Existing scores will have NULL for new_score and metrics.")
        print("New scores will populate both 'score' (deprecated) and 'new_score' fields.")

if __name__ == "__main__":
    print("="*60)
    print("Database Migration: Add New Score Columns")
    print("="*60)
    add_new_score_columns()
