from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import AsyncGenerator, Optional
import json
import urllib.parse

from ..deps import get_db
from ..models import ChatSession, ChatMessage
from ..services.provider_factory import get_provider


router = APIRouter(prefix="/api/chat", tags=["chat-stream"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\n" f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/stream")
async def stream(session_id: int, message: str, db: Session = Depends(get_db)) -> StreamingResponse:
    session: Optional[ChatSession] = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def generator() -> AsyncGenerator[bytes, None]:
        yield _sse_event("ack", {"session_id": session_id}).encode("utf-8")
        provider = get_provider()
        try:
            resp = await provider.chat(
                session_key=session.session_key,
                message=message,
                system_prompt=session.system_prompt,
                temperature=session.temperature,
                top_p=session.top_p,
                max_tokens=session.max_tokens,
            )
        except Exception as exc:
            yield _sse_event("error", {"message": str(exc)}).encode("utf-8")
            return

        content = (
            (resp.get("content") if isinstance(resp, dict) else None) or ""
        )

        yield _sse_event("final", {"content": content}).encode("utf-8")

    return StreamingResponse(generator(), media_type="text/event-stream")


