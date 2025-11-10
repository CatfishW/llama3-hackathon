"""Smoke test client for the OpenAI-compatible proxy.

=== For Machine C (Remote Client) Usage ===

This script connects to the OpenAI-compatible proxy running on Machine B,
which forwards requests to the LLM server on Machine A via SSH tunnel.

Architecture:
  Machine C (this script) → Machine B (proxy on port 8000) → localhost:8080 (SSH tunnel) → Machine A (llama.cpp server)

Setup on Machine B before running this:
1. Ensure SSH tunnel from Machine A is active: ssh -R 8080:localhost:8080 user@machine-b -N
2. Verify llama.cpp is accessible: curl http://localhost:8080/health
3. Start the OpenAI proxy: uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 25565
4. Optional: Configure firewall to allow port 25565 access

Configuration (set via environment variables):
  TEST_API_KEY: API key for authentication (default: sk-local-abc)
  TEST_BASE_URL: URL of Machine B's proxy server (default: http://173.61.35.162:25565/v1)
  TEST_MODEL: Model name (default: qwen3-30b-a3b-instruct)

Run from Machine C:
  python deployment/test_openai_proxy.py

Or with custom configuration:
  set TEST_BASE_URL=http://your-machine-b-ip:8000/v1
  set TEST_API_KEY=your-api-key
  python deployment/test_openai_proxy.py
"""
from __future__ import annotations
import os
import sys

# Check OpenAI library version and import appropriately
try:
    from openai import OpenAI
    # Test if the library supports the base_url parameter properly
    import openai
    print(f"OpenAI library version: {openai.__version__}")
except ImportError:
    print("Error: openai library not installed. Install with: pip install openai")
    sys.exit(1)

API_KEY = os.getenv("TEST_API_KEY", "sk-local-abc")
BASE_URL = os.getenv("TEST_BASE_URL", "http://173.61.35.162:25565/v1")
MODEL = os.getenv("TEST_MODEL", "qwen3-30b-a3b-instruct")

print(f"\n{'='*60}")
print(f"OpenAI Proxy Test Configuration")
print(f"{'='*60}")
print(f"Base URL: {BASE_URL}")
print(f"Model: {MODEL}")
print(f"API Key: {API_KEY[:10]}..." if len(API_KEY) > 10 else f"API Key: {API_KEY}")
print(f"{'='*60}\n")

try:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
except TypeError as e:
    # Handle version compatibility issues
    print(f"Warning: OpenAI client initialization issue: {e}")
    print("Trying alternative initialization...")
    try:
        # For older versions, try without certain parameters
        import httpx
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            http_client=httpx.Client()
        )
    except Exception as e2:
        print(f"Error: Could not initialize OpenAI client: {e2}")
        print("\nTry upgrading the OpenAI library:")
        print("  pip install --upgrade openai")
        sys.exit(1)

def test_connection():
    """Test basic connectivity to the proxy server."""
    print("Testing connection to proxy server...")
    try:
        import httpx
        response = httpx.get(BASE_URL.replace("/v1", ""), timeout=10.0)
        print(f"✓ Proxy server is reachable")
        print(f"  Response: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Cannot reach proxy server: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Is the proxy server running on Machine B?")
        print(f"     uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 25565")
        print(f"  2. Is the SSH tunnel active on Machine B?")
        print(f"     ssh -R 8080:localhost:8080 user@machine-a -N")
        print(f"  3. Is port 25565 accessible from Machine C?")
        print(f"     Check firewall rules on Machine B")
        print(f"  4. Verify BASE_URL is correct: {BASE_URL}")
        return False

def test_models():
    """Test listing available models."""
    print("\nTesting /v1/models endpoint...")
    try:
        models = client.models.list()
        print(f"✓ Available models:")
        for model in models.data:
            print(f"  - {model.id}")
        return True
    except Exception as e:
        print(f"✗ Failed to list models: {e}")
        return False

def test_chat():
    """Test non-streaming chat completion."""
    print("\nTesting chat completion (non-streaming)...")
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say 'pong' and nothing else"}],
            temperature=0.7,
            max_tokens=50,
        )
        content = resp.choices[0].message.content
        print(f"✓ Chat response: {content}")
        return True
    except Exception as e:
        print(f"✗ Chat completion failed: {e}")
        return False

def test_stream():
    """Test streaming chat completion."""
    print("\nTesting chat completion (streaming)...")
    try:
        print("Response: ", end="", flush=True)
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Write 1 short sentence about AI proxies"}],
            stream=True,
            max_tokens=100,
        )
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                print(content, end="", flush=True)
        print()
        print(f"✓ Streaming completed successfully")
        return True
    except Exception as e:
        print(f"\n✗ Streaming failed: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("OpenAI Proxy Integration Test Suite")
    print("="*60)
    
    # Run tests in sequence
    results = []
    
    # Test 1: Connection
    results.append(("Connection", test_connection()))
    
    if results[0][1]:  # Only continue if connection succeeded
        # Test 2: Models
        results.append(("Models List", test_models()))
        
        # Test 3: Non-streaming
        results.append(("Chat Completion", test_chat()))
        
        # Test 4: Streaming
        results.append(("Streaming", test_stream()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:20s} {status}")
    print("="*60)
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n✓ All tests passed! Machine C can successfully access the LLM.")
    else:
        print("\n✗ Some tests failed. Check the output above for details.")
        sys.exit(1)
