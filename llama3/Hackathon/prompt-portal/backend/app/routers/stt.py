"""
Speech-to-Text Router
Uses local SST broker (Whisper.cpp) at http://173.61.35.162:25567
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
import httpx
from ..utils.audio_utils import ensure_wav_format

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stt", tags=["speech-to-text"])

# SST Broker Configuration
SST_BROKER_URL = os.getenv("SST_BROKER_URL", "http://localhost:8082")
SST_REQUEST_TIMEOUT = float(os.getenv("SST_REQUEST_TIMEOUT", "300.0"))

# HTTP client
_sst_client: Optional[httpx.AsyncClient] = None


class STTResponse(BaseModel):
    """Response model for STT endpoints"""
    text: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    backend: str


class STTHealthResponse(BaseModel):
    """Health check response"""
    status: str
    backend: str
    configured: bool
    url: str


async def _get_sst_client() -> httpx.AsyncClient:
    """Get or create SST async HTTP client"""
    global _sst_client
    if _sst_client is None:
        _sst_client = httpx.AsyncClient(timeout=SST_REQUEST_TIMEOUT)
    return _sst_client


async def transcribe_with_sst_broker(audio_data: bytes, language: str = "en") -> dict:
    """Transcribe audio using SST broker (Whisper.cpp)"""
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
        
        logger.info(f"SST: Transcribing audio ({len(audio_data)} bytes → {len(wav_audio)} bytes with header, lang={language})")
        
        response = await client.post(
            f"{SST_BROKER_URL}/inference",
            files=files,
            data=data
        )
        response.raise_for_status()
        
        result = response.json()
        text = result.get("result", {}).get("text", "")
        
        logger.info(f"SST: Transcribed = '{text}'")
        
        return {
            "text": text,
            "confidence": None,
            "language": language,
            "backend": "whisper.cpp"
        }
        
    except httpx.ConnectError as exc:
        logger.error(f"SST Connection Error: {SST_BROKER_URL} - {exc}")
        raise HTTPException(
            status_code=503,
            detail=f"SST service unavailable at {SST_BROKER_URL}"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error(f"SST Timeout: {exc}")
        raise HTTPException(status_code=504, detail="SST service timeout") from exc
    except httpx.HTTPStatusError as exc:
        logger.error(f"SST Error: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"SST service error: {exc.response.text}"
        ) from exc
    except Exception as exc:
        logger.error(f"SST Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc


@router.post("/transcribe", response_model=STTResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Query("en", description="Language code (e.g., 'en', 'es', 'fr')")
) -> STTResponse:
    """
    Transcribe audio file to text using SST broker (Whisper.cpp)
    
    Args:
        file: Audio file (WAV, MP3, FLAC, etc.)
        language: Language code for transcription
    
    Returns:
        STTResponse with transcribed text
    """
    try:
        # Read audio file
        audio_data = await file.read()
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        logger.info(f"STT endpoint: Received {len(audio_data)} bytes")
        
        # Use SST broker
        result = await transcribe_with_sst_broker(audio_data, language)
        
        return STTResponse(**result)
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Transcription endpoint error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc


@router.get("/health", response_model=STTHealthResponse)
async def health_check() -> STTHealthResponse:
    """Check SST service health"""
    try:
        client = await _get_sst_client()
        response = await client.get(f"{SST_BROKER_URL}/healthz")
        response.raise_for_status()
        
        logger.info("✓ SST service is healthy")
        
        return STTHealthResponse(
            status="healthy",
            backend="whisper.cpp",
            configured=True,
            url=SST_BROKER_URL
        )
    except Exception as exc:
        logger.warning(f"✗ SST service health check failed: {exc}")
        return STTHealthResponse(
            status="unhealthy",
            backend="whisper.cpp",
            configured=False,
            url=SST_BROKER_URL
        )


@router.get("/backends")
async def list_backends() -> dict:
    """List available STT backends and their configuration status"""
    return {
        "backends": {
            "whisper.cpp": {
                "configured": True,
                "description": "Whisper.cpp STT Broker (local, fast, open-source)",
                "url": SST_BROKER_URL
            }
        },
        "current": "whisper.cpp",
        "note": f"Using SST broker at {SST_BROKER_URL}"
    }


@router.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global _sst_client
    if _sst_client:
        await _sst_client.aclose()
        _sst_client = None
    logger.info("STT router shutdown complete")

