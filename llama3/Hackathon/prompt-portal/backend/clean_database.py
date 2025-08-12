#!/usr/bin/env python3
"""
Database Cleanup Script for LAM Prompt Portal

This script provides various options to clean up data from the database:
- Clean all data (nuclear option)
- Clean specific data types
- Clean data older than certain dates
- Clean test/demo data
- Reset user data but keep accounts
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import (
    User, PromptTemplate, Score, Friendship, Message, UserSettings,
    FriendshipStatus, Base
)

def get_db_session() -> Session:
    """Get a database session"""
    return SessionLocal()

def confirm_action(action: str) -> bool:
    """Ask user to confirm a destructive action"""
    response = input(f"\n⚠️  WARNING: {action}\nAre you sure? Type 'yes' to confirm: ")
    return response.lower() == 'yes'

def clean_all_data(db: Session) -> None:
    """🚨 NUCLEAR OPTION: Delete ALL data from all tables"""
    if not confirm_action("This will DELETE ALL DATA from the database!"):
        print("❌ Operation cancelled.")
        return
    
    print("🗑️  Cleaning all data...")
    
    # Delete in order to respect foreign key constraints
    tables_to_clean = [
        (UserSettings, "user settings"),
        (Message, "messages"),
        (Friendship, "friendships"),
        (Score, "scores"),
        (PromptTemplate, "prompt templates"),
        (User, "users")
    ]
    
    total_deleted = 0
    for model, name in tables_to_clean:
        count = db.query(model).count()
        if count > 0:
            db.query(model).delete()
            print(f"  ✅ Deleted {count} {name}")
            total_deleted += count
        else:
            print(f"  ℹ️  No {name} to delete")
    
    db.commit()
    print(f"\n🎯 Total records deleted: {total_deleted}")
    print("✅ All data cleaned successfully!")

def clean_user_data_only(db: Session) -> None:
    """Clean user-generated data but keep user accounts"""
    if not confirm_action("This will delete all user data (templates, scores, messages, friendships) but keep user accounts"):
        print("❌ Operation cancelled.")
        return
    
    print("🗑️  Cleaning user data...")
    
    # Delete user-generated content but keep accounts
    tables_to_clean = [
        (Message, "messages"),
        (Friendship, "friendships"),
        (Score, "scores"),
        (PromptTemplate, "prompt templates")
    ]
    
    total_deleted = 0
    for model, name in tables_to_clean:
        count = db.query(model).count()
        if count > 0:
            db.query(model).delete()
            print(f"  ✅ Deleted {count} {name}")
            total_deleted += count
        else:
            print(f"  ℹ️  No {name} to delete")
    
    # Reset user stats but keep accounts
    users = db.query(User).all()
    for user in users:
        user.level = 1
        user.points = 0
        user.rank = 0
        user.is_online = False
        user.last_seen = datetime.utcnow()
    
    db.commit()
    print(f"  ✅ Reset stats for {len(users)} users")
    print(f"\n🎯 Total records deleted: {total_deleted}")
    print("✅ User data cleaned successfully!")

def clean_old_data(db: Session, days: int) -> None:
    """Clean data older than specified number of days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    if not confirm_action(f"This will delete all data older than {days} days (before {cutoff_date.strftime('%Y-%m-%d')})"):
        print("❌ Operation cancelled.")
        return
    
    print(f"🗑️  Cleaning data older than {days} days...")
    
    # Clean old messages
    old_messages = db.query(Message).filter(Message.created_at < cutoff_date).count()
    if old_messages > 0:
        db.query(Message).filter(Message.created_at < cutoff_date).delete()
        print(f"  ✅ Deleted {old_messages} old messages")
    
    # Clean old scores
    old_scores = db.query(Score).filter(Score.created_at < cutoff_date).count()
    if old_scores > 0:
        db.query(Score).filter(Score.created_at < cutoff_date).delete()
        print(f"  ✅ Deleted {old_scores} old scores")
    
    # Clean old friendships (but keep accepted ones)
    old_friendships = db.query(Friendship).filter(
        Friendship.created_at < cutoff_date,
        Friendship.status != FriendshipStatus.ACCEPTED
    ).count()
    if old_friendships > 0:
        db.query(Friendship).filter(
            Friendship.created_at < cutoff_date,
            Friendship.status != FriendshipStatus.ACCEPTED
        ).delete()
        print(f"  ✅ Deleted {old_friendships} old pending/blocked friendships")
    
    db.commit()
    print("✅ Old data cleaned successfully!")

