from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class FriendshipStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: int

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    school: Optional[str] = None
    birthday: Optional[date] = None
    bio: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    profile_picture: Optional[str] = None
    level: int = 1
    points: int = 0
    rank: int = 0
    is_online: bool = False
    last_seen: datetime
    created_at: datetime
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    school: Optional[str] = None
    birthday: Optional[date] = None
    bio: Optional[str] = None
    status: Optional[str] = None

class UserSearch(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    level: int = 1
    is_online: bool = False
    class Config:
        from_attributes = True

# Template schemas
class TemplateBase(BaseModel):
    title: str
    description: Optional[str] = ""
    content: str
    is_active: bool = True
    version: int = 1

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    version: Optional[int] = None

class TemplateOut(TemplateBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Leaderboard / score
class ScoreCreate(BaseModel):
    template_id: int
    session_id: str
    score: float
    survival_time: float = 0
    oxygen_collected: int = 0
    germs: int = 0

class ScoreOut(BaseModel):
    id: int
    user_id: int
    template_id: int
    session_id: str
    score: float
    survival_time: float
    oxygen_collected: int
    germs: int
    created_at: datetime
    class Config:
        from_attributes = True

class LeaderboardEntry(BaseModel):
    rank: int
    user_email: str
    template_id: int
    template_title: str
    score: float
    session_id: str
    created_at: datetime

# MQTT Test
class PublishStateIn(BaseModel):
    session_id: str
    template_id: int
    state: dict

# Profile schemas
class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    school: Optional[str] = None
    birthday: Optional[date] = None
    bio: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None

class PrivacySettings(BaseModel):
    profile_visible: bool = True
    allow_friend_requests: bool = True
    show_online_status: bool = True

class NotificationSettings(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    friend_request_notifications: bool = True
    message_notifications: bool = True

class SecuritySettings(BaseModel):
    two_factor_enabled: bool = False
    current_password: Optional[str] = None
    new_password: Optional[str] = None

# Friendship schemas
class FriendshipCreate(BaseModel):
    requested_id: int

class FriendshipRespond(BaseModel):
    user_id: int
    accept: bool

class FriendshipOut(BaseModel):
    id: int
    requester_id: int
    requested_id: int
    status: FriendshipStatus
    created_at: datetime
    requester: UserSearch
    requested: UserSearch
    class Config:
        from_attributes = True

class FriendOut(BaseModel):
    friendship_id: int
    user: UserSearch
    created_at: datetime
    class Config:
        from_attributes = True

# Message schemas
class MessageCreate(BaseModel):
    recipient_id: int
    content: str
    message_type: str = "text"

class MessageOut(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    content: str
    message_type: str
    file_url: Optional[str] = None
    is_read: bool
    created_at: datetime
    sender: UserSearch
    recipient: UserSearch
    class Config:
        from_attributes = True

class ConversationOut(BaseModel):
    user: UserSearch
    last_message: Optional[MessageOut] = None
    unread_count: int = 0

# Settings schemas
class UserSettingsOut(BaseModel):
    theme: str = "dark"
    language: str = "en"
    timezone: str = "UTC"
    privacy: PrivacySettings
    notifications: NotificationSettings
    class Config:
        from_attributes = True

class UserSettingsUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
