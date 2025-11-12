import base64
from pathlib import Path
import wave

import numpy as np
import requests

API_URL = "http://localhost:8000/synthesize"
OUTPUT_PATH = Path("sample_output.wav")

TOKENS = [
    50, 157, 43, 135, 16, 53, 135, 46, 16, 43, 102, 16, 56, 156, 57, 135, 6, 16, 102, 62, 61, 16,
    70, 56, 16, 138, 56, 156, 72, 56, 61, 85, 123, 83, 44, 83, 54, 16, 53, 65, 156, 86, 61, 62,
    131, 83, 56, 4
]

payload = {
    "tokens": TOKENS,
    "model_name": "model_q8f16.onnx",
    "voice": "af.bin",
    "speed": 1.0,
}

response = requests.post(API_URL, json=payload, timeout=60)
response.raise_for_status()

body = response.json()
audio_f32 = np.frombuffer(base64.b64decode(body["audio_base64"]), dtype=np.float32)

sample_rate = 24000  # Adjust if your model uses a different rate.
audio_i16 = np.clip(audio_f32, -1.0, 1.0)
audio_i16 = (audio_i16 * np.iinfo(np.int16).max).astype(np.int16)

with wave.open(str(OUTPUT_PATH), "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(audio_i16.tobytes())

print(f"Wrote {len(audio_i16)} samples to {OUTPUT_PATH.resolve()}")
