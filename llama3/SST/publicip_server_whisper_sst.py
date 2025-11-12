"""
Public IP Whisper.cpp SST Broker Server
Acts as a proxy/broker between public IP machines and private IP Whisper.cpp server.
Inherits all APIs from whisper.cpp server and forwards requests to remote SST service.
"""

import argparse
import logging
import os
import sys
from typing import Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# ============================================================================
# Local Request/Response Models (mirrors whisper.cpp server)
# ============================================================================

class InferenceResponse(BaseModel):
    """Response model for speech-to-text inference"""
    model_config = {"protected_namespaces": ()}
    
    result: dict
    language: Optional[str] = None
    duration: Optional[float] = None


class LoadModelRequest(BaseModel):
    """Request model for loading a model"""
    model_path: str = Field(
        ...,
        min_length=1,
        description="Path to the model file"
    )


class LoadModelResponse(BaseModel):
    """Response model for model loading"""
    status: str
    message: str


# ============================================================================
# Configuration - supports environment variables and command-line arguments
# ============================================================================

def _parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Whisper.cpp SST Broker Server - Forward requests to private IP Whisper server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python publicip_server_whisper_sst.py --port 9082
  python publicip_server_whisper_sst.py --port 8082 --remote-host 192.168.1.100 --remote-port 8082
  python publicip_server_whisper_sst.py --host 0.0.0.0 --port 8082 --remote-host sst.internal.local
  python publicip_server_whisper_sst.py --log-level DEBUG
        """
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("BROKER_PORT", "9082")),
        help="Port for broker server to listen on (default: 9082, env: BROKER_PORT)"
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
        default=os.getenv("REMOTE_SST_HOST", "localhost"),
        help="Remote SST server host (default: localhost, env: REMOTE_SST_HOST)"
    )
    parser.add_argument(
        "--remote-port",
        type=int,
        default=int(os.getenv("REMOTE_SST_PORT", "8082")),
        help="Remote SST server port (default: 8082, env: REMOTE_SST_PORT)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("REQUEST_TIMEOUT", "300.0")),
        help="Request timeout in seconds (default: 300.0, env: REQUEST_TIMEOUT)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("SST_BROKER_LOG_LEVEL", "INFO").upper(),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO, env: SST_BROKER_LOG_LEVEL)"
    )
    
    return parser.parse_args()


# Parse arguments
args = _parse_arguments()

# Configuration values (from arguments or environment variables)
LOG_LEVEL_NAME = args.log_level
REMOTE_SST_HOST = args.remote_host
REMOTE_SST_PORT = args.remote_port
REMOTE_SST_URL = f"http://{REMOTE_SST_HOST}:{REMOTE_SST_PORT}"
REQUEST_TIMEOUT = args.timeout
BROKER_HOST = args.host
BROKER_PORT = args.port

# Logging setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL_NAME, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("whisper_sst_broker")
logger.setLevel(getattr(logging, LOG_LEVEL_NAME, logging.INFO))

# FastAPI app
app = FastAPI(
    title="Whisper.cpp SST Broker Server",
    description="Public IP broker for remote Whisper.cpp SST server",
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
    json_data: Optional[dict] = None,
    files: Optional[dict] = None,
    data: Optional[dict] = None
) -> dict:
    """
    Forward a request to the remote SST server.
    Handles connection errors and timeouts gracefully.
    """
    try:
        client = await _get_http_client()
        url = f"{REMOTE_SST_URL}{endpoint}"
        
        logger.debug(f"Forwarding {method} request to {url}")
        
        if method.upper() == "GET":
            response = await client.get(url)
        elif method.upper() == "POST":
            if files:
                # For multipart file uploads
                response = await client.post(url, files=files, data=data)
            elif json_data:
                response = await client.post(url, json=json_data)
            else:
                response = await client.post(url, data=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        
        # Try to parse as JSON, otherwise return as text
        try:
            return response.json()
        except:
            return {"result": response.text}
        
    except httpx.ConnectError as exc:
        logger.error(f"Failed to connect to remote SST server at {REMOTE_SST_URL}: {exc}")
        raise HTTPException(
            status_code=503,
            detail=f"Remote SST server unavailable at {REMOTE_SST_URL}"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error(f"Timeout connecting to remote SST server: {exc}")
        raise HTTPException(
            status_code=504,
            detail="Remote SST server request timed out"
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error(f"Remote server returned error: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Remote server error: {exc.response.text}"
        ) from exc
    except Exception as exc:
        logger.error(f"Error forwarding request to remote SST server: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error forwarding request: {exc}"
        ) from exc


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Whisper.cpp SST Broker Server starting up...")
    logger.info(f"Remote SST server configured at: {REMOTE_SST_URL}")
    logger.info(f"Broker listening on: {BROKER_HOST}:{BROKER_PORT}")
    
    # Test connection to remote server
    try:
        client = await _get_http_client()
        response = await client.get(f"{REMOTE_SST_URL}/")
        response.raise_for_status()
        logger.info("✓ Successfully connected to remote SST server")
    except Exception as exc:
        logger.warning(f"⚠ Could not connect to remote SST server on startup: {exc}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Whisper.cpp SST Broker Server shutting down...")
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
    logger.info("Shutdown complete")


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """
    Serve HTML UI - forward to remote server if available, or provide broker info
    """
    try:
        # Try to get HTML from remote server
        client = await _get_http_client()
        response = await client.get(f"{REMOTE_SST_URL}/")
        response.raise_for_status()
        return response.text
    except:
        # Fallback: provide broker info
        return f"""
        <html>
        <head>
            <title>Whisper.cpp SST Broker Server</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width">
            <style>
            body {{
                font-family: sans-serif;
                margin: 2rem;
            }}
            .info-box {{
                background-color: #f0f0f0;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
            }}
            pre {{
                background-color: #f5f5f5;
                padding: 1rem;
                border-radius: 0.25rem;
                overflow-x: auto;
            }}
            </style>
        </head>
        <body>
            <h1>Whisper.cpp SST Broker Server</h1>
            <div class="info-box">
                <p><strong>Role:</strong> Public IP Bridge to Remote SST Server</p>
                <p><strong>Remote Server:</strong> {REMOTE_SST_URL}</p>
                <p><strong>Status:</strong> Broker Online (Remote server may be offline)</p>
            </div>

            <h2>/inference</h2>
            <pre>
