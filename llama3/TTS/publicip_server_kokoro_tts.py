"""
Public IP Kokoro TTS Broker Server
Acts as a proxy/broker between public IP machines and private IP TTS server.
Inherits all APIs from server_kokoro_tts.py and forwards requests to remote TTS service.
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ============================================================================
# Local Request/Response Models (mirrors server_kokoro_tts.py)
# ============================================================================

class SynthesisRequest(BaseModel):
    """Request model for text-to-speech synthesis"""
    model_config = {"protected_namespaces": ()}
    
    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Text to synthesize"
    )
    voice: str = Field(
        "af_heart",
        description="Voice name (e.g., 'af_heart', 'af', 'am')"
    )
    lang_code: str = Field(
        "a",
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


# ============================================================================
# Configuration
# ============================================================================

# ============================================================================
# Configuration - supports environment variables and command-line arguments
# ============================================================================

def _parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Kokoro TTS Broker Server - Forward requests to private IP TTS server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python publicip_server_kokoro_tts.py --port 9000
  python publicip_server_kokoro_tts.py --port 8080 --remote-host 192.168.1.100 --remote-port 8081
  python publicip_server_kokoro_tts.py --host 0.0.0.0 --port 8080 --remote-host tts.internal.local
  python publicip_server_kokoro_tts.py --log-level DEBUG
        """
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("BROKER_PORT", "8080")),
        help="Port for broker server to listen on (default: 8080, env: BROKER_PORT)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("BROKER_HOST", "0.0.0.0"),
        help="Host for broker server to bind to (default: 0.0.0.0, env: BROKER_HOST)"
    )
    parser.add_argument(
        "--remote-host",
        type=str,
        default=os.getenv("REMOTE_TTS_HOST", "localhost"),
        help="Remote TTS server host (default: localhost, env: REMOTE_TTS_HOST)"
    )
    parser.add_argument(
        "--remote-port",
        type=int,
        default=int(os.getenv("REMOTE_TTS_PORT", "8081")),
        help="Remote TTS server port (default: 8081, env: REMOTE_TTS_PORT)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("REQUEST_TIMEOUT", "30.0")),
        help="Request timeout in seconds (default: 30.0, env: REQUEST_TIMEOUT)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("TTS_BROKER_LOG_LEVEL", "INFO").upper(),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO, env: TTS_BROKER_LOG_LEVEL)"
    )
    parser.add_argument(
        "--ssl-cert",
        type=str,
        default=os.getenv("SERVER_SSL_CERT", None),
        help="SSL certificate file for HTTPS (env: SERVER_SSL_CERT)"
    )
    parser.add_argument(
        "--ssl-key",
        type=str,
        default=os.getenv("SERVER_SSL_KEY", None),
        help="SSL private key file for HTTPS (env: SERVER_SSL_KEY)"
    )
    
    return parser.parse_args()


# Parse arguments
args = _parse_arguments()

# Configuration values (from arguments or environment variables)
LOG_LEVEL_NAME = args.log_level
REMOTE_TTS_HOST = args.remote_host
REMOTE_TTS_PORT = args.remote_port
REMOTE_TTS_URL = f"http://{REMOTE_TTS_HOST}:{REMOTE_TTS_PORT}"
REQUEST_TIMEOUT = args.timeout
BROKER_HOST = args.host
BROKER_PORT = args.port
SERVER_SSL_CERT = args.ssl_cert
SERVER_SSL_KEY = args.ssl_key

# Logging setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_NAME, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kokoro_tts_broker")
logger.setLevel(getattr(logging, LOG_LEVEL_NAME, logging.INFO))

# FastAPI app
app = FastAPI(
    title="Kokoro TTS Broker Server",
    description="Public IP broker for remote Kokoro TTS server",
    version="1.0.0"
)

# HTTP client for remote requests
_http_client: Optional[httpx.AsyncClient] = None


