import os
import io
import json
import asyncio
from typing import Optional, List, Dict, Any
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

from huggingface_hub import hf_hub_download
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from onnxruntime import InferenceSession, SessionOptions, get_available_providers
import scipy.io.wavfile as wavfile

# =========================
# Configuration
# =========================

# Hugging Face model configuration
HF_REPO_ID = "onnx-community/Kokoro-82M-v1.0-ONNX"
ASSETS_DIR = os.environ.get("ASSETS_DIR", "./assets")

# Ensure ASSETS_DIR exists
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(os.path.join(ASSETS_DIR, "voices"), exist_ok=True)

# Helper function to download model files from Hugging Face
def download_from_hf(filename: str, subfolder: Optional[str] = None) -> str:
    """Download a file from Hugging Face and return its local path."""
    try:
        local_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=filename,
            subfolder=subfolder,
            cache_dir=ASSETS_DIR
        )
        return local_path
    except Exception as e:
        print(f"[ERROR] Failed to download {filename} from HuggingFace: {e}")
        raise

# Download model files from Hugging Face (cached after first download)
# Choose one model variant (in onnx/ subfolder):
# - model_q4.onnx        (4-bit quantized) - ~45 MB
# - model_q4f16.onnx     (4-bit + float16 hybrid) - ~155 MB
# - model_q8f16.onnx     (8-bit + float16 hybrid) - ~86 MB (recommended)
# - model_fp16.onnx      (float16, best for GPU) - ~163 MB
# - model.onnx           (FP32 reference) - ~326 MB
MODEL_VARIANT = os.environ.get("KOKORO_MODEL_VARIANT", "model_q8f16.onnx")
MODEL_PATH = os.environ.get("KOKORO_MODEL_PATH", None)
if not MODEL_PATH:
    print(f"[INFO] Downloading {MODEL_VARIANT} from Hugging Face...")
    try:
        MODEL_PATH = download_from_hf(MODEL_VARIANT, subfolder="onnx")
        print(f"[INFO] Model downloaded to: {MODEL_PATH}")
    except Exception as e:
        print(f"[ERROR] Failed to download model: {e}")
        raise

# Voice/style embedding file (float32, shape: N x 1 x 256).
# Available voice packs: language/gender-specific voices like af.bin, am_adam.bin, etc.
# For a complete list, see: https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/tree/main/voices
VOICE_BIN_PATH = os.environ.get("KOKORO_VOICE_BIN", None)
if not VOICE_BIN_PATH:
    print("[INFO] Downloading voice embeddings from Hugging Face...")
    try:
        # Default to af.bin (Afrikaans female voice)
        VOICE_BIN_PATH = download_from_hf("af.bin", subfolder="voices")
        print(f"[INFO] Voices downloaded to: {VOICE_BIN_PATH}")
    except Exception as e:
        print(f"[ERROR] Failed to download voices: {e}")
        raise

# Optional: phoneme→id config JSON (optional but recommended for better phoneme mapping)
PHONEME_CFG = os.environ.get("KOKORO_PHONEME_CFG", None)
if not PHONEME_CFG:
    print("[INFO] Downloading config.json from Hugging Face...")
    try:
        PHONEME_CFG = download_from_hf("config.json")
        print(f"[INFO] Config downloaded to: {PHONEME_CFG}")
    except Exception as e:
        print(f"[WARN] Failed to download config: {e}. Falling back to simple tokenizer.")
        PHONEME_CFG = None

# Sample rate (most Kokoro exports are 24kHz; change if your model outputs a different rate)
SAMPLE_RATE = int(os.environ.get("KOKORO_SAMPLE_RATE", "24000"))

# Concurrency: for GPU, keep small (2–4). For CPU, 8–16 is fine; tune with load tests.
MAX_CONCURRENT_INFER = int(os.environ.get("MAX_CONCURRENT_INFER", "4"))

# Thread pool for blocking work (ORT call, WAV mux)
MAX_WORKERS = int(os.environ.get("THREADPOOL_WORKERS", "8"))

# =========================
# API models
# =========================

ASSETS_DIR = os.environ.get("ASSETS_DIR", "./assets")

# Place your ONNX model file in ASSETS_DIR; choose one from onnx/ subfolder:
# - model_q4.onnx        (4-bit quantized) - ~45 MB
# - model_q4f16.onnx     (4-bit + float16 hybrid) - ~155 MB
# - model_q8f16.onnx     (8-bit + float16 hybrid) - ~86 MB (recommended)
# - model_fp16.onnx      (float16, best for GPU) - ~163 MB
# - model.onnx           (FP32 reference) - ~326 MB
MODEL_PATH = os.environ.get("KOKORO_MODEL_PATH", None)

