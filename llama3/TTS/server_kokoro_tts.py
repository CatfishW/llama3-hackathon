"""
Production Kokoro TTS Server
Combines KPipeline from example.py with production-grade FastAPI server structure.
Handles text-to-speech synthesis with support for multiple voices and languages.
"""

import base64
import logging
import os
import sys
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from kokoro import KPipeline
except ImportError:
    print("Warning: kokoro library not found. Install it with: pip install kokoro")
    KPipeline = None  # type: ignore

# Configuration
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_LANG_CODE = "a"  # English
DEFAULT_VOICE = "af_heart"
AUDIO_SAMPLE_RATE = 24000
TEXT_LENGTH_LIMIT = 10000
MAX_TOKENS = 2048

# Logging setup
LOG_LEVEL_NAME = os.getenv("TTS_SERVER_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_NAME, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kokoro_tts_server")
logger.setLevel(getattr(logging, LOG_LEVEL_NAME, logging.INFO))

# FastAPI app
app = FastAPI(
    title="Kokoro TTS Server",
    description="Production TTS server using Kokoro model",
    version="1.0.0"
)

# Global pipeline cache
_pipeline_cache: Dict[str, object] = {}
_pipeline_lock = Lock()
_available_voices: Optional[List[str]] = None
_available_langs: Optional[List[str]] = None


class SynthesisRequest(BaseModel):
    """Request model for text-to-speech synthesis"""
    model_config = {"protected_namespaces": ()}
    
    text: str = Field(
        ...,
        min_length=1,
        max_length=TEXT_LENGTH_LIMIT,
        description="Text to synthesize"
    )
    voice: str = Field(
        DEFAULT_VOICE,
        description="Voice name (e.g., 'af_heart', 'af', 'am')"
    )
    lang_code: str = Field(
        DEFAULT_LANG_CODE,
        description="Language code (e.g., 'a' for English)"
    )
    speed: float = Field(
        1.0,
        gt=0.0,
        le=2.0,
        description="Speech speed multiplier (0.5-2.0)"
    )


class SynthesisResponse(BaseModel):
    """Response model for synthesis results"""
    audio_base64: str
    audio_sample_rate: int
    audio_duration_seconds: float
    voice: str
    lang_code: str
    speed: float
    text_length: int


def _get_pipeline(lang_code: str) -> object:
    """
    Get or create a KPipeline instance for the specified language.
    Uses caching to avoid reloading the model unnecessarily.
    """
    if KPipeline is None:
        raise HTTPException(
            status_code=500,
            detail="Kokoro library not available. Install with: pip install kokoro"
        )
    
    with _pipeline_lock:
        if lang_code not in _pipeline_cache:
            try:
                logger.info(f"Initializing KPipeline for language code '{lang_code}'")
                pipeline = KPipeline(lang_code=lang_code)
                _pipeline_cache[lang_code] = pipeline
                logger.info(f"KPipeline initialized successfully for '{lang_code}'")
            except Exception as exc:
                logger.error(f"Failed to initialize KPipeline for '{lang_code}': {exc}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initialize TTS pipeline: {exc}"
                ) from exc
        else:
            logger.debug(f"Reusing cached pipeline for language code '{lang_code}'")
        
        return _pipeline_cache[lang_code]


def _synthesize_audio(
    text: str,
    voice: str,
    lang_code: str,
    speed: float
) -> Tuple[np.ndarray, float]:
    """
    Synthesize audio using KPipeline.
    Returns (audio_array, duration_seconds)
    """
    try:
        pipeline = _get_pipeline(lang_code)
        
        logger.info(
            f"Synthesizing text (len={len(text)}) with voice='{voice}', "
            f"lang_code='{lang_code}', speed={speed}"
        )
        
        # Use the generator to get audio
        audio_chunks = []
        generator = pipeline(text, voice=voice)
        
        chunk_count = 0
        for gs, ps, audio in generator:
            logger.debug(f"Generated chunk {chunk_count}: graph_source_pos={gs}, pipeline_source_pos={ps}, audio_shape={audio.shape}")
            audio_chunks.append(audio)
            chunk_count += 1
        
        if not audio_chunks:
            raise HTTPException(
                status_code=500,
                detail="No audio generated from synthesis"
            )
        
        # Concatenate all audio chunks
        audio = np.concatenate(audio_chunks, axis=0)
        
        # Apply speed adjustment if needed
        if speed != 1.0:
            # Speed adjustment by resampling
            original_length = len(audio)
            new_length = int(original_length / speed)
            audio = np.interp(
                np.linspace(0, original_length - 1, new_length),
                np.arange(original_length),
                audio
            )
        
        duration = len(audio) / AUDIO_SAMPLE_RATE
        logger.info(f"Synthesis completed. Audio duration: {duration:.2f}s")
        
        return audio, duration
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Synthesis failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Synthesis failed: {exc}"
        ) from exc


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Kokoro TTS Server starting up...")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Kokoro TTS Server shutting down...")
    # Clear CUDA cache if available
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Shutdown complete")