async def _get_http_client() -> httpx.AsyncClient:
    """Get or create an async HTTP client for remote requests"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    return _http_client


async def _forward_request(
    method: str,
    endpoint: str,
    json_data: Optional[dict] = None
) -> dict:
    """
    Forward a request to the remote TTS server.
    Handles connection errors and timeouts gracefully.
    """
    try:
        client = await _get_http_client()
        url = f"{REMOTE_TTS_URL}{endpoint}"
        
        logger.debug(f"Forwarding {method} request to {url}")
        
        if method.upper() == "GET":
            response = await client.get(url)
        elif method.upper() == "POST":
            response = await client.post(url, json=json_data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
        
    except httpx.ConnectError as exc:
        logger.error(f"Failed to connect to remote TTS server at {REMOTE_TTS_URL}: {exc}")
        raise HTTPException(
            status_code=503,
            detail=f"Remote TTS server unavailable at {REMOTE_TTS_URL}"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error(f"Timeout connecting to remote TTS server: {exc}")
        raise HTTPException(
            status_code=504,
            detail="Remote TTS server request timed out"
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error(f"Remote server returned error: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Remote server error: {exc.response.text}"
        ) from exc
    except Exception as exc:
        logger.error(f"Error forwarding request to remote TTS server: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error forwarding request: {exc}"
        ) from exc


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Kokoro TTS Broker Server starting up...")
    logger.info(f"Remote TTS server configured at: {REMOTE_TTS_URL}")
    logger.info(f"Broker listening on: {BROKER_HOST}:{BROKER_PORT}")
    
    # Test connection to remote server
    try:
        client = await _get_http_client()
        response = await client.get(f"{REMOTE_TTS_URL}/healthz")
        response.raise_for_status()
        logger.info("✓ Successfully connected to remote TTS server")
    except Exception as exc:
        logger.warning(f"⚠ Could not connect to remote TTS server on startup: {exc}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Kokoro TTS Broker Server shutting down...")
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
    logger.info("Shutdown complete")


@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint - checks both broker and remote server health
    """
    try:
        result = await _forward_request("GET", "/healthz")
        return {
            "status": "ok",
            "service": "kokoro_tts_broker",
            "version": "1.0.0",
            "remote_server": result.get("service", "unknown"),
            "remote_status": result.get("status", "unknown")
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Health check failed: {exc}", exc_info=True)
        return {
            "status": "error",
            "service": "kokoro_tts_broker",
            "error": str(exc)
        }


@app.get("/info")
async def server_info() -> Dict[str, object]:
    """
    Get server information including remote server details and defaults.
    Queries remote server for its configuration.
    """
    try:
        remote_info = await _forward_request("GET", "/info")
        
        return {
            "service_name": "Kokoro TTS Broker Server",
            "version": "1.0.0",
            "broker_role": "Public IP Bridge",
            "remote_tts_server": REMOTE_TTS_URL,
            "remote_server_info": remote_info
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get server info: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get server information: {exc}"
        ) from exc


@app.post("/synthesize")
async def synthesize(request: SynthesisRequest) -> SynthesisResponse:
    """
    Synthesize text to speech by forwarding request to remote TTS server.
    Inherits all validation and parameters from server_kokoro_tts.py
    
    Args:
        request: SynthesisRequest containing text, voice, language, and speed
    
    Returns:
        SynthesisResponse with base64-encoded audio and metadata from remote server
    """
    try:
        logger.info(
            f"Synthesis request forwarded: text_len={len(request.text)}, "
            f"voice={request.voice}, lang_code={request.lang_code}, speed={request.speed}"
        )
        
        # Forward the request as JSON
        request_dict = request.model_dump()
        result = await _forward_request("POST", "/synthesize", request_dict)
        
        # Validate response structure
        return SynthesisResponse(**result)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Synthesis request failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Synthesis failed: {exc}"
        ) from exc


