from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import User
from ..schemas import UserSearch
from ..deps import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/search", response_model=List[UserSearch])
def search_users(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search for users by name or email"""
    users = db.query(User).filter(
        and_(
            User.id != current_user.id,
            User.profile_visible == True,
            or_(
                User.full_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%")
            )
        )
    ).limit(20).all()
    
    return users

@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "profile_picture": current_user.profile_picture,
        "profile_visible": current_user.profile_visible,
        "allow_friend_requests": current_user.allow_friend_requests,
        "created_at": current_user.created_at,
        "is_online": current_user.is_online,
        "last_seen": current_user.last_seen
    }