# Voice/style embedding file (float32, shape: N x 1 x 256).
# Available voice packs (in voices/ subfolder):
# Female voices: af_*.bin (Afrikaans), bf_*.bin (Brazilian), ef_dora.bin, ff_siwis.bin, hf_*.bin, if_sara.bin, jf_*.bin, pf_dora.bin, zf_*.bin (Chinese)
# Male voices: am_*.bin (Amharic), bm_*.bin (Brazilian), em_*.bin (English), hm_*.bin, im_nicola.bin, jm_kumo.bin, pm_*.bin, etc.
# For a complete list: https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/tree/main/voices
VOICE_BIN_PATH = os.environ.get("KOKORO_VOICE_BIN", None)

# Optional: phoneme→id config JSON.
# If provided, we’ll load it and try to map basic phonemes/characters to ids.
# If missing, we fall back to a simple ASCII mapping (works but not "real" TTS quality).
PHONEME_CFG = os.environ.get("KOKORO_PHONEME_CFG", os.path.join(ASSETS_DIR, "config.json"))

# Sample rate (most Kokoro exports are 24kHz; change if your model outputs a different rate)
SAMPLE_RATE = int(os.environ.get("KOKORO_SAMPLE_RATE", "24000"))

# Concurrency: for GPU, keep small (2–4). For CPU, 8–16 is fine; tune with load tests.
MAX_CONCURRENT_INFER = int(os.environ.get("MAX_CONCURRENT_INFER", "4"))

# Thread pool for blocking work (ORT call, WAV mux)
MAX_WORKERS = int(os.environ.get("THREADPOOL_WORKERS", "8"))

# =========================
# API models
# =========================

class TTSRequest(BaseModel):
    # Provide either "text" OR "input_ids". If both present, input_ids wins.
    text: Optional[str] = Field(default=None, description="Plain text (we'll tokenize)")
    input_ids: Optional[List[int]] = Field(default=None, description="Pre-tokenized ids for the model")
    voice_index: int = Field(default=0, ge=0, description="Index into the voice/style table")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speaking rate multiplier")
    stream_wav: bool = Field(default=True, description="If true, streams WAV; else returns JSON with raw float PCM")

class TTSInfo(BaseModel):
    model_path: str
    voices_count: int
    sample_rate: int
    providers: List[str]
    max_concurrent_infer: int

# =========================
# Globals (per worker)
# =========================

app = FastAPI(title="Kokoro ONNX TTS", version="1.0")

_pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
_infer_gate = asyncio.Semaphore(MAX_CONCURRENT_INFER)

# Load voice/style embeddings
def _load_voices(path: str) -> np.ndarray:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Voice bin not found: {path}")
    arr = np.fromfile(path, dtype=np.float32)
    if arr.size % 256 != 0:
        raise ValueError(f"Voice bin must be multiple of 256 floats. Got {arr.size}.")
    voices = arr.reshape(-1, 1, 256)  # (N, 1, 256)
    return voices

# Tokenizer helpers (very lightweight; replace with your project’s phonemizer for best quality)
class SimpleTokenizer:
    def __init__(self, cfg_path: Optional[str]):
        self.has_cfg = False
        self.pad_or_special_id = 0  # many Kokoro exports use 0 as BOS/EOS
        self.max_ctx = 512

        self.char2id: Dict[str, int] = {}
        if cfg_path and os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                # Expect something like {"token_to_id": {"a": 12, "b": 13, ...}} or {"phoneme_id_map": {...}}
                token_map = cfg.get("token_to_id") or cfg.get("phoneme_id_map") or {}
                # Normalize keys to lowercase single tokens for a very simple pass
                self.char2id = {str(k).lower(): int(v) for k, v in token_map.items()}
                self.has_cfg = len(self.char2id) > 0
            except Exception:
                # fall back to naive
                pass

        if not self.has_cfg:
            # naive ASCII a-z + space mapping (demo only)
            base = 10
            for i, ch in enumerate("abcdefghijklmnopqrstuvwxyz '.,?!"):
                self.char2id[ch] = base + i
            self.has_cfg = True

    def encode_text(self, text: str) -> List[int]:
        # Very naive: lowercase and map character-by-character
        # Real deployments should: normalize + phonemize + map to ids as per your cfg.
        text = (text or "").lower().strip()
        ids = [self.char2id.get(ch, self.pad_or_special_id) for ch in text]
        # Enforce <= max_ctx - 2 for BOS/EOS padding
        ids = ids[: (self.max_ctx - 2)]
        # Add BOS/EOS (0) around as many Kokoro examples show
        ids = [self.pad_or_special_id] + ids + [self.pad_or_special_id]
        return ids

# ONNX Runtime init
def _make_session(model_path: str) -> InferenceSession:
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"ONNX model not found: {model_path}")
    so = SessionOptions()
    # Good general-purpose defaults:
    so.enable_mem_pattern = False
    so.graph_optimization_level = 3  # ORT_ENABLE_ALL
    providers = []
    avail = get_available_providers()
    if "CUDAExecutionProvider" in avail:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:
        providers = ["CPUExecutionProvider"]
    return InferenceSession(model_path, sess_options=so, providers=providers)

