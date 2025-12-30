
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.services.llm_client import detect_model_from_url
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_url():
    url = "https://game.agaii.org/llm/v1"
    print(f"Testing detection from: {url}")
    
    model_name = detect_model_from_url(url, api_key="not-needed")
    
    if model_name:
        print(f"SUCCESS: Detect model '{model_name}'")
        
        # Now try to generate text to verify it works
        print("\nTesting generation with detected model...")
        try:
            import httpx
            from openai import OpenAI
            
            # Construct base_url same as LLMClient
            base_url = url.rstrip('/')
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            
            print(f"Using Base URL: {base_url}")
            client = OpenAI(base_url=base_url, api_key="not-needed")
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "Hello, say hi!"}],
                max_tokens=50
            )
            print("Generation Response:", response.choices[0].message.content)
            print("SUCCESS: Generation worked.")
            
        except Exception as e:
            print(f"FAILURE: Generation failed: {e}")
            
    else:
        print("FAILURE: Could not detect model.")

if __name__ == "__main__":
    test_url()
