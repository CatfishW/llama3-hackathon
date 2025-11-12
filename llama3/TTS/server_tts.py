import base64
import logging
import os
import sys
from pathlib import Path
from threading import Lock
from typing import Dict, List, Tuple

import numpy as np
from fastapi import FastAPI, HTTPException
from huggingface_hub import hf_hub_download
from onnxruntime import InferenceSession, SessionOptions, GraphOptimizationLevel, get_available_providers
from pydantic import BaseModel, Field

REPO_ID = "onnx-community/Kokoro-82M-v1.0-ONNX"
ROOT_DIR = Path(__file__).resolve().parent
ONNX_DIR = Path("assets/models--onnx-community--Kokoro-82M-v1.0-ONNX/snapshots/1939ad2a8e416c0acfeecc08a694d14ef25f2231/onnx/")
VOICE_DIR = Path("assets/models--onnx-community--Kokoro-82M-v1.0-ONNX/snapshots/1939ad2a8e416c0acfeecc08a694d14ef25f2231/voices/")
DEFAULT_MODEL = "model_q8f16.onnx"
DEFAULT_VOICE = "af.bin"
CONTEXT_LIMIT = 512

LOG_LEVEL_NAME = os.getenv("TTS_SERVER_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_NAME, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kokoro_tts")
logger.setLevel(getattr(logging, LOG_LEVEL_NAME, logging.INFO))

app = FastAPI(title="Kokoro TTS Server")

_session_cache: Dict[str, InferenceSession] = {}
_session_paths: Dict[str, Path] = {}
_voice_cache: Dict[str, np.ndarray] = {}
_voice_paths: Dict[str, Path] = {}
_cache_lock = Lock()


class SynthesisRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    tokens: List[int] = Field(..., min_items=1, max_items=CONTEXT_LIMIT - 2)
    model_name: str = Field(DEFAULT_MODEL)
    voice: str = Field(DEFAULT_VOICE)
    speed: float = Field(1.0, gt=0.0)


def _ensure_local_file(filename: str, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    local_path = target_dir / Path(filename).name
    if local_path.exists():
        logger.debug(f"Using cached file: {local_path}")
        return local_path
    logger.info(f"Downloading {filename}...")
    remote_path = hf_hub_download(repo_id=REPO_ID, filename=filename)
    local_path.write_bytes(Path(remote_path).read_bytes())
    logger.info(f"Downloaded {filename} to {local_path}")
    return local_path


def _resolve_model(model_name: str) -> Path:
    filename = f"onnx/{model_name}"
    try:
        return _ensure_local_file(filename, ONNX_DIR)
    except Exception as exc:
        logger.error(f"Error resolving model '{model_name}': {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to prepare model '{model_name}': {exc}") from exc


def _resolve_voice(voice_file: str) -> Path:
    file_key = voice_file if voice_file.endswith(".bin") else f"{voice_file}.bin"
    filename = f"voices/{Path(file_key).name}"
    try:
        return _ensure_local_file(filename, VOICE_DIR)
    except Exception as exc:
        logger.error(f"Error resolving voice '{voice_file}': {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to prepare voice '{voice_file}': {exc}") from exc


def _get_session(model_name: str) -> Tuple[InferenceSession, Path]:
    with _cache_lock:
        model_path = _session_paths.get(model_name)
        if model_name not in _session_cache or model_path is None:
            model_path = _resolve_model(model_name)
            logger.info(f"Initializing model session '{model_name}' from {model_path}")
            if not model_path.exists():
                logger.error(f"Model file not found at {model_path}")
                raise HTTPException(status_code=500, detail=f"Model file not found at {model_path}")
            try:
                available_providers = get_available_providers()
                logger.info(f"Available ONNX providers: {available_providers}")
                
                sess_options = SessionOptions()
                sess_options.graph_optimization_level = GraphOptimizationLevel.ORT_DISABLE_ALL
                
                # Prioritize GPU providers, fallback to CPU
                providers_to_try = []
                if "CUDAExecutionProvider" in available_providers:
                    providers_to_try.append(["CUDAExecutionProvider", "CPUExecutionProvider"])
                if "TensorrtExecutionProvider" in available_providers:
                    providers_to_try.append(["TensorrtExecutionProvider", "CPUExecutionProvider"])
                providers_to_try.append(["CPUExecutionProvider"])
                
                session = None
                last_error = None
                for providers in providers_to_try:
                    try:
                        logger.info(f"Attempting to load model with providers: {providers}")
                        session = InferenceSession(
                            model_path.as_posix(),
                            sess_options,
                            providers=providers
                        )
                        logger.info(f"InferenceSession created successfully with providers: {providers}")
                        break
                    except Exception as e:
                        logger.debug(f"Failed with providers {providers}: {e}")
                        last_error = e
                        continue
                
                if session is None:
                    logger.error(f"Failed to create InferenceSession with all provider options")
                    raise last_error or Exception("Failed to create InferenceSession")
                
                _session_cache[model_name] = session
            except Exception as e:
                logger.error(f"Failed to create InferenceSession: {e}", exc_info=True)
                raise
            _session_paths[model_name] = model_path
        else:
            logger.debug(f"Reusing cached model session '{model_name}'")
        return _session_cache[model_name], _session_paths[model_name]


def _get_voice_tensor(voice_name: str) -> Tuple[np.ndarray, Path]:
    cache_key = voice_name if voice_name.endswith(".bin") else f"{voice_name}.bin"
    with _cache_lock:
        voice_path = _voice_paths.get(cache_key)
        if cache_key not in _voice_cache or voice_path is None:
            voice_path = _resolve_voice(cache_key)
            logger.info(f"Loading voice '{cache_key}' from {voice_path}")
            if not voice_path.exists():
                logger.error(f"Voice file not found at {voice_path}")
                raise HTTPException(status_code=500, detail=f"Voice file not found at {voice_path}")
            _voice_cache[cache_key] = np.fromfile(voice_path, dtype=np.float32).reshape(-1, 1, 256)
            _voice_paths[cache_key] = voice_path
        else:
            logger.debug(f"Reusing cached voice '{cache_key}'")
        return _voice_cache[cache_key], _voice_paths[cache_key]


@app.get("/healthz")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "default_model": DEFAULT_MODEL}


