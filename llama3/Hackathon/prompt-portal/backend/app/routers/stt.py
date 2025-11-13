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
        # Check if audio is already WAV format
        is_wav = audio_data[:4] == b'RIFF' and len(audio_data) >= 12 and audio_data[8:12] == b'WAVE'
        
        logger.info(f"[SST] Received audio data: {len(audio_data)} bytes")
        logger.info(f"[SST] First 4 bytes (hex): {audio_data[:4].hex()}")
        logger.info(f"[SST] Is WAV format: {is_wav}")
        
        # If not WAV, treat as raw PCM and add WAV header
        if not is_wav:
            logger.info(f"[SST] Not WAV format, treating as raw PCM and adding WAV header")
            wav_audio = ensure_wav_format(audio_data, sample_rate=16000)
            logger.info(f"[SST] Added WAV header: {len(audio_data)} bytes PCM → {len(wav_audio)} bytes WAV")
        else:
            logger.info(f"[SST] Already WAV format, using as-is")
            wav_audio = audio_data
        
        client = await _get_sst_client()
        
        files = {
            "file": ("audio.wav", wav_audio, "audio/wav")
        }
        data = {
            "temperature": "0.0",
            "temperature_inc": "0.2",
            "response_format": "json"
        }
        
        logger.info(f"[SST] Transcribing audio (lang={language}, size={len(wav_audio)} bytes)")
        logger.info(f"[SST] Sending to: {SST_BROKER_URL}/inference")
        
        response = await client.post(
            f"{SST_BROKER_URL}/inference",
            files=files,
            data=data
        )
        logger.info(f"[SST] Response status: {response.status_code}")
        response.raise_for_status()
        
        # Parse JSON response
        result = response.json()
        logger.info(f"[SST] Parsed JSON result: {result}")
        
        # Extract text from response (try multiple possible formats)
        text = result.get("text", "")
        if not text:
            text = result.get("result", {}).get("text", "")
        if not text and isinstance(result, dict):
            for key in ["transcription", "output", "content"]:
                if key in result:
                    text = result[key]
                    break
        
        logger.info(f"[SST] Extracted text: '{text}' (length: {len(text)})")
        
        # Filter out invalid Whisper.cpp artifacts
        import re
        invalid_patterns = [
            r'^\s*\[MUSIC\]\s*$',
            r'^\s*\[SOUND\]\s*$',
            r'^\s*\[MUSIC\s+PLAYING\]\s*$',
            r'^\s*\[SILENCE\]\s*$',
            r'^\s*\[BLANK[_\s]*AUDIO\]\s*$',
            r'^\s*\[\s*\]\s*$',
            r'^\s*\.+\s*$',
        ]
        
        if text and any(re.match(pattern, text, re.IGNORECASE) for pattern in invalid_patterns):
            logger.info(f"[SST] Filtered out invalid artifact: '{text}'")
            text = ""
        
        logger.info(f"[SST] Final transcribed text: '{text}' (length: {len(text)})")
        
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
        
        logger.info(f"[STT] Endpoint received file: {file.filename}")
        logger.info(f"[STT] File content-type: {file.content_type}")
        logger.info(f"[STT] Audio data size: {len(audio_data)} bytes")
        logger.info(f"[STT] Language: {language}")
        
        if not audio_data:
            logger.error(f"[STT] Empty audio file received")
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        logger.info(f"[STT] STT endpoint: Received {len(audio_data)} bytes")
        
        # Use SST broker
        result = await transcribe_with_sst_broker(audio_data, language)
        
        logger.info(f"[STT] Returning result: {result}")
        
        response = STTResponse(**result)
        logger.info(f"[STT] Final response text: '{response.text}' (length: {len(response.text)})")
        
        return response
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[STT] Transcription endpoint error: {exc}", exc_info=True)
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