@app.post("/synthesize-batch")
async def synthesize_batch(requests: List[SynthesisRequest]) -> List[SynthesisResponse]:
    """
    Synthesize multiple text requests in batch by forwarding to remote TTS server.
    
    Args:
        requests: List of SynthesisRequest objects
    
    Returns:
        List of SynthesisResponse objects from remote server
    """
    try:
        if not requests:
            raise HTTPException(status_code=400, detail="Request list cannot be empty")
        
        if len(requests) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 requests per batch"
            )
        
        logger.info(f"Batch synthesis request forwarded for {len(requests)} items")
        
        # Convert requests to dictionaries
        request_dicts = [req.model_dump() for req in requests]
        
        # Forward the batch request
        results = await _forward_request("POST", "/synthesize-batch", request_dicts)
        
        # Validate and convert response
        return [SynthesisResponse(**result) for result in results]
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Batch synthesis request failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch synthesis failed: {exc}"
        ) from exc


@app.get("/broker-status")
async def broker_status() -> Dict[str, object]:
    """
    Get detailed broker status including remote server connectivity
    """
    try:
        # Test remote server connectivity
        remote_info = await _forward_request("GET", "/info")
        remote_healthy = remote_info.get("service") is not None
        
        return {
            "broker_running": True,
            "remote_server_url": REMOTE_TTS_URL,
            "remote_server_reachable": remote_healthy,
            "broker_host": BROKER_HOST,
            "broker_port": BROKER_PORT,
            "request_timeout": REQUEST_TIMEOUT,
            "remote_server_info": remote_info
        }
    except Exception as exc:
        logger.warning(f"Remote server unreachable: {exc}")
        return {
            "broker_running": True,
            "remote_server_url": REMOTE_TTS_URL,
            "remote_server_reachable": False,
            "broker_host": BROKER_HOST,
            "broker_port": BROKER_PORT,
            "request_timeout": REQUEST_TIMEOUT,
            "error": str(exc)
        }


if __name__ == "__main__":
    import uvicorn

    # Determine if SSL is enabled
    ssl_enabled = SERVER_SSL_CERT and SERVER_SSL_KEY
    protocol = "https" if ssl_enabled else "http"

    print("\n" + "="*70)
    print("Kokoro TTS Broker Server Configuration")
    print("="*70)
    print(f"  Broker listening on:      {protocol}://{BROKER_HOST}:{BROKER_PORT}")
    print(f"  Remote TTS server:        {REMOTE_TTS_URL}")
    print(f"  Request timeout:          {REQUEST_TIMEOUT}s")
    print(f"  Log level:                {LOG_LEVEL_NAME}")
    print(f"  SSL enabled:              {ssl_enabled}")
    if ssl_enabled:
        print(f"  SSL certificate:          {SERVER_SSL_CERT}")
        print(f"  SSL key:                  {SERVER_SSL_KEY}")
    print("="*70 + "\n")
    
    logger.info(
        f"Starting Kokoro TTS Broker Server on {protocol}://{BROKER_HOST}:{BROKER_PORT}\n"
        f"Forwarding requests to TTS server at {REMOTE_TTS_URL}"
    )
    
    # Build SSL kwargs if certificates are provided
    ssl_kwargs = {}
    if ssl_enabled:
        ssl_kwargs = {
            "ssl_certfile": SERVER_SSL_CERT,
            "ssl_keyfile": SERVER_SSL_KEY,
        }
    else:
        logger.warning(
            "Running without HTTPS. Browsers on HTTPS pages will block requests. "
            "Use --ssl-cert and --ssl-key to enable HTTPS."
        )
    
    uvicorn.run(
        "publicip_server_kokoro_tts:app",
        host=BROKER_HOST,
        port=BROKER_PORT,
        workers=1,
        reload=False,
        log_level=LOG_LEVEL_NAME.lower(),
        **ssl_kwargs
    )
