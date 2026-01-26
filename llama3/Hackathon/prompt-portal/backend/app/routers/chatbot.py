import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..deps import get_current_user
from ..models import ChatMessage, ChatSession, PromptTemplate, User
from ..models_config import get_models_manager

router = APIRouter(prefix="/api/chatbot", tags=["chatbot"])
logger = logging.getLogger(__name__)


def _fallback_model_names(preferred: Optional[str]) -> List[str]:
    models_manager = get_models_manager()
    model_names = [model.name for model in models_manager.get_all_models()]
    if preferred and preferred in model_names:
        return [preferred] + [name for name in model_names if name != preferred]
    return model_names


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
    
    # Use selected_model from payload, or from user settings, or default
    selected_model = payload.selected_model
    if not selected_model:
        db_user = db.query(User).filter(User.id == user.id).first()
        selected_model = db_user.selected_model if db_user else "AGAII Cloud LLM"

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
        selected_model=selected_model,
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

    if payload.selected_model is not None:
        session.selected_model = payload.selected_model

    session.updated_at = datetime.utcnow()
    
    # System prompt is stored in the session and applied on the next message.
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
    from ..config import settings
    
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
        metadata_json=json.dumps({
            "image_urls": payload.image_urls,
            "video_urls": payload.metadata.get("video_urls") if payload.metadata else None
        }) if (payload.image_urls or (payload.metadata and payload.metadata.get("video_urls"))) else None,
        request_id=None,
        created_at=now,
    )
    session.message_count = (session.message_count or 0) + 1

    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(session)

    try:
        from ..services.llm_service import get_llm_service
        llm_service = get_llm_service()

        db_user = db.query(User).filter(User.id == user.id).first()
        preferred_model = session.selected_model or (db_user.selected_model if db_user else None)
        candidate_models = _fallback_model_names(preferred_model)

        def call_model(model_name: Optional[str]) -> str:
            if settings.LLM_VISION_ENABLED and payload.image_urls:
                system_prompt_value = session.system_prompt or _default_prompt()
                user_parts = [{"type": "text", "text": payload.content}]
                for url in payload.image_urls:
                    user_parts.append({"type": "image_url", "image_url": {"url": url}})
                messages = [
                    {"role": "system", "content": system_prompt_value},
                    {"role": "user", "content": user_parts},
                ]
                return llm_service.generate(
                    messages=messages,
                    temperature=effective_temperature,
                    top_p=effective_top_p,
                    max_tokens=effective_max_tokens,
                    model=model_name,
                    tools=None,
                    tool_choice="none"
                )

            return llm_service.process_message(
                session_id=session.session_key,
                system_prompt=session.system_prompt or _default_prompt(),
                user_message=payload.content,
                temperature=effective_temperature,
                top_p=effective_top_p,
                max_tokens=effective_max_tokens,
                use_tools=False,
                model=model_name
            )

        assistant_content = ""
        used_model: Optional[str] = None
        last_error: Optional[Exception] = None
        for model_name in candidate_models:
            try:
                assistant_content = call_model(model_name)
                used_model = model_name
                break
            except Exception as exc:
                last_error = exc
                continue

        if used_model is None:
            raise last_error or RuntimeError("No available models")

        if used_model != preferred_model:
            logger.warning(
                "LLM failure; switched model from %s to %s",
                preferred_model,
                used_model
            )
            session.selected_model = used_model
            if db_user:
                db_user.selected_model = used_model
            db.commit()
            db.refresh(session)

        response_payload = {
            "content": assistant_content,
            "request_id": f"sse-{uuid.uuid4().hex[:8]}",
            "assistant_message": {
                "content": assistant_content
            }
        }

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service error: {str(exc)}"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to contact LLM backend: {str(exc)}"
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