def clean_test_data(db: Session) -> None:
    """Clean test/demo data (users with test emails, demo templates)"""
    if not confirm_action("This will delete test users and demo data"):
        print("❌ Operation cancelled.")
        return
    
    print("🗑️  Cleaning test data...")
    
    # Find test users (emails containing 'test', 'demo', 'example')
    test_patterns = ['test', 'demo', 'example', 'temp', '@test.', '@demo.', '@example.']
    test_user_ids = []
    
    for pattern in test_patterns:
        test_users = db.query(User).filter(User.email.ilike(f'%{pattern}%')).all()
        test_user_ids.extend([user.id for user in test_users])
    
    test_user_ids = list(set(test_user_ids))  # Remove duplicates
    
    if test_user_ids:
        # Delete related data for test users
        deleted_messages = db.query(Message).filter(
            (Message.sender_id.in_(test_user_ids)) | 
            (Message.recipient_id.in_(test_user_ids))
        ).count()
        if deleted_messages > 0:
            db.query(Message).filter(
                (Message.sender_id.in_(test_user_ids)) | 
                (Message.recipient_id.in_(test_user_ids))
            ).delete()
            print(f"  ✅ Deleted {deleted_messages} test user messages")
        
        deleted_friendships = db.query(Friendship).filter(
            (Friendship.requester_id.in_(test_user_ids)) | 
            (Friendship.requested_id.in_(test_user_ids))
        ).count()
        if deleted_friendships > 0:
            db.query(Friendship).filter(
                (Friendship.requester_id.in_(test_user_ids)) | 
                (Friendship.requested_id.in_(test_user_ids))
            ).delete()
            print(f"  ✅ Deleted {deleted_friendships} test user friendships")
        
        deleted_scores = db.query(Score).filter(Score.user_id.in_(test_user_ids)).count()
        if deleted_scores > 0:
            db.query(Score).filter(Score.user_id.in_(test_user_ids)).delete()
            print(f"  ✅ Deleted {deleted_scores} test user scores")
        
        deleted_templates = db.query(PromptTemplate).filter(PromptTemplate.user_id.in_(test_user_ids)).count()
        if deleted_templates > 0:
            db.query(PromptTemplate).filter(PromptTemplate.user_id.in_(test_user_ids)).delete()
            print(f"  ✅ Deleted {deleted_templates} test user templates")
        
        deleted_settings = db.query(UserSettings).filter(UserSettings.user_id.in_(test_user_ids)).count()
        if deleted_settings > 0:
            db.query(UserSettings).filter(UserSettings.user_id.in_(test_user_ids)).delete()
            print(f"  ✅ Deleted {deleted_settings} test user settings")
        
        # Delete test users
        deleted_users = db.query(User).filter(User.id.in_(test_user_ids)).count()
        if deleted_users > 0:
            db.query(User).filter(User.id.in_(test_user_ids)).delete()
            print(f"  ✅ Deleted {deleted_users} test users")
    
    # Clean demo templates (titles containing 'test', 'demo', 'example')
    demo_templates = db.query(PromptTemplate).filter(
        (PromptTemplate.title.ilike('%test%')) |
        (PromptTemplate.title.ilike('%demo%')) |
        (PromptTemplate.title.ilike('%example%'))
    ).count()
    if demo_templates > 0:
        db.query(PromptTemplate).filter(
            (PromptTemplate.title.ilike('%test%')) |
            (PromptTemplate.title.ilike('%demo%')) |
            (PromptTemplate.title.ilike('%example%'))
        ).delete()
        print(f"  ✅ Deleted {demo_templates} demo templates")
    
    db.commit()
    print("✅ Test data cleaned successfully!")