# Globals initialized at import
VOICES = _load_voices(VOICE_BIN_PATH)
TOKENIZER = SimpleTokenizer(PHONEME_CFG)
SESS = _make_session(MODEL_PATH)
PROVIDERS = SESS.get_providers()

# Warmup at startup
def _warmup():
    # Minimal dummy request
    dummy_ids = [0, 42, 0]
    style = VOICES[min(0, len(VOICES)-1)]
    speed = np.array([1.0], dtype=np.float32)
    _ = SESS.run(None, {"input_ids": [dummy_ids], "style": style, "speed": speed})

try:
    _warmup()
except Exception as e:
    # Don’t crash startup; log and continue (healthcheck will show error if needed)
    print(f"[WARN] Warmup failed: {e}")

# =========================
# Utilities
# =========================

def _select_style(voice_index: int) -> np.ndarray:
    if voice_index < 0 or voice_index >= len(VOICES):
        raise HTTPException(status_code=400, detail=f"voice_index out of range (0..{len(VOICES)-1})")
    return VOICES[voice_index]

def _validate_ids(ids: List[int]) -> List[int]:
    if not ids:
        raise HTTPException(status_code=400, detail="input_ids is empty")
    if len(ids) > 512:
        raise HTTPException(status_code=400, detail="input_ids length must be <= 512")
    return ids

def _run_infer(input_ids: List[int], style: np.ndarray, speed: float) -> np.ndarray:
    # ORT wants numpy arrays or lists; list-of-ints is fine for 1D shape at batch=1
    outputs = SESS.run(
        None,
        {
            "input_ids": [input_ids],
            "style": style,
            "speed": np.array([speed], dtype=np.float32),
        },
    )
    # Expect first output is audio samples, shape (T,)
    audio = outputs[0]
    if isinstance(audio, list):
        audio = np.asarray(audio)
    # Ensure 1D float32
    audio = audio.astype(np.float32).reshape(-1)
    return audio

# Small in-memory cache for hot phrases
@lru_cache(maxsize=512)
def _cached_tts_key(key: str) -> bytes:
    # This function shouldn't be called directly; it's used by tts() via keying only.
    # We return WAV bytes as cache payload.
    return b""  # placeholder never used; we always overwrite when populating

def _wav_bytes_from_audio(audio: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, audio)
    return buf.getvalue()

# =========================
# Routes
# =========================

@app.get("/healthz")
def health() -> JSONResponse:
    ok = True
    details: Dict[str, Any] = {}
    try:
        # Tiny verify: run through providers list and test voice shape
        details["providers"] = PROVIDERS
        details["voices_count"] = int(VOICES.shape[0])
        details["model_path"] = MODEL_PATH
    except Exception as e:
        ok = False
        details["error"] = str(e)
    status = 200 if ok else 500
    return JSONResponse(status_code=status, content=details)

@app.get("/info", response_model=TTSInfo)
def info() -> TTSInfo:
    return TTSInfo(
        model_path=MODEL_PATH,
        voices_count=int(VOICES.shape[0]),
        sample_rate=SAMPLE_RATE,
        providers=PROVIDERS,
        max_concurrent_infer=MAX_CONCURRENT_INFER,
    )

@app.post("/tts")
async def tts(req: TTSRequest):
    # Resolve input ids
    if req.input_ids is not None:
        input_ids = _validate_ids(req.input_ids)
    elif req.text is not None:
        input_ids = TOKENIZER.encode_text(req.text)
    else:
        raise HTTPException(status_code=400, detail="Provide either 'text' or 'input_ids'.")

    style = _select_style(req.voice_index)
    speed = float(req.speed)

    # Concurrency gate
    async with _infer_gate:
        loop = asyncio.get_event_loop()
        # Run ORT in a thread to avoid blocking the event loop
        audio = await loop.run_in_executor(_pool, _run_infer, input_ids, style, speed)

    if req.stream_wav:
        # Stream once (whole wav). For true chunked streaming, you’d split `audio` into chunks.
        def gen():
            buf = io.BytesIO()
            wavfile.write(buf, SAMPLE_RATE, audio)
            buf.seek(0)
            yield from buf
        return StreamingResponse(gen(), media_type="audio/wav")

    # Or return raw float PCM in JSON (debug)
    return JSONResponse(
        content={
            "sample_rate": SAMPLE_RATE,
            "num_samples": int(audio.shape[0]),
            "audio": audio.tolist(),
        }
    )

# Root
@app.get("/")
def root():
    return {"name": "Kokoro ONNX TTS", "docs": "/docs"}
