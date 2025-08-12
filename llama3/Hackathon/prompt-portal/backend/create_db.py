#!/usr/bin/env python3
"""
Script to manually create the database with the correct schema
"""
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app import models

def create_database():
    """Create all tables in the database"""
    print("Creating database tables...")
    
    # Drop all existing tables first
    Base.metadata.drop_all(bind=engine)
    print("Dropped existing tables (if any)")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Created all tables successfully")
    
    print("Database created successfully!")

if __name__ == "__main__":
    create_database()
