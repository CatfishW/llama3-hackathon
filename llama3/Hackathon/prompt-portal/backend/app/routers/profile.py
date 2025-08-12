from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from datetime import datetime

from ..database import get_db
from ..models import User
from ..schemas import UserOut, ProfileUpdate, PrivacySettings, NotificationSettings, SecuritySettings
from ..deps import get_current_user
from ..utils.security import hash_password, verify_password

router = APIRouter(prefix="/api/profile", tags=["profile"])

UPLOAD_DIRECTORY = "uploads/profile_pictures"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

@router.get("/me", response_model=UserOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile"""
    return current_user

@router.put("/update", response_model=UserOut)
def update_profile(
    profile_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user profile information"""
    update_data = profile_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/upload-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload profile picture"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    filename = f"{current_user.id}_{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Update user profile
    current_user.profile_picture = f"/uploads/profile_pictures/{filename}"
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"profile_picture": current_user.profile_picture}

@router.get("/privacy", response_model=PrivacySettings)
def get_privacy_settings(current_user: User = Depends(get_current_user)):
    """Get privacy settings"""
    return PrivacySettings(
        profile_visible=current_user.profile_visible,
        allow_friend_requests=current_user.allow_friend_requests,
        show_online_status=current_user.show_online_status
    )

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

@router.get("/notifications", response_model=NotificationSettings)
def get_notification_settings(current_user: User = Depends(get_current_user)):
    """Get notification settings"""
    return NotificationSettings(
        email_notifications=current_user.email_notifications,
        push_notifications=current_user.push_notifications,
        friend_request_notifications=current_user.friend_request_notifications,
        message_notifications=current_user.message_notifications
    )

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

@router.put("/security")
def update_security_settings(
    settings: SecuritySettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update security settings"""
    if settings.new_password:
        if not settings.current_password:
            raise HTTPException(status_code=400, detail="Current password required")
        
        if not verify_password(settings.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Invalid current password")
        
        current_user.password_hash = hash_password(settings.new_password)
    
    current_user.two_factor_enabled = settings.two_factor_enabled
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Security settings updated successfully"}

@router.put("/online-status")
def update_online_status(
    is_online: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user online status"""
    current_user.is_online = is_online
    current_user.last_seen = datetime.utcnow()
    db.commit()
    
    return {"message": "Online status updated"}
