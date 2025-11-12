"""
Text-to-Speech (TTS) Router
Proxies requests to Kokoro TTS server
"""

import logging
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tts", tags=["tts"])

# ============================================================================
# Request/Response Models
# ============================================================================

class TTSSynthesisRequest(BaseModel):
    """Request model for TTS synthesis"""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to synthesize")
    voice: str = Field("af_heart", description="Voice name (e.g., 'af_heart', 'af', 'am')")
    lang_code: str = Field("a", description="Language code (e.g., 'a' for English)")
    speed: float = Field(1.0, gt=0.0, le=2.0, description="Speech speed multiplier (0.5-2.0)")


class TTSSynthesisResponse(BaseModel):
    """Response model for TTS synthesis"""
    audio_base64: str
    audio_sample_rate: int
    audio_duration_seconds: float
    voice: str
    lang_code: str
    speed: float
    text_length: int


class TTSVoicesResponse(BaseModel):
    """Response model for available voices"""
    voices: list[str]
    default_voice: str


# ============================================================================
# Configuration
# ============================================================================

# Get TTS server configuration from environment or use defaults
TTS_SERVER_URL = getattr(settings, 'TTS_SERVER_URL', 'http://localhost:8081')
TTS_REQUEST_TIMEOUT = getattr(settings, 'TTS_REQUEST_TIMEOUT', 30.0)

# Cache for HTTP client
_http_client: Optional[httpx.AsyncClient] = None


async def _get_http_client() -> httpx.AsyncClient:
    """Get or create async HTTP client"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=TTS_REQUEST_TIMEOUT)
    return _http_client


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/synthesize", response_model=TTSSynthesisResponse)
async def synthesize(request: TTSSynthesisRequest) -> TTSSynthesisResponse:
    """
    Synthesize text to speech using Kokoro TTS
    
    This endpoint forwards requests to the Kokoro TTS server and returns
    the audio as base64-encoded WAV data.
    
    Args:
        request: TTSSynthesisRequest containing text, voice, language, and speed
    
    Returns:
        TTSSynthesisResponse with base64-encoded audio and metadata
    """
    try:
        logger.info(
            f"TTS synthesis request: text_len={len(request.text)}, "
            f"voice={request.voice}, lang_code={request.lang_code}, speed={request.speed}"
        )
        
        # Prepare request payload
        payload = {
            "text": request.text,
            "voice": request.voice,
            "lang_code": request.lang_code,
            "speed": request.speed
        }
        
        # Forward to Kokoro TTS server
        client = await _get_http_client()
        response = await client.post(f"{TTS_SERVER_URL}/synthesize", json=payload)
        response.raise_for_status()
        
        # Parse and validate response
        data = response.json()
        result = TTSSynthesisResponse(**data)
        
        logger.info(
            f"TTS synthesis successful: duration={result.audio_duration_seconds}s, "
            f"size={len(result.audio_base64)}B"
        )
        
        return result
        
    except httpx.ConnectError as exc:
        logger.error(f"Failed to connect to TTS server at {TTS_SERVER_URL}: {exc}")
        raise HTTPException(
            status_code=503,
            detail=f"TTS server unavailable at {TTS_SERVER_URL}"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error(f"TTS server request timed out: {exc}")
        raise HTTPException(
            status_code=504,
            detail="TTS server request timed out"
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error(f"TTS server error: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"TTS server error: {exc.response.text}"
        ) from exc
    except ValueError as exc:
        logger.error(f"Invalid TTS response format: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"Invalid response from TTS server: {exc}"
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected error during TTS synthesis: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis error: {exc}"
        ) from exc


@router.get("/voices", response_model=TTSVoicesResponse)
async def get_available_voices() -> TTSVoicesResponse:
    """
    Get list of available TTS voices from Kokoro TTS server
    
    Returns:
        TTSVoicesResponse with list of voice names and default voice
    """
    try:
        logger.info("Fetching available TTS voices")
        
        client = await _get_http_client()
        response = await client.get(f"{TTS_SERVER_URL}/info")
        response.raise_for_status()
        
        data = response.json()
        
        # Default voices if not provided by server
        voices = data.get("voices", ["af_heart", "af", "am", "bf", "bm"])
        default_voice = data.get("default_voice", "af_heart")
        
        logger.info(f"Retrieved {len(voices)} available voices")
        
        return TTSVoicesResponse(voices=voices, default_voice=default_voice)
        
    except Exception as exc:
        logger.error(f"Failed to get TTS voices: {exc}")
        # Return default voices even if server is unreachable
        return TTSVoicesResponse(
            voices=["af_heart", "af", "am", "bf", "bm"],
            default_voice="af_heart"
        )


@router.get("/health")
async def health_check() -> dict:
    """Check health of TTS service"""
    try:
        client = await _get_http_client()
        response = await client.get(f"{TTS_SERVER_URL}/healthz")
        response.raise_for_status()
        
        return {
            "status": "healthy",
            "tts_server": TTS_SERVER_URL,
            "remote_status": response.json().get("status", "unknown")
        }
    except Exception as exc:
        logger.warning(f"TTS server health check failed: {exc}")
        return {
            "status": "degraded",
            "tts_server": TTS_SERVER_URL,
            "error": str(exc)
        }


@router.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
