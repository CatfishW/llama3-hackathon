from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
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
    score: float  # Deprecated score (old system)
    new_score: float | None = None  # New comprehensive scoring system
    survival_time: float = 0
    oxygen_collected: int = 0
    germs: int = 0
    mode: str = "manual"
    
    # Comprehensive metrics for new scoring system
    total_steps: int | None = None
    optimal_steps: int | None = None
    backtrack_count: int | None = None
    collision_count: int | None = None
    dead_end_entries: int | None = None
    avg_latency_ms: float | None = None
    
    # Driving Game metrics
    driving_game_consensus_reached: bool | None = None
    driving_game_message_count: int | None = None
    driving_game_duration_seconds: float | None = None
    driving_game_player_option: str | None = None
    driving_game_agent_option: str | None = None

class ScoreOut(BaseModel):
    id: int
    user_id: int
    template_id: int
    session_id: str
    score: float  # Deprecated score (old system)
    new_score: float | None = None  # New comprehensive scoring system
    survival_time: float
    oxygen_collected: int
    germs: int
    mode: str
    
    # Comprehensive metrics
    total_steps: int | None = None
    optimal_steps: int | None = None
    backtrack_count: int | None = None
    collision_count: int | None = None
    dead_end_entries: int | None = None
    avg_latency_ms: float | None = None
    
    created_at: datetime
    class Config:
        from_attributes = True

class LeaderboardEntry(BaseModel):
    rank: int
    user_email: str
    template_id: int
    template_title: str
    score: float  # Deprecated score (old system)
    new_score: float | None = None  # New comprehensive scoring system
    session_id: str
    created_at: datetime
    
    # Optionally include metrics for detailed view
    total_steps: int | None = None
    collision_count: int | None = None


# Driving Game Score schemas (separate from maze game)
class DrivingGameScoreCreate(BaseModel):
    template_id: int
    session_id: str
    score: float
    message_count: int
    duration_seconds: float
    player_option: str  # a, b, or c
    agent_option: str   # a, b, or c


class DrivingGameScoreOut(BaseModel):
    id: int
    user_id: int
    template_id: int
    session_id: str
    score: float
    consensus_reached: bool
    message_count: int
    duration_seconds: float
    player_option: str
    agent_option: str
    created_at: datetime
    class Config:
        from_attributes = True


class DrivingGameLeaderboardEntry(BaseModel):
    rank: int
    user_email: str
    template_id: int
    template_title: str
    score: float
    message_count: int
    duration_seconds: float
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


# Chat assistant schemas
class ChatSessionCreate(BaseModel):
    title: Optional[str] = None
    template_id: Optional[int] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    template_id: Optional[int] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatSessionOut(BaseModel):
    id: int
    session_key: str
    title: str
    template_id: Optional[int] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    message_count: int
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime

    class Config:
        from_attributes = True


class ChatSessionSummary(ChatSessionOut):
    last_message_preview: Optional[str] = None


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageSendRequest(BaseModel):
    session_id: int
    content: str = Field(..., min_length=1)
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    template_id: Optional[int] = None


class ChatMessageSendResponse(BaseModel):
    session: ChatSessionOut
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    raw_response: Optional[Dict[str, Any]] = None


class ChatPresetOut(BaseModel):
    key: str
    title: str
    description: Optional[str] = None
    system_prompt: str


# Announcement schemas
class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    announcement_type: str = Field(default="info", pattern="^(info|warning|success|error)$")
    priority: int = Field(default=0, ge=0, le=10)
    expires_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    announcement_type: Optional[str] = Field(None, pattern="^(info|warning|success|error)$")
    priority: Optional[int] = Field(None, ge=0, le=10)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class AnnouncementOut(BaseModel):
    id: int
    title: str
    content: str
    announcement_type: str
    priority: int
    is_active: bool
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True
