"""Smoke test client for the OpenAI-compatible proxy.
Run after starting uvicorn server.

python deployment/test_openai_proxy.py
"""
from __future__ import annotations
import os
from openai import OpenAI

API_KEY = os.getenv("TEST_API_KEY", "sk-local-abc")
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000/v1")
MODEL = os.getenv("TEST_MODEL", "qwen3-30b-a3b-instruct")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def test_chat():
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Say 'pong'"}],
        temperature=0.7,
    )
    print("Chat response:", resp.choices[0].message.content)

def test_stream():
    print("Streaming:")
    with client.chat.completions.stream(
        model=MODEL,
        messages=[{"role": "user", "content": "Write 1 short sentence about proxies"}],
        stream=True,
    ) as stream:
        for event in stream:
            if event.type == "content.delta":
                print(event.delta, end="", flush=True)
    print()

if __name__ == "__main__":
    test_chat()
    test_stream()
