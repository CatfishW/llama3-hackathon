from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True, default=None)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_key = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=True)
    title = Column(String(255), nullable=False, default="New Chat")
    template_id = Column(Integer, ForeignKey("prompt_templates.id"), nullable=True)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Integer, nullable=True)
    top_p = Column(Integer, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("PromptTemplate")
    messages = relationship("ChatMessage", back_populates="session", cascade="all,delete")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    request_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


