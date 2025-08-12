#!/usr/bin/env python3
"""
Quick Database Reset Script

Simple script for common cleanup operations during development.
"""

import sys
import os

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, PromptTemplate, Score, Friendship, Message, UserSettings

def quick_reset():
    """Quick reset for development - keeps users but cleans data"""
    db = SessionLocal()
    
    try:
        print("🗑️  Quick Database Reset (Development Mode)")
        print("=" * 45)
        
        # Count before deletion
        messages_count = db.query(Message).count()
        friendships_count = db.query(Friendship).count()
        scores_count = db.query(Score).count()
        templates_count = db.query(PromptTemplate).count()
        
        # Delete user-generated content
        db.query(Message).delete()
        db.query(Friendship).delete()
        db.query(Score).delete()
        db.query(PromptTemplate).delete()
        
        # Reset user stats
        users = db.query(User).all()
        for user in users:
            user.level = 1
            user.points = 0
            user.rank = 0
            user.is_online = False
        
        db.commit()
        
        print(f"✅ Deleted {messages_count} messages")
        print(f"✅ Deleted {friendships_count} friendships")
        print(f"✅ Deleted {scores_count} scores")
        print(f"✅ Deleted {templates_count} templates")
        print(f"✅ Reset stats for {len(users)} users")
        print("\n🎯 Database reset complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    quick_reset()
