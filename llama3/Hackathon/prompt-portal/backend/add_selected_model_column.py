#!/usr/bin/env python3
"""
Migration script to add selected_model column to users table.

This adds support for multi-model selection in the user preferences.
"""

import sqlite3
import os

def migrate():
    """Add selected_model column to users table"""
    db_path = "app.db"
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Skipping migration.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'selected_model' in columns:
            print("Column 'selected_model' already exists. Skipping migration.")
            return
        
        # Add the selected_model column
        print("Adding 'selected_model' column to users table...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN selected_model VARCHAR(255) DEFAULT 'TangLLM'
        """)
        
        conn.commit()
        print("✓ Successfully added 'selected_model' column")
        
    except sqlite3.Error as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
