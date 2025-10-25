"""Add announcements table to the database"""
from app.database import engine, Base
from app.models import Announcement
from sqlalchemy import inspect

# Check if table exists
inspector = inspect(engine)
existing_tables = inspector.get_table_names()

if 'announcements' not in existing_tables:
    print("Creating announcements table...")
    Announcement.__table__.create(engine)
    print("✓ Announcements table created successfully!")
else:
    print("✓ Announcements table already exists.")