def clean_messages(db: Session, days: int = None) -> None:
    """Clean messages (optionally older than specified days)"""
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = db.query(Message).filter(Message.created_at < cutoff_date)
        action_desc = f"messages older than {days} days"
    else:
        query = db.query(Message)
        action_desc = "all messages"
    
    if not confirm_action(f"This will delete {action_desc}"):
        print("❌ Operation cancelled.")
        return
    
    count = query.count()
    if count > 0:
        query.delete()
        db.commit()
        print(f"✅ Deleted {count} messages")
    else:
        print("ℹ️  No messages to delete")

def clean_friendships(db: Session, status: str = None) -> None:
    """Clean friendships (optionally filter by status)"""
    query = db.query(Friendship)
    action_desc = "all friendships"
    
    if status:
        if status.upper() == 'PENDING':
            query = query.filter(Friendship.status == FriendshipStatus.PENDING)
            action_desc = "pending friend requests"
        elif status.upper() == 'BLOCKED':
            query = query.filter(Friendship.status == FriendshipStatus.BLOCKED)
            action_desc = "blocked friendships"
    
    if not confirm_action(f"This will delete {action_desc}"):
        print("❌ Operation cancelled.")
        return
    
    count = query.count()
    if count > 0:
        query.delete()
        db.commit()
        print(f"✅ Deleted {count} friendships")
    else:
        print("ℹ️  No friendships to delete")

def show_database_stats(db: Session) -> None:
    """Show current database statistics"""
    print("\n📊 Current Database Statistics:")
    print("=" * 40)
    
    stats = [
        ("Users", db.query(User).count()),
        ("Prompt Templates", db.query(PromptTemplate).count()),
        ("Scores", db.query(Score).count()),
        ("Friendships", db.query(Friendship).count()),
        ("  - Pending", db.query(Friendship).filter(Friendship.status == FriendshipStatus.PENDING).count()),
        ("  - Accepted", db.query(Friendship).filter(Friendship.status == FriendshipStatus.ACCEPTED).count()),
        ("  - Blocked", db.query(Friendship).filter(Friendship.status == FriendshipStatus.BLOCKED).count()),
        ("Messages", db.query(Message).count()),
        ("User Settings", db.query(UserSettings).count()),
    ]
    
    for name, count in stats:
        print(f"{name:<20}: {count:>10}")
    
    print("=" * 40)

def main():
    parser = argparse.ArgumentParser(description="Database cleanup script for LAM Prompt Portal")
    parser.add_argument("--action", "-a", required=True, choices=[
        "stats", "clean-all", "clean-user-data", "clean-old", "clean-test", 
        "clean-messages", "clean-friendships"
    ], help="Action to perform")
    
    parser.add_argument("--days", "-d", type=int, help="Number of days for old data cleanup")
    parser.add_argument("--status", "-s", choices=["pending", "blocked"], help="Friendship status to clean")
    parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompts")
    
    args = parser.parse_args()
    
    print("🗄️  LAM Prompt Portal Database Cleanup Script")
    print("=" * 50)
    
    # Create database session
    db = get_db_session()
    
    try:
        if args.action == "stats":
            show_database_stats(db)
            
        elif args.action == "clean-all":
            clean_all_data(db)
            
        elif args.action == "clean-user-data":
            clean_user_data_only(db)
            
        elif args.action == "clean-old":
            days = args.days or 30  # Default to 30 days
            clean_old_data(db, days)
            
        elif args.action == "clean-test":
            clean_test_data(db)
            
        elif args.action == "clean-messages":
            clean_messages(db, args.days)
            
        elif args.action == "clean-friendships":
            clean_friendships(db, args.status)
            
        # Show final stats
        if args.action != "stats":
            show_database_stats(db)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    exit(main())
