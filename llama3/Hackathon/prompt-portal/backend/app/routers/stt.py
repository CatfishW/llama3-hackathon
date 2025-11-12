"""
Speech-to-Text Router
Supports multiple backends: AssemblyAI, OpenAI Whisper, or local speech recognition
"""

import os
import io
import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel

router = APIRouter(prefix="/api/stt", tags=["speech-to-text"])

# Get configuration from environment
STT_BACKEND = os.getenv("STT_BACKEND", "openai").lower()  # openai, assemblyai, or google
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
GOOGLE_CLOUD_CREDENTIALS = os.getenv("GOOGLE_CLOUD_CREDENTIALS", "")


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


async def transcribe_with_openai(audio_data: bytes, language: str = "en") -> dict:
    """Transcribe audio using OpenAI Whisper API"""
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        )
    
    try:
        async with httpx.AsyncClient() as client:
            files = {
                "file": ("audio.wav", audio_data, "audio/wav"),
                "model": (None, "whisper-1"),
                "language": (None, language),
            }
            
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files=files,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenAI API error: {response.text}"
                )
            
            result = response.json()
            return {
                "text": result.get("text", ""),
                "confidence": None,  # OpenAI doesn't return confidence
                "language": language,
                "backend": "openai"
            }
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenAI API timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


async def transcribe_with_assemblyai(audio_data: bytes, language: str = "en") -> dict:
    """Transcribe audio using AssemblyAI API"""
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="AssemblyAI API key not configured. Set ASSEMBLYAI_API_KEY environment variable."
        )
    
    try:
        async with httpx.AsyncClient() as client:
            # Upload audio
            upload_response = await client.post(
                "https://api.assemblyai.com/v2/upload",
                content=audio_data,
                headers={"Authorization": ASSEMBLYAI_API_KEY},
                timeout=30.0
            )
            
            if upload_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to upload audio to AssemblyAI")
            
            upload_url = upload_response.json()["upload_url"]
            
            # Request transcription
            transcript_response = await client.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={"Authorization": ASSEMBLYAI_API_KEY},
                json={
                    "audio_url": upload_url,
                    "language_code": language
                },
                timeout=30.0
            )
            
            if transcript_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to request transcription")
            
            transcript_id = transcript_response.json()["id"]
            
            # Poll for completion
            for _ in range(120):  # 2 minute timeout
                status_response = await client.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers={"Authorization": ASSEMBLYAI_API_KEY},
                    timeout=10.0
                )
                
                status_data = status_response.json()
                if status_data["status"] == "completed":
                    return {
                        "text": status_data.get("text", ""),
                        "confidence": status_data.get("confidence", 0),
                        "language": language,
                        "backend": "assemblyai"
                    }
                elif status_data["status"] == "error":
                    raise HTTPException(status_code=500, detail="AssemblyAI transcription failed")
                
                # Wait before polling again
                await asyncio.sleep(1)
            
            raise HTTPException(status_code=504, detail="AssemblyAI transcription timeout")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AssemblyAI API timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@router.post("/transcribe", response_model=STTResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Query("en", description="Language code (e.g., 'en', 'es', 'fr')")
) -> STTResponse:
    """
    Transcribe audio file to text
    
    - **file**: Audio file (WAV, MP3, M4A, FLAC, etc.)
    - **language**: Language code for transcription
    
    Returns transcribed text
    """
    try:
        # Read audio file
        audio_data = await file.read()
        
        if not audio_data:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Use configured backend
        if STT_BACKEND == "openai":
            result = await transcribe_with_openai(audio_data, language)
        elif STT_BACKEND == "assemblyai":
            result = await transcribe_with_assemblyai(audio_data, language)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown STT backend: {STT_BACKEND}"
            )
        
        return STTResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.get("/health", response_model=STTHealthResponse)
async def health_check() -> STTHealthResponse:
    """Check STT service health and configuration"""
    configured = False
    
    if STT_BACKEND == "openai":
        configured = bool(OPENAI_API_KEY)
    elif STT_BACKEND == "assemblyai":
        configured = bool(ASSEMBLYAI_API_KEY)
    
    return STTHealthResponse(
        status="healthy" if configured else "unconfigured",
        backend=STT_BACKEND,
        configured=configured
    )


@router.get("/backends")
async def list_backends() -> dict:
    """List available STT backends and their configuration status"""
    return {
        "backends": {
            "openai": {
                "configured": bool(OPENAI_API_KEY),
                "description": "OpenAI Whisper API (cloud-based, very reliable)"
            },
            "assemblyai": {
                "configured": bool(ASSEMBLYAI_API_KEY),
                "description": "AssemblyAI API (cloud-based, fast)"
            }
        },
        "current": STT_BACKEND,
        "note": "Configure backends via environment variables: OPENAI_API_KEY, ASSEMBLYAI_API_KEY, STT_BACKEND"
    }
