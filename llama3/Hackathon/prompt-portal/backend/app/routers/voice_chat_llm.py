"""
Voice Chat with LLM Integration Router
Complete Flow: SST (Speech-to-Text) → LLM → TTS (Text-to-Speech)
Provides end-to-end voice conversational AI.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx
import base64
import io

from ..config import settings
from ..deps import get_current_user
from ..services.llm_client import get_llm_client_for_user
from ..utils.audio_utils import ensure_wav_format

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["voice-chat"])

# ============================================================================
# Configuration
# ============================================================================

# SST (Speech-to-Text) - Whisper.cpp via broker
SST_BROKER_URL = getattr(settings, 'SST_BROKER_URL', 'http://localhost:9082')
SST_REQUEST_TIMEOUT = getattr(settings, 'SST_REQUEST_TIMEOUT', 300.0)

# TTS (Text-to-Speech) - Kokoro via broker
TTS_BROKER_URL = getattr(settings, 'TTS_BROKER_URL', 'http://localhost:8080')
TTS_REQUEST_TIMEOUT = getattr(settings, 'TTS_REQUEST_TIMEOUT', 30.0)

# HTTP clients
_sst_client: Optional[httpx.AsyncClient] = None
_tts_client: Optional[httpx.AsyncClient] = None


# ============================================================================
# Request/Response Models
# ============================================================================

class VoiceMessageRequest(BaseModel):
    """Voice message for SST → LLM → TTS processing"""
    audio_base64: str = Field(..., description="Base64-encoded audio")
    language: str = Field("en", description="Language code")
    voice: str = Field("af_heart", description="TTS voice")
    speed: float = Field(1.0, gt=0.0, le=2.0, description="TTS speed")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt")


class VoiceMessageResponse(BaseModel):
    """Response with transcription, LLM response, and audio"""
    user_text: str = Field(..., description="Transcribed user text (SST)")
    assistant_text: str = Field(..., description="LLM generated response")
    audio_base64: str = Field(..., description="TTS synthesized audio")
    audio_duration_seconds: float = Field(..., description="Audio duration")
    audio_sample_rate: int = Field(..., description="Audio sample rate")


class VoiceHealthResponse(BaseModel):
    """Health check response"""
    status: str
    sst_healthy: bool
    tts_healthy: bool
    sst_service: str
    tts_service: str


# ============================================================================
# HTTP Client Management
# ============================================================================

async def _get_sst_client() -> httpx.AsyncClient:
    """Get or create SST async HTTP client"""
    global _sst_client
    if _sst_client is None:
        _sst_client = httpx.AsyncClient(timeout=SST_REQUEST_TIMEOUT)
    return _sst_client


async def _get_tts_client() -> httpx.AsyncClient:
    """Get or create TTS async HTTP client"""
    global _tts_client
    if _tts_client is None:
        _tts_client = httpx.AsyncClient(timeout=TTS_REQUEST_TIMEOUT)
    return _tts_client


# ============================================================================
# SST (Speech-to-Text) - Transcribe user voice
# ============================================================================

async def _transcribe_audio(audio_data: bytes, language: str = "en") -> str:
    """
    Transcribe audio to text using SST broker (Whisper.cpp)
    
    Args:
        audio_data: Raw audio bytes
        language: Language code
    
    Returns:
        Transcribed text
    """
    try:
        # Ensure audio is in WAV format (add header if needed)
        wav_audio = ensure_wav_format(audio_data, sample_rate=16000)
        
        client = await _get_sst_client()
        
        files = {
            "file": ("audio.wav", wav_audio, "audio/wav")
        }
        data = {
            "temperature": "0.0",
            "temperature_inc": "0.2",
            "response_format": "json"
        }
        
        logger.debug(f"SST: Transcribing audio ({len(audio_data)} bytes → {len(wav_audio)} bytes with header, lang={language})")
        
        response = await client.post(
            f"{SST_BROKER_URL}/inference",
            files=files,
            data=data
        )
        response.raise_for_status()
        
        result = response.json()
        logger.debug(f"SST raw response: {result}")
        
        # Try multiple response formats
        # Format 1: {"result": {"text": "..."}}
        text = result.get("result", {}).get("text", "")
        
        # Format 2: {"text": "..."}
        if not text:
            text = result.get("text", "")
        
        # Format 3: Direct text content
        if not text and isinstance(result, dict):
            # Check for other possible keys
            for key in ["transcription", "output", "content"]:
                if key in result:
                    text = result[key]
                    break
        
        logger.info(f"SST: Transcribed text = '{text}'")
        return text
        
    except httpx.ConnectError as exc:
        logger.error(f"SST Connection Error: {SST_BROKER_URL} - {exc}")
        raise HTTPException(status_code=503, detail=f"SST service unavailable") from exc
    except httpx.TimeoutException as exc:
        logger.error(f"SST Timeout: {exc}")
        raise HTTPException(status_code=504, detail="SST service timeout") from exc
    except Exception as exc:
        logger.error(f"SST Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc


# ============================================================================
# TTS (Text-to-Speech) - Synthesize LLM response
# ============================================================================

async def _synthesize_speech(
    text: str,
    voice: str = "af_heart",
    speed: float = 1.0
) -> dict:
    """
    Synthesize text to speech using TTS broker (Kokoro)
    
    Args:
        text: Text to synthesize
        voice: Voice name
        speed: Speech speed
    
    Returns:
        Dict with audio_base64, duration, sample_rate
    """
    try:
        client = await _get_tts_client()
        
        payload = {
            "text": text,
            "voice": voice,
            "lang_code": "a",
            "speed": speed
        }
        
        logger.debug(f"TTS: Synthesizing ({len(text)} chars, voice={voice})")
        
        response = await client.post(
            f"{TTS_BROKER_URL}/synthesize",
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        
        logger.info(f"TTS: Synthesized audio ({result.get('audio_duration_seconds')}s)")
        return result
        
    except httpx.ConnectError as exc:
        logger.error(f"TTS Connection Error: {TTS_BROKER_URL} - {exc}")
        raise HTTPException(status_code=503, detail=f"TTS service unavailable") from exc
    except httpx.TimeoutException as exc:
        logger.error(f"TTS Timeout: {exc}")
        raise HTTPException(status_code=504, detail="TTS service timeout") from exc
    except Exception as exc:
        logger.error(f"TTS Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {exc}") from exc


# ============================================================================
# Main Endpoint: Voice → LLM → Audio
# ============================================================================

@router.post("/message", response_model=VoiceMessageResponse)
async def voice_message(
    request: VoiceMessageRequest,
    user = Depends(get_current_user)
):
    """
    Complete voice message flow:
    1. **SST**: Transcribe user's voice to text
    2. **LLM**: Process text and generate response
    3. **TTS**: Synthesize response back to voice
    
    Args:
        request: Voice message with base64 audio
        user: Authenticated user
    
    Returns:
        VoiceMessageResponse with user_text, assistant_text, and audio
    
    Example:
        ```bash
        curl -X POST http://localhost:8000/api/voice/message \\
          -H "Authorization: Bearer <token>" \\
          -H "Content-Type: application/json" \\
          -d '{
            "audio_base64": "<base64-audio>",
            "language": "en",
            "voice": "af_heart",
            "speed": 1.0
          }'
        ```
    """
    try:
        logger.info(f"=== Voice Message Pipeline Started (User: {user.id}) ===")
        
        # ===== STEP 1: SST - Transcribe audio =====
        logger.info("STEP 1: SST - Transcribing voice to text")
        audio_bytes = base64.b64decode(request.audio_base64)
        user_text = await _transcribe_audio(audio_bytes, request.language)
        
        if not user_text.strip():
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        
        logger.info(f"✓ SST Complete: '{user_text}'")
        
        # ===== STEP 2: LLM - Get AI response =====
        logger.info("STEP 2: LLM - Processing text with language model")
        llm_client = get_llm_client_for_user(None)  # Use default model
        
        messages = [
            {
                "role": "system",
                "content": request.system_prompt or "You are a helpful assistant. Respond concisely."
            },
            {"role": "user", "content": user_text}
        ]
        
        assistant_text = llm_client.generate(messages=messages)
        logger.info(f"✓ LLM Complete: '{assistant_text[:100]}...'")
        
        # ===== STEP 3: TTS - Synthesize response =====
        logger.info("STEP 3: TTS - Synthesizing response to voice")
        audio_result = await _synthesize_speech(
            text=assistant_text,
            voice=request.voice,
            speed=request.speed
        )
        logger.info(f"✓ TTS Complete: {audio_result['audio_duration_seconds']}s audio")
        
        logger.info("=== Voice Message Pipeline Completed Successfully ===\n")
        
        return VoiceMessageResponse(
            user_text=user_text,
            assistant_text=assistant_text,
            audio_base64=audio_result["audio_base64"],
            audio_duration_seconds=audio_result["audio_duration_seconds"],
            audio_sample_rate=audio_result["audio_sample_rate"]
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Pipeline Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Voice pipeline failed: {exc}") from exc


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health", response_model=VoiceHealthResponse)
async def voice_health():
    """
    Check health of SST and TTS services.
    
    Returns:
        VoiceHealthResponse with individual service statuses
    """
    sst_healthy = False
    tts_healthy = False
    
    # Check SST
    try:
        client = await _get_sst_client()
        response = await client.get(f"{SST_BROKER_URL}/healthz")
        response.raise_for_status()
        sst_healthy = True
        logger.info("✓ SST service healthy")
    except Exception as exc:
        logger.warning(f"✗ SST service error: {exc}")
    
    # Check TTS
    try:
        client = await _get_tts_client()
        response = await client.get(f"{TTS_BROKER_URL}/healthz")
        response.raise_for_status()
        tts_healthy = True
        logger.info("✓ TTS service healthy")
    except Exception as exc:
        logger.warning(f"✗ TTS service error: {exc}")
    
    overall = "healthy" if (sst_healthy and tts_healthy) else "degraded"
    
    return VoiceHealthResponse(
        status=overall,
        sst_healthy=sst_healthy,
        tts_healthy=tts_healthy,
        sst_service=SST_BROKER_URL,
        tts_service=TTS_BROKER_URL
    )


# ============================================================================
# WebSocket: Real-time Voice Chat
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")


manager = ConnectionManager()


@router.websocket("/ws/voice")
async def websocket_voice_chat(websocket: WebSocket):
    """
    WebSocket for real-time voice chat.
    
    Protocol:
    ```json
    // User sends voice
    {
      "type": "voice_message",
      "audio_base64": "<...>",
      "language": "en",
      "voice": "af_heart",
      "speed": 1.0
    }
    
    // Server responds with all results
    {
      "type": "transcription",
      "text": "Hello"
    }
    {
      "type": "assistant",
      "text": "Hi there!"
    }
    {
      "type": "audio",
      "audio_base64": "<...>",
      "duration": 2.5
    }
    ```
    """
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            logger.debug(f"WebSocket: {msg_type}")
            
            if msg_type == "voice_message":
                try:
                    audio_b64 = data.get("audio_base64")
                    language = data.get("language", "en")
                    voice = data.get("voice", "af_heart")
                    speed = data.get("speed", 1.0)
                    system_prompt = data.get("system_prompt")
                    
                    if not audio_b64:
                        await websocket.send_json({"type": "error", "error": "Missing audio_base64"})
                        continue
                    
                    # Step 1: SST
                    audio_bytes = base64.b64decode(audio_b64)
                    user_text = await _transcribe_audio(audio_bytes, language)
                    
                    await websocket.send_json({
                        "type": "transcription",
                        "text": user_text
                    })
                    
                    # Step 2: LLM
                    llm_client = get_llm_client_for_user(None)
                    messages = [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant. Respond concisely."
                        },
                        {"role": "user", "content": user_text}
                    ]
                    assistant_text = llm_client.generate(messages=messages)
                    
                    await websocket.send_json({
                        "type": "assistant",
                        "text": assistant_text
                    })
                    
                    # Step 3: TTS
                    audio_result = await _synthesize_speech(
                        text=assistant_text,
                        voice=voice,
                        speed=speed
                    )
                    
                    await websocket.send_json({
                        "type": "audio",
                        "audio_base64": audio_result["audio_base64"],
                        "duration": audio_result["audio_duration_seconds"],
                        "sample_rate": audio_result["audio_sample_rate"]
                    })
                    
                except Exception as exc:
                    logger.error(f"Voice message error: {exc}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "error": str(exc)
                    })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Unknown type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info("Voice WebSocket disconnected")
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}", exc_info=True)
        await manager.disconnect(websocket)


# ============================================================================
# Cleanup
# ============================================================================

@router.on_event("shutdown")
async def shutdown():
    """Cleanup HTTP clients"""
    global _sst_client, _tts_client
    
    if _sst_client:
        await _sst_client.aclose()
        _sst_client = None
    
    if _tts_client:
        await _tts_client.aclose()
        _tts_client = None
    
    logger.info("Voice chat router shutdown complete")
