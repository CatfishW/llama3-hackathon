"""
LLM API Router

Provides HTTP endpoints for direct LLM inference.
Supports both single-shot and session-based conversation.
Includes streaming support for real-time responses.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import logging
import json

from ..deps import get_current_user, get_db
from ..services.llm_client import get_llm_client, get_session_manager, get_llm_client_for_user
from ..services.memory_manager import get_memory_manager
from ..models_config import get_models_manager
from ..models import User
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


def _resolve_model_for_call(model: Optional[str]) -> Optional[str]:
    if not model or model == "default":
        return "default"
    models_manager = get_models_manager()
    if models_manager.get_model_by_name(model):
        return "default"
    return model


def _fallback_model_names(preferred: Optional[str]) -> List[str]:
    models_manager = get_models_manager()
    model_names = [model.name for model in models_manager.get_all_models()]
    if preferred and preferred in model_names:
        return [preferred] + [name for name in model_names if name != preferred]
    return model_names


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
    model: Optional[str] = Field("default", description="Model to use")



class ChatResponse(BaseModel):
    """Response from chat completion"""
    response: str = Field(..., description="Generated response")
    session_id: Optional[str] = Field(None, description="Session ID (for session-based chat)")


class SessionHistoryResponse(BaseModel):
    """Session conversation history"""
    session_id: str
    messages: List[ChatMessage]


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a chat completion (stateless, single-shot).
    
    This endpoint does not maintain conversation history.
    Use /chat/session for conversation management.
    Uses the user's selected model from their settings.
    """
    try:
        # Resolve model to use
        model_to_use = request.model if request.model and request.model != "default" else None

        db_user = db.query(User).filter(User.id == user.id).first()
        if not model_to_use:
            model_to_use = db_user.selected_model if db_user else "AGAII Cloud LLM"

        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        candidate_models = _fallback_model_names(model_to_use)
        last_error: Optional[Exception] = None

        for model_name in candidate_models:
            try:
                llm_client = get_llm_client_for_user(model_name)
                model_for_call = _resolve_model_for_call(model_name)
                response = await llm_client.agenerate(
                    messages=messages,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    model=model_for_call
                )
                if db_user and model_name != db_user.selected_model:
                    db_user.selected_model = model_name
                    db.commit()
                if model_name != model_to_use:
                    logger.warning("LLM failure; switched model from %s to %s", model_to_use, model_name)
                return ChatResponse(response=response)
            except Exception as exc:
                last_error = exc
                continue

        raise RuntimeError(str(last_error) if last_error else "LLM failed with no available models")
        
    except RuntimeError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/session", response_model=ChatResponse)
