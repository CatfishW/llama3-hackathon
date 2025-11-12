from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models import User, UserSettings
from ..schemas import UserSettingsOut, UserSettingsUpdate, PrivacySettings, NotificationSettings
from ..deps import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/")
def get_user_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user settings"""
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    
    if not user_settings:
        # Create default settings if they don't exist
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    
    # Return format that frontend expects
    return {
        "email_notifications": current_user.email_notifications,
        "friend_requests": current_user.allow_friend_requests,
        "message_notifications": current_user.message_notifications,
        "leaderboard_visibility": current_user.profile_visible,
        "profile_visibility": "public" if current_user.profile_visible else "private",
        "theme": user_settings.theme or "dark",
        "language": user_settings.language or "en",
        "timezone": user_settings.timezone or "UTC"
    }

@router.put("/")
def update_all_settings(
    new_settings: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update all user settings at once"""
    # Update user settings
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
    
    # Update general settings (theme, language, timezone)
    if 'theme' in new_settings:
        user_settings.theme = new_settings['theme']
    if 'language' in new_settings:
        user_settings.language = new_settings['language']
    if 'timezone' in new_settings:
        user_settings.timezone = new_settings['timezone']
    
    user_settings.updated_at = datetime.utcnow()
    
    # Update user notification and privacy settings
    if 'email_notifications' in new_settings:
        current_user.email_notifications = new_settings['email_notifications']
    if 'friend_requests' in new_settings:
        current_user.allow_friend_requests = new_settings['friend_requests']
    if 'message_notifications' in new_settings:
        current_user.message_notifications = new_settings['message_notifications']
    if 'leaderboard_visibility' in new_settings:
        # This could be a new field or mapped to profile_visible
        current_user.profile_visible = new_settings['leaderboard_visibility']
    if 'profile_visibility' in new_settings:
        current_user.profile_visible = new_settings['profile_visibility'] != 'private'
    
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Settings updated successfully"}

@router.put("/general")
def update_general_settings(
    settings: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update general settings (theme, language, timezone)"""
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.add(user_settings)
    
    update_data = settings.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user_settings, field, value)
    
    user_settings.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "General settings updated successfully"}

@router.put("/privacy")
def update_privacy_settings(
    settings: PrivacySettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update privacy settings"""
    current_user.profile_visible = settings.profile_visible
    current_user.allow_friend_requests = settings.allow_friend_requests
    current_user.show_online_status = settings.show_online_status
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Privacy settings updated successfully"}

@router.put("/notifications")
def update_notification_settings(
    settings: NotificationSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update notification settings"""
    current_user.email_notifications = settings.email_notifications
    current_user.push_notifications = settings.push_notifications
    current_user.friend_request_notifications = settings.friend_request_notifications
    current_user.message_notifications = settings.message_notifications
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Notification settings updated successfully"}

@router.delete("/account")
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user account and all associated data"""
    # This is a destructive operation - in production you might want to:
    # 1. Require password confirmation
    # 2. Send email confirmation
    # 3. Add a grace period before actual deletion
    # 4. Anonymize data instead of hard delete
    
    # For now, we'll just mark the account as deleted
    current_user.email = f"deleted_{current_user.id}@deleted.com"
    current_user.profile_visible = False
    current_user.allow_friend_requests = False
    current_user.is_online = False
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Account deletion initiated"}

@router.get("/export")
def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export user data (GDPR compliance)"""
    # In a real implementation, this would:
    # 1. Generate a comprehensive data export
    # 2. Include all user data, messages, friends, etc.
    # 3. Return a downloadable file or email a link
    
    user_data = {
        "profile": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "school": current_user.school,
            "birthday": current_user.birthday.isoformat() if current_user.birthday else None,
            "bio": current_user.bio,
            "status": current_user.status,
            "level": current_user.level,
            "points": current_user.points,
            "rank": current_user.rank,
            "created_at": current_user.created_at.isoformat(),
            "updated_at": current_user.updated_at.isoformat()
        },
        "settings": {
            "privacy": {
                "profile_visible": current_user.profile_visible,
                "allow_friend_requests": current_user.allow_friend_requests,
                "show_online_status": current_user.show_online_status
            },
            "notifications": {
                "email_notifications": current_user.email_notifications,
                "push_notifications": current_user.push_notifications,
                "friend_request_notifications": current_user.friend_request_notifications,
                "message_notifications": current_user.message_notifications
            }
        }
    }
    
    return {
        "message": "Data export prepared",
        "data": user_data,
        "export_date": datetime.utcnow().isoformat()
    }
