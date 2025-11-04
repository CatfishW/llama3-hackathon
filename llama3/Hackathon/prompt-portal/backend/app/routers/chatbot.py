import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..models import ChatMessage, ChatSession, PromptTemplate
from ..mqtt import send_chat_message, publish_template_update

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])


DEFAULT_PROMPTS: List[schemas.ChatPresetOut] = [
    schemas.ChatPresetOut(
        key="prompt_portal",
        title="Prompt Portal Assistant",
        description="Goal-focused assistant for testing and refining prompt templates",
        system_prompt=(
            "You are an AI assistant helping users test and refine their prompt templates. "
            "Provide thoughtful, helpful responses that demonstrate how the prompt template "
            "affects your behavior. Be clear, concise, and adapt to the style and tone specified "
            "in the user's prompt template. If the prompt asks you to respond in a specific format "
            "(JSON, etc.), follow that format exactly."
        ),
    ),
    schemas.ChatPresetOut(
        key="general",
        title="General Assistant",
        description="Friendly, direct assistant with no specialized persona",
        system_prompt="You are a helpful AI assistant. Provide clear, concise, and accurate responses.",
    ),
    schemas.ChatPresetOut(
        key="maze",
        title="Maze Hint Strategist",
        description="JSON-formatted navigator designed for the maze LAM",
        system_prompt=(
            "You are a Large Action Model (LAM) guiding players through a maze game.\n"
            "You provide strategic hints and pathfinding advice. Be concise and helpful.\n"
            'Always respond in JSON format with keys: "hint" (string), "suggestion" (string).'
        ),
    ),
    schemas.ChatPresetOut(
        key="driving",
        title="Physics Study Buddy",
        description="Playful peer agent for driving/forces learning scenarios",
        system_prompt=(
            "You are Cap, a goofy peer agent in a physics learning game about forces and motion.\n"
            "Your role is to learn from the player's explanations. Never directly give the right answer.\n"
            "Keep responses under 50 words. Be playful, use first person, and encourage the player to explain their reasoning.\n"
            "Always end with state tags: <Cont or EOS><PlayerOp:x><AgentOP:y>"
        ),
    ),
]