@app.post("/synthesize")
def synthesize(request: SynthesisRequest) -> Dict[str, object]:
    try:
        logger.info(f"Synthesis request: model={request.model_name}, voice={request.voice}, tokens={len(request.tokens)}, speed={request.speed}")
        tokens = request.tokens
        if any(t < 0 for t in tokens):
            raise HTTPException(status_code=400, detail="Tokens must be non-negative integers.")
        
        voice_tensor, voice_path = _get_voice_tensor(request.voice)
        logger.debug(f"Voice tensor shape: {voice_tensor.shape}")
        
        if len(tokens) >= voice_tensor.shape[0]:
            raise HTTPException(
                status_code=400,
                detail=f"Voice embedding length {voice_tensor.shape[0] - 1} exceeded by token count {len(tokens)}.",
            )

        session, model_path = _get_session(request.model_name)
        
        input_ids = np.array([[0, *tokens, 0]], dtype=np.int64)
        style = voice_tensor[len(tokens)]
        speed = np.array([request.speed], dtype=np.float32)

        logger.debug(f"Input shapes - input_ids: {input_ids.shape}, style: {style.shape}, speed: {speed.shape}")

        try:
            logger.debug("Running inference...")
            output = session.run(None, {"input_ids": input_ids, "style": style, "speed": speed})
            audio = output[0].squeeze()
            logger.debug(f"Inference completed. Audio shape: {audio.shape}")
        except Exception as exc:
            logger.error(f"Inference failed: {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

        audio_bytes = base64.b64encode(audio.astype(np.float32).tobytes()).decode("utf-8")
        return {
            "audio_base64": audio_bytes,
            "dtype": "float32",
            "frame_count": int(audio.size),
            "model_name": request.model_name,
            "model_path": model_path.as_posix(),
            "voice": request.voice,
            "voice_path": voice_path.as_posix(),
        }
    except Exception as exc:
        logger.error(f"Unexpected error in synthesize: {exc}", exc_info=True)
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server_tts:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
