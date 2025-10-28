import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import init_db
from ..deps import get_db
from ..models import ChatMessage, ChatSession, PromptTemplate
from ..services.provider_factory import get_provider
from ..providers.mqtt_provider import MQTTProvider


router = APIRouter(prefix="/api/chat", tags=["chat"])


DEFAULT_PROMPTS: List[schemas.ChatPresetOut] = [
    schemas.ChatPresetOut(
        key="owogpt_general",
        title="OwOGPT Assistant",
        description="General-purpose, helpful assistant",
        system_prompt=(
            "You are OwOGPT, a helpful AI assistant. Provide clear, concise, and accurate responses."
        ),
    ),
    schemas.ChatPresetOut(
        key="developer",
        title="Developer Mode",
        description="More technical, concise answers with code snippets when useful",
        system_prompt=(
            "You are a senior software engineer assistant. Prefer precise, production-grade suggestions."
        ),
    ),
]


def _serialize_session(session: ChatSession) -> schemas.ChatSessionOut:
    return schemas.ChatSessionOut.model_validate(session, from_attributes=True)


def _serialize_message(message: ChatMessage) -> schemas.ChatMessageOut:
    metadata = None
    if message.metadata_json:
        try:
            metadata = json.loads(message.metadata_json)
        except json.JSONDecodeError:
            metadata = None
    return schemas.ChatMessageOut(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        metadata=metadata,
        request_id=message.request_id,
        created_at=message.created_at,
    )


def _default_prompt() -> str:
    return DEFAULT_PROMPTS[0].system_prompt


@router.get("/presets", response_model=List[schemas.ChatPresetOut])
def list_presets() -> List[schemas.ChatPresetOut]:
    return DEFAULT_PROMPTS


@router.get("/sessions", response_model=List[schemas.ChatSessionSummary])
def list_sessions(
    db: Session = Depends(get_db),
) -> List[schemas.ChatSessionSummary]:
    sessions = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    results: List[schemas.ChatSessionSummary] = []
    for session in sessions:
        last_message = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        preview: Optional[str] = None
        if last_message and last_message.content:
            preview = last_message.content.strip()
            if len(preview) > 180:
                preview = preview[:177] + "..."
        base = _serialize_session(session).model_dump()
        results.append(schemas.ChatSessionSummary(**base, last_message_preview=preview))
    return results


@router.post("/sessions", response_model=schemas.ChatSessionOut)
async def create_session(
    payload: schemas.ChatSessionCreate,
    db: Session = Depends(get_db),
) -> schemas.ChatSessionOut:
    init_db()
    template: Optional[PromptTemplate] = None
    if payload.template_id:
        template = db.query(PromptTemplate).filter(PromptTemplate.id == payload.template_id).first()

    system_prompt = payload.system_prompt or (template.content if template else _default_prompt())
    title = payload.title or (template.title if template else "New Chat")

    now = datetime.utcnow()
    session = ChatSession(
        session_key=f"anon-{uuid.uuid4().hex[:10]}",
        user_id=None,
        template_id=template.id if template else None,
        title=title,
        system_prompt=system_prompt,
        temperature=payload.temperature,
        top_p=payload.top_p,
        max_tokens=payload.max_tokens,
        message_count=0,
        created_at=now,
        updated_at=now,
        last_used_at=now,
    )

    db.add(session)
    db.commit()
    db.refresh(session)
    return _serialize_session(session)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
) -> dict:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.patch("/sessions/{session_id}", response_model=schemas.ChatSessionOut)
async def update_session(
    session_id: int,
    payload: schemas.ChatSessionUpdate,
    db: Session = Depends(get_db),
) -> schemas.ChatSessionOut:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.template_id is not None:
        template = db.query(PromptTemplate).filter(PromptTemplate.id == payload.template_id).first()
        session.template_id = template.id if template else None
        if template and not payload.system_prompt:
            session.system_prompt = template.content
        if template and not payload.title:
            session.title = template.title

    prev_prompt = session.system_prompt or ""

    if payload.title is not None:
        session.title = payload.title.strip() or session.title
    if payload.system_prompt is not None:
        session.system_prompt = payload.system_prompt
    if payload.temperature is not None:
        session.temperature = payload.temperature
    if payload.top_p is not None:
        session.top_p = payload.top_p
    if payload.max_tokens is not None:
        session.max_tokens = payload.max_tokens

    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    # If system_prompt changed and session has messages, delete MQTT session and reset locally
    if payload.system_prompt is not None and prev_prompt != (payload.system_prompt or ""):
        prompt_changed = True
        has_messages = session.message_count > 0
        
        if has_messages:
            # Delete MQTT session to clear server-side history
            try:
                MQTTProvider.delete_session(session.session_key)
                print(f"[MQTT] Deleted session {session.session_key} due to template change")
            except Exception as e:
                print(f"[MQTT] Failed to delete session: {e}")
            
            # Clear local message history
            db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
            session.message_count = 0
            print(f"[API] Cleared {session.message_count} messages locally")
        
        # Push new template to MQTT (with reset=True to ensure clean state)
        try:
            MQTTProvider.update_template(session.session_key, payload.system_prompt or "", reset=True)
        except Exception as e:
            print(f"[MQTT] Failed to update template: {e}")

    return _serialize_session(session)


