from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


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
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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