curl 127.0.0.1:{BROKER_PORT}/inference \\
    -H "Content-Type: multipart/form-data" \\
    -F file="@<file-path>" \\
    -F temperature="0.0" \\
    -F temperature_inc="0.2" \\
    -F response_format="json"
            </pre>

            <h2>/load</h2>
            <pre>
curl 127.0.0.1:{BROKER_PORT}/load \\
    -H "Content-Type: application/json" \\
    -d '{{"model_path": "<path-to-model-file>"}}'
            </pre>

            <h2>Available Endpoints</h2>
            <ul>
                <li><strong>GET /</strong> - This page</li>
                <li><strong>GET /healthz</strong> - Health check (broker + remote server)</li>
                <li><strong>GET /info</strong> - Server information</li>
                <li><strong>POST /inference</strong> - Perform speech-to-text inference</li>
                <li><strong>POST /load</strong> - Load a model</li>
                <li><strong>GET /broker-status</strong> - Detailed broker status</li>
            </ul>
        </body>
        </html>
        """


@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint - checks both broker and remote server health
    """
    try:
        result = await _forward_request("GET", "/")
        return {
            "status": "ok",
            "service": "whisper_sst_broker",
            "version": "1.0.0",
            "remote_server": "whisper.cpp",
            "remote_status": "ok"
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Health check failed: {exc}", exc_info=True)
        return {
            "status": "error",
            "service": "whisper_sst_broker",
            "error": str(exc)
        }


@app.get("/info")
async def server_info() -> Dict[str, object]:
    """
    Get server information including remote server details.
    """
    try:
        return {
            "service_name": "Whisper.cpp SST Broker Server",
            "version": "1.0.0",
            "broker_role": "Public IP Bridge",
            "remote_sst_server": REMOTE_SST_URL,
            "api_endpoints": {
                "inference": "POST /inference - Speech-to-text inference",
                "load": "POST /load - Load a model",
                "health": "GET /healthz - Health check",
                "info": "GET /info - Server info",
                "status": "GET /broker-status - Detailed status"
            }
        }
    except Exception as exc:
        logger.error(f"Failed to get server info: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get server information: {exc}"
        ) from exc


@app.post("/inference")
async def inference(
    file: UploadFile = File(...),
    temperature: float = Form(0.0),
    temperature_inc: float = Form(0.2),
    response_format: str = Form("json")
) -> JSONResponse:
    """
    Perform speech-to-text inference by forwarding request to remote SST server.
    
    Args:
        file: Audio file to transcribe
        temperature: Sampling temperature (0.0 - 1.0)
        temperature_inc: Temperature increment for fallback
        response_format: Response format (json, text, srt, vtt, verbose_json)
    
    Returns:
        Transcription result from remote server
    """
    try:
        # Read file content
        file_content = await file.read()
        
        logger.info(
            f"Inference request forwarded: filename={file.filename}, "
            f"size={len(file_content)} bytes, "
            f"format={response_format}"
        )
        
        # Prepare multipart data
        files = {
            "file": (file.filename, file_content, file.content_type or "audio/wav")
        }
        data = {
            "temperature": str(temperature),
            "temperature_inc": str(temperature_inc),
            "response_format": response_format
        }
        
        # Forward the request
        result = await _forward_request("POST", "/inference", files=files, data=data)
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Inference request failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed: {exc}"
        ) from exc


