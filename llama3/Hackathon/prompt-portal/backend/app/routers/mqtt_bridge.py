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
    publish_state(state)
    return {"ok": True}

@router.get("/last_hint")
def get_last_hint(session_id: str = Query(..., min_length=1)):
    return {"session_id": session_id, "last_hint": LAST_HINTS.get(session_id)}

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
    """Publish the selected or custom template to LAM over MQTT.
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

    publish_template(body, session_id=session_id)
    return {"ok": True}
