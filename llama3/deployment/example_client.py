"""
Simple example client for Machine C to access LLM via Machine B proxy.

This is a minimal working example you can customize for your needs.

Usage:
    1. Set environment variables or edit the config below
    2. Run: python deployment/example_client.py
"""
from __future__ import annotations
import os
import sys

try:
    from openai import OpenAI
    import httpx
except ImportError:
    print("Error: Required libraries not installed.")
    print("Install with: pip install openai httpx")
    sys.exit(1)

# ==================== CONFIGURATION ====================
# Edit these values or set as environment variables

BASE_URL = os.getenv("LLM_BASE_URL", "http://173.61.35.162:25565/v1")
API_KEY = os.getenv("LLM_API_KEY", "sk-local-abc")
MODEL = os.getenv("LLM_MODEL", "qwen3-30b-a3b-instruct")

# =======================================================

def create_client():
    """Create OpenAI client with fallback for compatibility."""
    try:
        return OpenAI(api_key=API_KEY, base_url=BASE_URL)
    except TypeError:
        # Fallback for older versions
        return OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            http_client=httpx.Client()
        )

def simple_chat(prompt: str, temperature: float = 0.7, max_tokens: int = 500):
    """Send a simple chat request and get a response."""
    client = create_client()
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content

def streaming_chat(prompt: str, temperature: float = 0.7, max_tokens: int = 500):
    """Send a streaming chat request and print responses in real-time."""
    client = create_client()
    
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True
    )
    
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_response += content
            print(content, end="", flush=True)
    
    print()  # New line after streaming
    return full_response

def conversation(system_prompt: str = "You are a helpful assistant."):
    """Interactive conversation loop."""
    client = create_client()
    messages = [{"role": "system", "content": system_prompt}]
    
    print(f"Connected to: {BASE_URL}")
    print(f"Model: {MODEL}")
    print("Type 'quit' or 'exit' to end the conversation.\n")
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Add user message
        messages.append({"role": "user", "content": user_input})
        
        # Get AI response (streaming)
        print("AI: ", end="", flush=True)
        try:
            stream = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                stream=True
            )
            
            ai_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    ai_response += content
                    print(content, end="", flush=True)
            
            print("\n")  # New line after response
            
            # Add AI response to history
            messages.append({"role": "assistant", "content": ai_response})
            
        except Exception as e:
            print(f"\nError: {e}")
            print("Please check your connection and try again.\n")

def main():
    """Main function with examples."""
    print("="*60)
    print("Machine C - LLM Client Example")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Model: {MODEL}")
    print("="*60)
    print()
    
    # Example 1: Simple non-streaming request
    print("Example 1: Simple Chat Request")
    print("-" * 60)
    try:
        response = simple_chat("What is 2+2? Answer briefly.")
        print(f"Response: {response}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the proxy server is running and accessible.")
        return
    
    # Example 2: Streaming request
    print("\nExample 2: Streaming Chat Request")
    print("-" * 60)
    print("Response: ", end="", flush=True)
    try:
        streaming_chat("Write a haiku about AI.")
        print()
    except Exception as e:
        print(f"\nError: {e}")
        return
    
    # Example 3: Interactive conversation
    print("\nExample 3: Interactive Conversation")
    print("-" * 60)
    try:
        conversation("You are a friendly AI assistant who gives concise answers.")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    # Check if user wants to run in interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        try:
            conversation()
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
    else:
        main()