@app.get("/healthz")
def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    try:
        # Try to get cached pipeline without initializing
        has_pipeline = len(_pipeline_cache) > 0
        return {
            "status": "ok",
            "service": "kokoro_tts",
            "version": "1.0.0",
            "has_cached_pipeline": str(has_pipeline),
            "cuda_available": str(torch.cuda.is_available())
        }
    except Exception as exc:
        logger.error(f"Health check failed: {exc}", exc_info=True)
        return {
            "status": "error",
            "service": "kokoro_tts",
            "error": str(exc)
        }


@app.get("/info")
def server_info() -> Dict[str, object]:
    """Get server information and defaults"""
    return {
        "service_name": "Kokoro TTS Server",
        "version": "1.0.0",
        "default_lang_code": DEFAULT_LANG_CODE,
        "default_voice": DEFAULT_VOICE,
        "audio_sample_rate": AUDIO_SAMPLE_RATE,
        "text_length_limit": TEXT_LENGTH_LIMIT,
        "max_tokens": MAX_TOKENS,
        "cuda_available": torch.cuda.is_available(),
        "torch_version": torch.__version__
    }


@app.post("/synthesize")
def synthesize(request: SynthesisRequest) -> SynthesisResponse:
    """
    Synthesize text to speech using Kokoro TTS model.
    
    Args:
        request: SynthesisRequest containing text, voice, language, and speed
    
    Returns:
        SynthesisResponse with base64-encoded audio and metadata
    """
    try:
        logger.info(
            f"Synthesis request: text_len={len(request.text)}, "
            f"voice={request.voice}, lang_code={request.lang_code}, speed={request.speed}"
        )
        
        # Validate input
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if len(request.text) > TEXT_LENGTH_LIMIT:
            raise HTTPException(
                status_code=400,
                detail=f"Text exceeds maximum length of {TEXT_LENGTH_LIMIT} characters"
            )
        
        # Synthesize audio
        audio, duration = _synthesize_audio(
            text=request.text,
            voice=request.voice,
            lang_code=request.lang_code,
            speed=request.speed
        )
        
        # Normalize audio to [-1, 1] range if needed
        audio_max = np.max(np.abs(audio))
        if audio_max > 1.0:
            logger.debug(f"Normalizing audio (max value: {audio_max})")
            audio = audio / (audio_max * 1.05)  # Small headroom
        
        # Encode to base64
        audio_bytes = base64.b64encode(audio.astype(np.float32).tobytes()).decode("utf-8")
        
        return SynthesisResponse(
            audio_base64=audio_bytes,
            audio_sample_rate=AUDIO_SAMPLE_RATE,
            audio_duration_seconds=duration,
            voice=request.voice,
            lang_code=request.lang_code,
            speed=request.speed,
            text_length=len(request.text)
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in synthesize: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}") from exc


@app.post("/synthesize-batch")
def synthesize_batch(requests: List[SynthesisRequest]) -> List[SynthesisResponse]:
    """
    Synthesize multiple text requests in batch.
    Useful for processing multiple items efficiently.
    """
    if not requests:
        raise HTTPException(status_code=400, detail="Request list cannot be empty")
    
    if len(requests) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 requests per batch"
        )
    
    logger.info(f"Processing batch synthesis for {len(requests)} items")
    
    results = []
    for i, request in enumerate(requests):
        try:
            result = synthesize(request)
            results.append(result)
            logger.debug(f"Batch item {i+1}/{len(requests)} completed")
        except Exception as exc:
            logger.error(f"Batch item {i+1} failed: {exc}")
            # Continue processing other items, but log the failure
            raise HTTPException(
                status_code=500,
                detail=f"Batch item {i+1} failed: {exc}"
            ) from exc
    
    return results


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    
    logger.info(f"Starting Kokoro TTS Server on {host}:{port} with {workers} worker(s)")
    
    uvicorn.run(
        "server_kokoro_tts:app",
        host=host,
        port=port,
        workers=workers,
        reload=False,
        log_level=LOG_LEVEL_NAME.lower()
    )
