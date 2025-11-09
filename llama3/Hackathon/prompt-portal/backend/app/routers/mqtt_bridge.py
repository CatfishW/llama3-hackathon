from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..deps import get_current_user
from .. import models, schemas
from ..mqtt import publish_state, LAST_HINTS, SUBSCRIBERS, publish_template
from ..config import settings

router = APIRouter(prefix="/api/mqtt", tags=["mqtt"])

@router.post("/publish_state")
def publish_state_endpoint(payload: schemas.PublishStateIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Fetch the template content to embed into state, so LAM can use it.
    t = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == payload.template_id, models.PromptTemplate.user_id == user.id).first()
    if not t:
        raise HTTPException(404, "Template not found or not owned by you")
    state = dict(payload.state or {})
    state.update({
        "sessionId": payload.session_id,
        "prompt_template": {
            "title": t.title,
            "content": t.content,
            "version": t.version,
            "user_id": user.id,
        }
    })
    
    if settings.LLM_COMM_MODE.lower() == "sse":
        # In SSE mode, we just acknowledge receipt
        # The actual hint generation happens in /request_hint
        return {"ok": True, "mode": "sse", "message": "State received, use /request_hint to get hints"}
    else:
        # MQTT mode: Publish to MQTT broker
        publish_state(state)
        return {"ok": True, "mode": "mqtt"}

@router.get("/last_hint")
def get_last_hint(session_id: str = Query(..., min_length=1)):
    """Get the last hint for a session (polling method - no WebSocket needed)"""
    hint = LAST_HINTS.get(session_id)
    return {
        "session_id": session_id, 
        "last_hint": hint,
        "has_hint": hint is not None,
        "timestamp": hint.get("timestamp") if hint and isinstance(hint, dict) else None
    }

@router.post("/request_hint")
async def request_hint_endpoint(
    payload: dict,
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    """Request a hint for the maze game - works in both MQTT and SSE modes"""
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id is required")
    
    # Optional: verify template ownership if template_id provided
    template_id = payload.get("template_id")
    template = None
    if template_id:
        template = db.query(models.PromptTemplate).filter(
            models.PromptTemplate.id == template_id, 
            models.PromptTemplate.user_id == user.id
        ).first()
        if not template:
            raise HTTPException(404, "Template not found or not owned by you")
    
    state = payload.get("state", {})
    state["sessionId"] = session_id
    
    # Add template info if provided
    if template:
        state["prompt_template"] = {
            "title": template.title,
            "content": template.content,
            "version": template.version,
            "user_id": user.id,
        }
    
    # Handle based on communication mode
    if settings.LLM_COMM_MODE.lower() == "sse":
        # SSE mode: Generate hint directly and store it
        try:
            from ..services.llm_service import get_llm_service
            import json
            
            llm_service = get_llm_service()
            
            # Build system prompt from template or default
            system_prompt = template.content if template else (
                "You are a Large Action Model (LAM) guiding players through a maze game.\n"
                "You provide strategic hints and pathfinding advice. Be concise and helpful.\n"
                'Always respond in JSON format with keys: "hint" (string), "suggestion" (string).'
            )
            
            # Build user message from game state
            user_message = f"Game state: {json.dumps(state)}\nProvide a helpful hint."
            
            # Generate hint with function calling enabled for maze actions
            hint_response = llm_service.process_message(
                session_id=session_id,
                system_prompt=system_prompt,
                user_message=user_message,
                use_tools=True  # Enable maze game function calling
            )
            
            # Store the hint so it can be retrieved via /last_hint
            import time
            LAST_HINTS[session_id] = {
                "hint": hint_response,
                "timestamp": time.time()
            }
            
            # Also broadcast to WebSocket subscribers if any
            if session_id in SUBSCRIBERS:
                import asyncio
                disconnected = set()
                for ws in SUBSCRIBERS[session_id]:
                    try:
                        await ws.send_json({"hint": hint_response, "session_id": session_id})
                    except Exception:
                        disconnected.add(ws)
                SUBSCRIBERS[session_id] -= disconnected
            
            return {"ok": True, "session_id": session_id, "hint": hint_response, "mode": "sse"}
            
        except Exception as e:
            raise HTTPException(500, f"Failed to generate hint: {str(e)}")
    else:
        # MQTT mode: Publish state and hint will arrive via MQTT
        publish_state(state)
        return {"ok": True, "session_id": session_id, "message": "Hint request published", "mode": "mqtt"}

# WebSocket to stream hints in real time
async def _subscribe_ws(session_id: str, websocket: WebSocket):
    print(f"[WebSocket] New connection for session '{session_id}'")
    await websocket.accept()
    SUBSCRIBERS.setdefault(session_id, set()).add(websocket)
    print(f"[WebSocket] Total subscribers for session '{session_id}': {len(SUBSCRIBERS[session_id])}")
    
    try:
        while True:
            # Keep connection alive: client may send ping or text; we just read and ignore
            message = await websocket.receive_text()
            print(f"[WebSocket] Received keep-alive from session '{session_id}': {message[:50]}...")
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected from session '{session_id}'")
    except Exception as e:
        print(f"[WebSocket] Error in session '{session_id}': {e}")
    finally:
        SUBSCRIBERS.get(session_id, set()).discard(websocket)
        print(f"[WebSocket] Cleaned up connection for session '{session_id}'")

@router.websocket("/ws/hints/{session_id}")
async def hints_ws(websocket: WebSocket, session_id: str):
    await _subscribe_ws(session_id, websocket)

@router.post("/publish_template")
def publish_template_endpoint(
    payload: dict,
    session_id: str | None = Query(default=None, description="Optional session to target"),
    reset: bool = Query(default=True, description="Reset dialog for the target(s)"),
    db: Session = Depends(get_db), user=Depends(get_current_user)
):
    """Publish the selected or custom template - works in both MQTT and SSE modes.
    If session_id is provided, it overrides globally for that session; otherwise updates global template.
    """
    # payload may contain either a raw template string or a template_id to load from DB
    body: dict
    if isinstance(payload, dict) and (tid := payload.get("template_id")):
        t = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == tid, models.PromptTemplate.user_id == user.id).first()
        if not t:
            raise HTTPException(404, "Template not found or not owned by you")
        body = {
            "template": t.content,
            "title": t.title,
            "version": t.version,
            "user_id": user.id,
            "reset": bool(payload.get("reset", reset)),
            "max_breaks": payload.get("max_breaks")
        }
    else:
        # expect raw template content in 'template'
        tpl = payload.get("template") or payload.get("system_prompt")
        if not tpl:
            raise HTTPException(422, "Missing template content")
        body = {
            "template": tpl,
            "title": payload.get("title", "Custom Template"),
            "version": payload.get("version"),
            "user_id": user.id,
            "reset": bool(payload.get("reset", reset)),
            "max_breaks": payload.get("max_breaks")
        }

    if settings.LLM_COMM_MODE.lower() == "sse":
        # In SSE mode, templates are applied per-request in /request_hint
        # We can store it in a cache or just acknowledge
        return {"ok": True, "mode": "sse", "message": "Template will be used in subsequent hint requests"}
    else:
        # MQTT mode: Publish to MQTT broker
        publish_template(body, session_id=session_id)
        return {"ok": True, "mode": "mqtt"}
