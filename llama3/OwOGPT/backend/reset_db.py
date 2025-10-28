"""Reset database with updated schema"""
import os
import sys

# Delete existing database
db_path = "app.db"
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"✓ Deleted old database: {db_path}")

# Import and recreate
from app.database import engine, Base, init_db

# Drop all tables and recreate
Base.metadata.drop_all(bind=engine)
print("✓ Dropped all tables")

init_db()
print("✓ Created new tables with updated schema")
print("\n✅ Database reset complete! You can now save templates.")