@app.post("/load")
async def load_model(request: LoadModelRequest) -> LoadModelResponse:
    """
    Load a model on the remote SST server.
    
    Args:
        request: LoadModelRequest containing model path
    
    Returns:
        Status of model loading
    """
    try:
        logger.info(f"Load model request forwarded: model_path={request.model_path}")
        
        # Forward the request as JSON
        request_dict = request.model_dump()
        result = await _forward_request("POST", "/load", json_data=request_dict)
        
        return LoadModelResponse(
            status=result.get("status", "success"),
            message=result.get("message", "Model loaded successfully")
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Load model request failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Load model failed: {exc}"
        ) from exc


@app.get("/broker-status")
async def broker_status() -> Dict[str, object]:
    """
    Get detailed broker status including remote server connectivity
    """
    try:
        # Test remote server connectivity
        result = await _forward_request("GET", "/")
        remote_healthy = result is not None
        
        return {
            "broker_running": True,
            "remote_server_url": REMOTE_SST_URL,
            "remote_server_reachable": remote_healthy,
            "broker_host": BROKER_HOST,
            "broker_port": BROKER_PORT,
            "request_timeout": REQUEST_TIMEOUT,
            "service": "whisper_sst_broker"
        }
    except Exception as exc:
        logger.warning(f"Remote server unreachable: {exc}")
        return {
            "broker_running": True,
            "remote_server_url": REMOTE_SST_URL,
            "remote_server_reachable": False,
            "broker_host": BROKER_HOST,
            "broker_port": BROKER_PORT,
            "request_timeout": REQUEST_TIMEOUT,
            "error": str(exc)
        }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*70)
    print("Whisper.cpp SST Broker Server Configuration")
    print("="*70)
    print(f"  Broker listening on:      {BROKER_HOST}:{BROKER_PORT}")
    print(f"  Remote SST server:        {REMOTE_SST_URL}")
    print(f"  Request timeout:          {REQUEST_TIMEOUT}s")
    print(f"  Log level:                {LOG_LEVEL_NAME}")
    print("="*70 + "\n")
    
    logger.info(
        f"Starting Whisper.cpp SST Broker Server on {BROKER_HOST}:{BROKER_PORT}\n"
        f"Forwarding requests to SST server at {REMOTE_SST_URL}"
    )
    
    uvicorn.run(
        "publicip_server_whisper_sst:app",
        host=BROKER_HOST,
        port=BROKER_PORT,
        workers=1,
        reload=False,
        log_level=LOG_LEVEL_NAME.lower()
    )