def _load_template(db: Session, user_id: int, template_id: Optional[int]) -> Optional[PromptTemplate]:
    if not template_id:
        return None
    tpl = (
        db.query(PromptTemplate)
        .filter(PromptTemplate.id == template_id, PromptTemplate.user_id == user_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found or not owned by user")
    return tpl


def _serialize_session(session: ChatSession) -> schemas.ChatSessionOut:
    return schemas.ChatSessionOut.model_validate(session, from_attributes=True)


def _serialize_summary(session: ChatSession, last_message: Optional[ChatMessage]) -> schemas.ChatSessionSummary:
    base = _serialize_session(session).model_dump()
    preview: Optional[str] = None
    if last_message and last_message.content:
        preview = last_message.content.strip()
        if len(preview) > 180:
            preview = preview[:177] + "..."
    return schemas.ChatSessionSummary(**base, last_message_preview=preview)


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
    user=Depends(get_current_user),
) -> List[schemas.ChatSessionSummary]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    results: List[schemas.ChatSessionSummary] = []
    for session in sessions:
        last_message = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        results.append(_serialize_summary(session, last_message))
    return results


@router.post("/sessions", response_model=schemas.ChatSessionOut)
async def create_session(
    payload: schemas.ChatSessionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> schemas.ChatSessionOut:
    template = _load_template(db, user.id, payload.template_id)

    system_prompt = payload.system_prompt or (template.content if template else _default_prompt())
    title = payload.title or (template.title if template else "New Chat")

    now = datetime.utcnow()
    session = ChatSession(
        session_key=f"user{user.id}-{uuid.uuid4().hex[:10]}",
        user_id=user.id,
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


@router.patch("/sessions/{session_id}", response_model=schemas.ChatSessionOut)
async def update_session(
    session_id: int,
    payload: schemas.ChatSessionUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> schemas.ChatSessionOut:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.template_id is not None:
        template = _load_template(db, user.id, payload.template_id)
        session.template_id = template.id if template else None
        if template and not payload.system_prompt:
            session.system_prompt = template.content
        if template and not payload.title:
            session.title = template.title

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
    
    # If system_prompt changed, publish update to MQTT so llama.cpp deployment uses new prompt
    if payload.system_prompt is not None and (session.system_prompt or "") != (payload.system_prompt or ""):
        publish_template_update(session.session_key, payload.system_prompt)
    
    db.commit()
    db.refresh(session)

    return _serialize_session(session)


@router.post("/sessions/{session_id}/reset", response_model=schemas.ChatSessionOut)
async def reset_session(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> schemas.ChatSessionOut:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.session_key = f"user{user.id}-{uuid.uuid4().hex[:10]}"
    session.message_count = 0
    session.updated_at = datetime.utcnow()
    session.last_used_at = session.updated_at

    db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
    db.commit()
    db.refresh(session)

    return _serialize_session(session)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return {"ok": True}


@router.get("/sessions/{session_id}/messages", response_model=List[schemas.ChatMessageOut])
async def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    limit: int = Query(default=200, ge=1, le=500),
) -> List[schemas.ChatMessageOut]:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return [_serialize_message(msg) for msg in messages]


@router.post("/messages", response_model=schemas.ChatMessageSendResponse)
async def send_message(
    payload: schemas.ChatMessageSendRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> schemas.ChatMessageSendResponse:
    # Check MQTT connection health before processing
    from ..mqtt import mqtt_client
    if not mqtt_client or not mqtt_client.is_connected():
        raise HTTPException(
            status_code=503,
            detail="LLM backend connection unavailable. Please try again in a moment."
        )
    
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    template = _load_template(db, user.id, payload.template_id)

    if template and session.template_id != template.id:
        session.template_id = template.id
        if not payload.system_prompt:
            session.system_prompt = template.content
        if not payload.content.strip():
            raise HTTPException(status_code=400, detail="Message content cannot be empty")

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

    mqtt_payload = {
        "sessionId": session.session_key,
        "message": payload.content,
    }
    if session.system_prompt:
        mqtt_payload["systemPrompt"] = session.system_prompt
    if effective_temperature is not None:
        mqtt_payload["temperature"] = effective_temperature
    if effective_top_p is not None:
        mqtt_payload["topP"] = effective_top_p
    if effective_max_tokens is not None:
        mqtt_payload["maxTokens"] = effective_max_tokens

    try:
        # Increased timeout to 90 seconds for LLM responses
        response_payload = await send_chat_message(mqtt_payload, timeout=90.0)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The AI model is taking longer than usual to respond. Please try again."
        )
    except RuntimeError as exc:
        if "MQTT connection" in str(exc):
            raise HTTPException(
                status_code=503,
                detail="LLM backend connection lost. Reconnecting... Please try again in a moment."
            )
        raise HTTPException(status_code=502, detail=f"Backend error: {str(exc)}") from exc
    except Exception as exc:  # pragma: no cover - surface error to client
        raise HTTPException(
            status_code=502,
            detail=f"Failed to contact LLM backend. Please try again. Error: {str(exc)}"
        ) from exc

    # Reload session to pick up assistant message count update
    db.refresh(session)

    assistant_message_data = response_payload.get("assistant_message")
    assistant_message: Optional[ChatMessage]

    if assistant_message_data and assistant_message_data.get("id"):
        assistant_message = db.query(ChatMessage).filter(ChatMessage.id == assistant_message_data["id"]).first()
    else:
        request_id = response_payload.get("request_id")
        assistant_message = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id, ChatMessage.request_id == request_id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

    if not assistant_message:
        assistant_content: Optional[str] = None
        if assistant_message_data and isinstance(assistant_message_data, dict):
            raw_content = assistant_message_data.get("content")
            if isinstance(raw_content, str) and raw_content.strip():
                assistant_content = raw_content

        if not assistant_content:
            candidate = response_payload.get("content")
            if isinstance(candidate, str) and candidate.strip():
                assistant_content = candidate

        if not assistant_content:
            raw_field = response_payload.get("raw")
            if isinstance(raw_field, dict):
                fallback = raw_field.get("response") or raw_field.get("content")
                if isinstance(fallback, str) and fallback.strip():
                    assistant_content = fallback
            elif isinstance(raw_field, str) and raw_field.strip():
                assistant_content = raw_field

        if not assistant_content:
            assistant_content = "Assistant response unavailable."

        metadata_dict: Optional[dict] = None
        if assistant_message_data and isinstance(assistant_message_data, dict):
            candidate_meta = assistant_message_data.get("metadata")
            if isinstance(candidate_meta, dict):
                metadata_dict = candidate_meta
        if metadata_dict is None:
            raw_field = response_payload.get("raw")
            if isinstance(raw_field, dict):
                metadata_dict = raw_field

        try:
            now_assistant = datetime.utcnow()
            assistant_message = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=assistant_content,
                metadata_json=json.dumps(metadata_dict) if metadata_dict is not None else None,
                request_id=response_payload.get("request_id"),
                created_at=now_assistant,
            )
            session.message_count = (session.message_count or 0) + 1
            session.updated_at = now_assistant
            session.last_used_at = now_assistant
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)
            db.refresh(session)
        except Exception as exc:  # pragma: no cover - persistence failure should surface
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to persist assistant response: {exc}") from exc

    raw_response = response_payload.get("raw") if isinstance(response_payload.get("raw"), dict) else None

    return schemas.ChatMessageSendResponse(
        session=_serialize_session(session),
        user_message=_serialize_message(user_message),
        assistant_message=_serialize_message(assistant_message),
        raw_response=raw_response,
    )