@router.get("/sessions/{session_id}/messages", response_model=List[schemas.ChatMessageOut])
async def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=500),
) -> List[schemas.ChatMessageOut]:
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return [_serialize_message(m) for m in messages]


@router.post("/messages", response_model=schemas.ChatMessageSendResponse)
async def send_message(
    payload: schemas.ChatMessageSendRequest,
    db: Session = Depends(get_db),
) -> schemas.ChatMessageSendResponse:
    session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    template: Optional[PromptTemplate] = None
    if payload.template_id:
        template = db.query(PromptTemplate).filter(PromptTemplate.id == payload.template_id).first()
        if template and session.template_id != template.id:
            session.template_id = template.id
            if not payload.system_prompt:
                session.system_prompt = template.content

    if payload.system_prompt is not None:
        session.system_prompt = payload.system_prompt

    effective_temperature = payload.temperature if payload.temperature is not None else session.temperature
    effective_top_p = payload.top_p if payload.top_p is not None else session.top_p
    effective_max_tokens = payload.max_tokens if payload.max_tokens is not None else session.max_tokens

    now = datetime.utcnow()
    session.updated_at = now
    session.last_used_at = now

    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.content,
        metadata_json=None,
        request_id=None,
        created_at=now,
    )
    session.message_count = (session.message_count or 0) + 1

    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(session)

    provider = get_provider()

    try:
        resp = await provider.chat(
            session_key=session.session_key,
            message=payload.content,
            system_prompt=session.system_prompt,
            temperature=effective_temperature,
            top_p=effective_top_p,
            max_tokens=effective_max_tokens,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Timed out waiting for model response")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to contact LLM backend: {exc}") from exc

    assistant_content: Optional[str] = None
    if isinstance(resp, dict):
        candidate = resp.get("content")
        if isinstance(candidate, str) and candidate.strip():
            assistant_content = candidate
        if not assistant_content:
            raw = resp.get("raw")
            if isinstance(raw, dict):
                assistant_content = raw.get("response") or raw.get("content")
            elif isinstance(raw, str):
                assistant_content = raw

    if not assistant_content:
        assistant_content = "(no response)"

    now_a = datetime.utcnow()
    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=assistant_content,
        metadata_json=json.dumps(resp.get("raw")) if isinstance(resp.get("raw"), dict) else None,
        request_id=resp.get("request_id"),
        created_at=now_a,
    )
    session.message_count = (session.message_count or 0) + 1
    session.updated_at = now_a
    session.last_used_at = now_a

    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    db.refresh(session)

    return schemas.ChatMessageSendResponse(
        session=_serialize_session(session),
        user_message=_serialize_message(user_message),
        assistant_message=_serialize_message(assistant_message),
        raw_response=resp.get("raw") if isinstance(resp.get("raw"), dict) else None,
    )


