"""Quick manual test for image-enabled chat endpoint.
Run after starting the FastAPI server (ensure /api base path).

Usage (Windows PowerShell):
python test_image_message.py
"""
import base64
import requests

API_BASE = "http://localhost:8000/api/chat"

# 1x1 transparent PNG
PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAA"  # shortened portion
    "AAAC0lEQVR42mP4/58BAgMDEA0GAbcCAgAAAABJRU5ErkJggg=="
)
DATA_URL = f"data:image/png;base64,{PNG_BASE64}"

def main():
    # Create session
    r = requests.post(f"{API_BASE}/sessions", json={"title": "Vision Test"})
    r.raise_for_status()
    session = r.json()
    sid = session["id"]
    print("Session created", sid)

    payload = {
        "session_id": sid,
        "content": "What do you see?",
        "images": [DATA_URL],
    }
    r2 = requests.post(f"{API_BASE}/messages", json=payload)
    print("Status:", r2.status_code)
    print("Response:", r2.text[:500])

if __name__ == "__main__":
    main()