@router.post("/messages/stream")
async def send_message_stream(
    request: Request,
    payload: schemas.ChatMessageSendRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Send a message and stream the response over SSE.
    """
    from ..config import settings
    
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
        metadata_json=json.dumps({
            "image_urls": payload.image_urls,
            "video_urls": payload.metadata.get("video_urls") if payload.metadata else None
        }) if (payload.image_urls or (payload.metadata and payload.metadata.get("video_urls"))) else None,
        request_id=None,
        created_at=now,
    )
    session.message_count = (session.message_count or 0) + 1

    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(session)

    # Extract data needed for streaming (avoid accessing session objects in async generator)
    session_id_value = session.id
    user_message_id_value = user_message.id
    session_key_value = session.session_key
    system_prompt_value = session.system_prompt or _default_prompt()
    db_user = db.query(User).filter(User.id == user.id).first()
    preferred_model = session.selected_model or (db_user.selected_model if db_user else None)
    candidate_models = _fallback_model_names(preferred_model)

    # Create a generator that streams the response
    async def stream_generator():
        try:
            # Send metadata first (session and user message info)
            metadata = {
                "type": "metadata",
                "session_id": session_id_value,
                "user_message_id": user_message_id_value,
                "session_key": session_key_value
            }
            yield f"data: {json.dumps(metadata)}\n\n"
            
            full_content = ""

            from ..services.llm_service import get_llm_service
            llm_service = get_llm_service()
            used_model: Optional[str] = None
            last_error: Optional[str] = None

            for model_name in candidate_models:
                try:
                    if settings.LLM_VISION_ENABLED and payload.image_urls:
                        user_parts = [{"type": "text", "text": payload.content}]
                        for url in payload.image_urls:
                            user_parts.append({"type": "image_url", "image_url": {"url": url}})
                        messages = [
                            {"role": "system", "content": system_prompt_value},
                            {"role": "user", "content": user_parts},
                        ]
                        stream_iter = llm_service.agenerate_stream(
                            messages=messages,
                            temperature=effective_temperature,
                            top_p=effective_top_p,
                            max_tokens=effective_max_tokens,
                            model=model_name,
                            tools=None,
                            tool_choice="none"
                        )
                    else:
                        stream_iter = llm_service.aprocess_message_stream(
                            session_id=session_key_value,
                            system_prompt=system_prompt_value,
                            user_message=payload.content,
                            temperature=effective_temperature,
                            top_p=effective_top_p,
                            max_tokens=effective_max_tokens,
                            use_tools=False,
                            model=model_name
                        )

                    # Used to track if we successfully started streaming from this model
                    model_started = False
                    
                    async for chunk in stream_iter:
                        if not model_started:
                            model_started = True
                            used_model = model_name
                            if used_model != preferred_model:
                                logger.warning(
                                    "LLM failure; switched model from %s to %s",
                                    preferred_model,
                                    used_model
                                )
                                async def update_model_choice():
                                    def _sync_db_update():
                                        from ..database import SessionLocal
                                        db_switch = SessionLocal()
                                        try:
                                            session_update = db_switch.query(ChatSession).filter(ChatSession.id == session_id_value).first()
                                            if session_update:
                                                session_update.selected_model = used_model
                                                session_update.updated_at = datetime.utcnow()
                                                session_update.last_used_at = datetime.utcnow()
                                            user_update = db_switch.query(User).filter(User.id == user.id).first()
                                            if user_update:
                                                user_update.selected_model = used_model
                                            db_switch.commit()
                                        finally:
                                            db_switch.close()
                                    await asyncio.to_thread(_sync_db_update)
                                
                                asyncio.create_task(update_model_choice())

                        if isinstance(chunk, str) and chunk.startswith("Error:"):
                            last_error = chunk
                            model_started = False # Reset so we try next model
                            break
                        
                        full_content += chunk
                        chunk_data = {"type": "chunk", "content": chunk}
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                        await asyncio.sleep(0)
                        if await request.is_disconnected():
                            logger.info("Client disconnected during stream")
                            return
                    
                    if model_started:
                        break
                except Exception as exc:
                    last_error = str(exc)
                    continue

            if used_model is None:
                err_msg = last_error or "LLM error: no available models"
                yield f"data: {json.dumps({'type': 'error', 'error': err_msg})}\n\n"
                return

            # Save assistant message to database (offload to thread to keep stream smooth)
            def _save_assistant_message():
                from ..database import SessionLocal
                db_stream = SessionLocal()
                try:
                    request_id = f"stream-{uuid.uuid4().hex[:8]}"
                    now_assistant = datetime.utcnow()
                    assistant_message = ChatMessage(
                        session_id=session_id_value,
                        role="assistant",
                        content=full_content,
                        metadata_json=None,
                        request_id=request_id,
                        created_at=now_assistant,
                    )
                    
                    session_update = db_stream.query(ChatSession).filter(ChatSession.id == session_id_value).first()
                    if session_update:
                        session_update.message_count = (session_update.message_count or 0) + 1
                        session_update.updated_at = now_assistant
                        session_update.last_used_at = now_assistant
                    
                    db_stream.add(assistant_message)
                    db_stream.commit()
                    db_stream.refresh(assistant_message)
                    return assistant_message.id
                finally:
                    db_stream.close()

            assistant_msg_id = await asyncio.to_thread(_save_assistant_message)
            
            # Send completion with assistant message ID
            completion_data = {
                "type": "done",
                "assistant_message_id": assistant_msg_id,
                "full_content": full_content
            }
            yield f"data: {json.dumps(completion_data)}\n\n"
            
        except Exception as e:
            error_data = {"type": "error", "message": f"Streaming error: {str(e)}"}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Upload and extract text from PDF or Word documents"""
    import os
    import tempfile
    
    # Check file type
    file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
    if file_extension not in ['pdf', 'doc', 'docx']:
        raise HTTPException(status_code=400, detail="Only PDF and Word documents are supported")
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        extracted_text = ""
        
        if file_extension == 'pdf':
            # Extract text from PDF
            try:
                import PyPDF2
                with open(temp_file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        extracted_text += page.extract_text() + "\n"
            except ImportError:
                raise HTTPException(
                    status_code=500, 
                    detail="PDF support not available. Please install PyPDF2."
                )
        
        elif file_extension in ['doc', 'docx']:
            # Extract text from Word document
            try:
                import docx
                doc = docx.Document(temp_file_path)
                for paragraph in doc.paragraphs:
                    extracted_text += paragraph.text + "\n"
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="Word document support not available. Please install python-docx."
                )
        
        # Clean up extracted text
        extracted_text = extracted_text.strip()
        
        if not extracted_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from the document")
        
        return {
            "filename": file.filename,
            "text": extracted_text,
            "length": len(extracted_text)
        }
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Upload a video file."""
    import os
    import uuid as _uuid
    
    filename = file.filename or "uploaded_video"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    allowed = {"mp4", "webm", "ogg", "mov"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported video type. Use MP4/WEBM/OGG/MOV.")

    stored_filename = f"vid_{_uuid.uuid4().hex}.{ext}"
    uploads_dir = "uploads"
    os.makedirs(uploads_dir, exist_ok=True)
    final_path = os.path.join(uploads_dir, stored_filename)

    with open(final_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return {
        "filename": filename,
        "stored_filename": stored_filename,
        "url": f"/uploads/{stored_filename}",
    }


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Upload an image and return a base64 data URL for LLM vision APIs.

    Returns:
        {
          "filename": original filename,
          "stored_filename": name stored on server,
          "url": base64 data URL for LLM vision API consumption,
          "file_url": accessible URL under /uploads/ (for display),
          "ocr_text": extracted text (may be empty),
          "ocr_length": length of extracted text,
          "has_text": bool indicating if OCR produced non-empty text
        }

    Notes:
        - OCR uses pytesseract + Pillow if available; otherwise returns empty text.
        - For security, the image is re-saved via Pillow to ensure it's a valid image and strip any embedded metadata.
        - Supported formats: png, jpg, jpeg, webp, gif (gif: first frame only for OCR).
        - The 'url' field returns a base64 data URL for direct use with LLM vision APIs.
    """
    import os
    import uuid as _uuid
    import tempfile
    import base64
    import io

    # Validate content type / extension
    filename = file.filename or "uploaded_image"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    allowed = {"png", "jpg", "jpeg", "webp", "gif"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use PNG/JPG/JPEG/WEBP/GIF.")

    # Read file content to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    ocr_text = ""
    stored_filename = f"img_{_uuid.uuid4().hex}.{ext}"
    uploads_dir = "uploads"  # Must match mount in main.py
    os.makedirs(uploads_dir, exist_ok=True)
    final_path = os.path.join(uploads_dir, stored_filename)

    try:
        try:
            from PIL import Image
            # Open & normalize image, convert to RGB (avoid issues with GIF/P modes)
            img = Image.open(tmp_path)
            if img.format == "GIF":
                try:
                    img.seek(0)  # First frame for OCR
                except Exception:  # pragma: no cover
                    pass
            # Convert to RGB to standardize
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            
            # Save to file for serving
            img.save(final_path, optimize=True)
            
            # Generate base64 data URL for LLM vision API
            # Resize if too large (max 2048px on longest edge) to reduce token usage
            max_dimension = 2048
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to base64 data URL
            buffer = io.BytesIO()
            # Use JPEG for smaller size (unless PNG is needed for transparency)
            output_format = "PNG" if img.mode == "RGBA" else "JPEG"
            mime_type = "image/png" if output_format == "PNG" else "image/jpeg"
            img.save(buffer, format=output_format, quality=85 if output_format == "JPEG" else None)
            buffer.seek(0)
            base64_data = base64.b64encode(buffer.read()).decode("utf-8")
            data_url = f"data:{mime_type};base64,{base64_data}"
            
        except ImportError:
            raise HTTPException(status_code=500, detail="Image processing requires Pillow. Please install pillow.")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

        # Attempt OCR (optional)
        try:
            import pytesseract
            from PIL import Image as _Img
            ocr_text = pytesseract.image_to_string(_Img.open(final_path)) or ""
        except ImportError:
            # OCR optional; just skip if not installed
            ocr_text = ""
        except Exception:
            # Any OCR runtime errors should not block upload
            ocr_text = ""

        ocr_text = ocr_text.strip()

        return {
            "filename": filename,
            "stored_filename": stored_filename,
            "url": data_url,  # Base64 data URL for LLM vision API
            "file_url": f"/uploads/{stored_filename}",  # Server file URL for display
            "ocr_text": ocr_text,
            "ocr_length": len(ocr_text),
            "has_text": bool(ocr_text),
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
