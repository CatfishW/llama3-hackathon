"""
LLM API Router

Provides HTTP endpoints for direct LLM inference.
Supports both single-shot and session-based conversation.
Includes streaming support for real-time responses.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import logging
import json

from ..deps import get_current_user
from ..services.llm_client import get_llm_client, get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for chat completion"""
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    temperature: Optional[float] = Field(None, description="Sampling temperature (0.0-2.0)")
    top_p: Optional[float] = Field(None, description="Top-p sampling (0.0-1.0)")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    model: Optional[str] = Field("default", description="Model to use")


class SessionChatRequest(BaseModel):
    """Request for session-based chat"""
    session_id: str = Field(..., description="Session identifier")
    message: str = Field(..., description="User message")
    system_prompt: Optional[str] = Field(None, description="System prompt (only for new sessions)")
    temperature: Optional[float] = Field(None, description="Sampling temperature")
    top_p: Optional[float] = Field(None, description="Top-p sampling")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")


class ChatResponse(BaseModel):
    """Response from chat completion"""
    response: str = Field(..., description="Generated response")
    session_id: Optional[str] = Field(None, description="Session ID (for session-based chat)")


class SessionHistoryResponse(BaseModel):
    """Session conversation history"""
    session_id: str
    messages: List[ChatMessage]


@router.post("/chat", response_model=ChatResponse)
def chat_completion(
    request: ChatRequest,
    user = Depends(get_current_user)
):
    """
    Generate a chat completion (stateless, single-shot).
    
    This endpoint does not maintain conversation history.
    Use /chat/session for conversation management.
    """
    try:
        llm_client = get_llm_client()
        
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Generate response
        response = llm_client.generate(
            messages=messages,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            model=request.model
        )
        
        return ChatResponse(response=response)
        
    except RuntimeError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/session", response_model=ChatResponse)
def session_chat(
    request: SessionChatRequest,
    user = Depends(get_current_user)
):
    """
    Send a message in a session-based conversation.
    
    The session maintains conversation history automatically.
    Provide system_prompt only when starting a new session.
    """
    try:
        session_manager = get_session_manager()
        
        # Default system prompt if not provided
        system_prompt = request.system_prompt or "You are a helpful AI assistant."
        
        # Process message with session management
        response = session_manager.process_message(
            session_id=request.session_id,
            system_prompt=system_prompt,
            user_message=request.message,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens
        )
        
        return ChatResponse(response=response, session_id=request.session_id)
        
    except RuntimeError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/stream")
async def chat_completion_stream(
    request: ChatRequest,
    user = Depends(get_current_user)
):
    """
    Generate a streaming chat completion (stateless, single-shot).
    
    Returns Server-Sent Events (SSE) stream.
    This endpoint does not maintain conversation history.
    """
    try:
        llm_client = get_llm_client()
        
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Create a generator that formats output as SSE
        def generate():
            try:
                for chunk in llm_client.generate_stream(
                    messages=messages,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    model=request.model
                ):
                    # Format as Server-Sent Events
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                
                # Send done signal
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except RuntimeError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/session/stream")
async def session_chat_stream(
    request: SessionChatRequest,
    user = Depends(get_current_user)
):
    """
    Send a message in a session-based conversation with streaming response.
    
    Returns Server-Sent Events (SSE) stream.
    The session maintains conversation history automatically.
    """
    try:
        session_manager = get_session_manager()
        
        # Default system prompt if not provided
        system_prompt = request.system_prompt or "You are a helpful AI assistant."
        
        # Create a generator that formats output as SSE
        def generate():
            try:
                for chunk in session_manager.process_message_stream(
                    session_id=request.session_id,
                    system_prompt=system_prompt,
                    user_message=request.message,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens
                ):
                    # Format as Server-Sent Events
                    yield f"data: {json.dumps({'content': chunk, 'session_id': request.session_id})}\n\n"
                
                # Send done signal
                yield f"data: {json.dumps({'done': True, 'session_id': request.session_id})}\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except RuntimeError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/chat/session/{session_id}/history", response_model=SessionHistoryResponse)
def get_session_history(
    session_id: str,
    user = Depends(get_current_user)
):
    """
    Get the conversation history for a session.
    """
    try:
        session_manager = get_session_manager()
        history = session_manager.get_session_history(session_id)
        
        if history is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in history]
        
        return SessionHistoryResponse(session_id=session_id, messages=messages)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class SessionHistoryIn(BaseModel):
    session_id: str


@router.post("/chat/session/history", response_model=SessionHistoryResponse)
def post_session_history(
    payload: SessionHistoryIn,
    user = Depends(get_current_user)
):
    """POST variant for environments that block GET on dynamic paths."""
    try:
        session_manager = get_session_manager()
        history = session_manager.get_session_history(payload.session_id)
        if history is None:
            raise HTTPException(status_code=404, detail="Session not found")
        messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in history]
        return SessionHistoryResponse(session_id=payload.session_id, messages=messages)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session history (POST): {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/chat/session/{session_id}")
def clear_session(
    session_id: str,
    user = Depends(get_current_user)
):
    """
    Clear a session's conversation history.
    """
    try:
        session_manager = get_session_manager()
        session_manager.clear_session(session_id)
        
        return {"ok": True, "message": f"Session {session_id} cleared"}
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
def health_check():
    """
    Check if LLM service is available.
    Does not require authentication.
    """
    try:
        llm_client = get_llm_client()
        return {
            "status": "ok",
            "server_url": llm_client.server_url,
            "temperature": llm_client.default_temperature,
            "max_tokens": llm_client.default_max_tokens
        }
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="LLM service not initialized"
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