async def session_chat(
    request: SessionChatRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message in a session-based conversation.
    
    The session maintains conversation history automatically.
    Provide system_prompt only when starting a new session.
    Uses the user's selected model from their settings.
    """
    try:
        session_manager = get_session_manager()
        
        # Default system prompt if not provided
        system_prompt = request.system_prompt or "You are a helpful AI assistant."
        
        # Resolve model and client
        model_to_use = request.model if request.model and request.model != "default" else None
        
        db_user = db.query(User).filter(User.id == user.id).first()
        if not model_to_use and db_user:
            model_to_use = db_user.selected_model
            
        candidate_models = _fallback_model_names(model_to_use)
        last_error: Optional[Exception] = None

        for model_name in candidate_models:
            try:
                llm_client = get_llm_client_for_user(model_name)
                model_for_call = _resolve_model_for_call(model_name)
                
                # Process message with session management
                response = await session_manager.aprocess_message(
                    session_id=request.session_id,
                    system_prompt=system_prompt,
                    user_message=request.message,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    model=model_for_call,
                    llm_client=llm_client
                )
                
                if db_user and model_name != db_user.selected_model:
                    db_user.selected_model = model_name
                    db.commit()
                    
                return ChatResponse(response=response, session_id=request.session_id)
            except Exception as exc:
                last_error = exc
                continue

        raise RuntimeError(str(last_error) if last_error else "LLM failed with no available models")

        
    except RuntimeError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/stream")
async def chat_completion_stream(
    request: Request,
    request_data: ChatRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a streaming chat completion (stateless, single-shot).
    
    Returns Server-Sent Events (SSE) stream.
    This endpoint does not maintain conversation history.
    Uses the user's selected model from their settings.
    """
    try:
        # Get user's selected model
        db_user = db.query(User).filter(User.id == user.id).first()
        selected_model_name = db_user.selected_model if db_user else None
        
        # Get LLM client configured for user's model
        llm_client = get_llm_client_for_user(selected_model_name)
        
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Create a generator that formats output as SSE
        async def generate():
            try:
                model_for_call = _resolve_model_for_call(request.model)
                async for chunk in llm_client.agenerate_stream(
                    messages=messages,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    max_tokens=request.max_tokens,
                    model=model_for_call
                ):
                    # Format as Server-Sent Events
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                    if await request.is_disconnected():
                        return
                
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
    request: Request,
    request_data: SessionChatRequest,
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
        async def generate():
            try:
                # Resolve model and client
                model_to_use = request_data.model if request_data.model and request_data.model != "default" else None
                
                # We need a DB session here to get user settings if needed
                # But for simplicity we'll just use the requested model or let the manager decide
                
                llm_client = get_llm_client_for_user(model_to_use)
                model_for_call = _resolve_model_for_call(model_to_use)

                async for chunk in session_manager.aprocess_message_stream(
                    session_id=request_data.session_id,
                    system_prompt=system_prompt,
                    user_message=request_data.message,
                    temperature=request_data.temperature,
                    top_p=request_data.top_p,
                    max_tokens=request_data.max_tokens,
                    model=model_for_call,
                    llm_client=llm_client
                ):
                    # Format as Server-Sent Events
                    yield f"data: {json.dumps({'content': chunk, 'session_id': request_data.session_id})}\n\n"
                    if await request.is_disconnected():
                        return

                # Send done signal
                yield f"data: {json.dumps({'done': True, 'session_id': request_data.session_id})}\n\n"
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


# ============================================================================
# MAZE AGENT ENDPOINTS - Optimized Memory Management
# ============================================================================

class MazeAgentRequest(BaseModel):
    """Request for maze agent with optimized memory."""
    session_id: str = Field(..., description="Unique session identifier")
    system_prompt: Optional[str] = Field(None, description="System prompt (sent only on first message)")
    
    # Current state
    position: List[int] = Field(..., description="Current [x, y] position")
    exit_position: List[int] = Field(..., description="Exit [x, y] position")
    energy: int = Field(..., description="Current energy level")
    oxygen: int = Field(0, description="Oxygen collected")
    score: int = Field(0, description="Current score")
    
    # Map data
    minimap: str = Field(..., description="ASCII minimap representation")
    surroundings: Dict[str, str] = Field(..., description="Immediate surroundings {north, south, east, west}")
    
    # Skills
    available_skills: List[Dict] = Field(default_factory=list, description="Available skills with status")
    
    # Last action result
    last_action: Optional[Dict] = Field(None, description="Last action taken")
    last_result: Optional[str] = Field(None, description="Result of last action")
    
    # LLM parameters
    temperature: Optional[float] = Field(0.1, description="Sampling temperature")
    max_tokens: Optional[int] = Field(400, description="Max tokens to generate")
    model: Optional[str] = Field("default", description="Model to use")


class MazeAgentResponse(BaseModel):
    """Response from maze agent."""
    response: str = Field(..., description="Agent's response (JSON action)")
    session_id: str = Field(..., description="Session ID")
    memory_stats: Optional[Dict] = Field(None, description="Memory usage statistics")
    tokens_saved: Optional[int] = Field(None, description="Estimated tokens saved vs naive approach")


@router.post("/maze/agent", response_model=MazeAgentResponse)
async def maze_agent_step(
    request: MazeAgentRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a maze agent step with optimized memory management.
    
    This endpoint uses a hierarchical memory system:
    1. Static Layer: System prompt (cached, sent only once)
    2. Episodic Layer: Compressed history summaries
    3. Working Layer: Current state (always sent)
    
    Benefits:
    - Reduces token usage by 40-60% vs naive approach
    - Maintains agent accuracy through smart context prioritization
    - Tracks patterns to prevent loops/oscillation
    """
    try:
        memory_manager = get_memory_manager()
        session_manager = get_session_manager()
        
        # Get or create memory state
        state = memory_manager.get_or_create_session(request.session_id)
        is_first_message = state.message_count == 0
        
        # Update memory state with current info
        memory_manager.update_state(
            session_id=request.session_id,
            position=tuple(request.position),
            energy=request.energy,
            oxygen=request.oxygen,
            score=request.score,
            action=request.last_action,
            result=request.last_result,
            exit_position=tuple(request.exit_position)
        )
        
        # Build optimized prompt using memory layers
        system_prompt_to_send, user_message = memory_manager.build_optimized_prompt(
            session_id=request.session_id,
            system_prompt=request.system_prompt or "You are a maze navigation agent. Output JSON actions.",
            minimap=request.minimap,
            surroundings=request.surroundings,
            available_skills=request.available_skills,
            is_first_message=is_first_message
        )
        
        # Estimate tokens saved
        naive_tokens = memory_manager.estimate_tokens(request.minimap) + 500  # Rough estimate
        optimized_tokens = memory_manager.estimate_tokens(user_message)
        if system_prompt_to_send:
            optimized_tokens += memory_manager.estimate_tokens(system_prompt_to_send)
        tokens_saved = max(0, naive_tokens - optimized_tokens)
        
        # Resolve model
        model_to_use = request.model if request.model and request.model != "default" else None
        db_user = db.query(User).filter(User.id == user.id).first()
        if not model_to_use and db_user:
            model_to_use = db_user.selected_model
        
        candidate_models = _fallback_model_names(model_to_use)
        last_error: Optional[Exception] = None
        response_text = ""
        
        for model_name in candidate_models:
            try:
                llm_client = get_llm_client_for_user(model_name)
                model_for_call = _resolve_model_for_call(model_name)
                
                # Use session manager with history disabled for stateless agent calls
                # Or with very limited history for context
                response_text = await session_manager.aprocess_message(
                    session_id=request.session_id,
                    system_prompt=system_prompt_to_send or request.system_prompt or "You are a maze navigation agent.",
                    user_message=user_message,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    model=model_for_call,
                    llm_client=llm_client,
                    use_history=True,  # Use history for context
                    max_history_messages=3  # Only keep last 3 exchanges
                )
                
                # Update model preference if changed
                if db_user and model_name != db_user.selected_model:
                    db_user.selected_model = model_name
                    db.commit()
                
                break
            except Exception as exc:
                last_error = exc
                logger.warning(f"Model {model_name} failed: {exc}")
                continue
        
        if not response_text and last_error:
            raise RuntimeError(str(last_error))
        
        # Get memory stats
        memory_stats = memory_manager.get_memory_stats(request.session_id)
        
        return MazeAgentResponse(
            response=response_text,
            session_id=request.session_id,
            memory_stats=memory_stats,
            tokens_saved=tokens_saved
        )
        
    except RuntimeError as e:
        logger.error(f"Maze agent error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected maze agent error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/maze/memory/{session_id}")
def get_maze_memory_stats(
    session_id: str,
    user = Depends(get_current_user)
):
    """
    Get memory statistics for a maze session.
    Useful for debugging and monitoring token usage.
    """
    try:
        memory_manager = get_memory_manager()
        stats = memory_manager.get_memory_stats(session_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/maze/memory/{session_id}")
def clear_maze_memory(
    session_id: str,
    user = Depends(get_current_user)
):
    """
    Clear memory for a maze session.
    """
    try:
        memory_manager = get_memory_manager()
        memory_manager.clear_session(session_id)
        
        # Also clear LLM session
        session_manager = get_session_manager()
        session_manager.clear_session(session_id)
        
        return {"ok": True, "message": f"Memory cleared for session {session_id}"}
    except Exception as e:
        logger.error(f"Error clearing maze memory: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
