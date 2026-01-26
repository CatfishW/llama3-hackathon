import re
import os
import requests
import base64
import json
import io
import soundfile as sf
import numpy as np
import hashlib

# Configuration
MAIN_PY = "/data/Yanlai/llama3-hackathon/llama3/Hackathon/prompt-portal/AgentSkillsAnimationExplain/main_2.py"
OUTPUT_DIR = "/data/Yanlai/llama3-hackathon/llama3/Hackathon/prompt-portal/AgentSkillsAnimationExplain/audio"
TTS_URL = "http://localhost:9999/tts"
GURA_PROMPT = "/data/Yanlai/minecraft_server_fabric_1.21.1_fresh/voiceover_prompt_audio/[Gura]A! Gu......ight_.mp3"

EMOTION_PRESETS = [
    (0.65, 0.82),  # Thoughtful
    (0.75, 0.85),  # Neutral
    (0.80, 0.90),  # Slightly excited
    (0.70, 0.82),  # Calm
    (0.82, 0.88),  # Enthusiastic
]

def generate_voiceover(text, output_path, temperature, top_p):
    print(f"Generating: \"{text[:50]}...\"")
    payload = {
        "text": text,
        "speaker_audio_path": GURA_PROMPT,
        "temperature": temperature,
        "top_p": top_p,
        "max_text_tokens_per_segment": 200
    }
    try:
        response = requests.post(TTS_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            audio_bytes = base64.b64decode(data["audio_base64"])
            with io.BytesIO(audio_bytes) as b:
                audio_np, sample_rate = sf.read(b)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            sf.write(output_path, audio_np, sample_rate)
            return True
        else:
            print(f"Error: {data.get('error')}")
    except Exception as e:
        print(f"Exception: {e}")
    return False

def main():
    if not os.path.exists(MAIN_PY):
        print("main.py not found")
        return

    with open(MAIN_PY, 'r') as f:
        content = f.read()

    # Find all play_segment("text", ...) calls
    # Robustly find text even if there are multi-line quotes or other args
    segments_raw = re.findall(r'play_segment\(\s*\"(.*?)\"', content, re.DOTALL)
    
    print(f"Found {len(segments_raw)} unique entries in code.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    active_hashes = set()

    for i, text in enumerate(segments_raw, 0):
        # Clean up text precisely as play_segment does
        clean_text = text.strip()
        txt_hash = hashlib.md5(clean_text.encode()).hexdigest()[:12]
        output_path = os.path.join(OUTPUT_DIR, f"{txt_hash}.ogg")
        active_hashes.add(f"{txt_hash}.ogg")
        
        if os.path.exists(output_path):
            print(f"Hash {txt_hash} already exists, skipping.")
            continue

        temp, top_p = EMOTION_PRESETS[i % len(EMOTION_PRESETS)]
        generate_voiceover(clean_text, output_path, temp, top_p)

    # Cleanup unused audio files
    print("Cleaning up old segments...")
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith(".ogg") and f not in active_hashes:
            print(f"Removing orphan: {f}")
            os.remove(os.path.join(OUTPUT_DIR, f))

if __name__ == "__main__":
    main()
