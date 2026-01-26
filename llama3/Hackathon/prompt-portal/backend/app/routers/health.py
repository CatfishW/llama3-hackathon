from fastapi import APIRouter
from datetime import datetime

from ..services.llm_client import get_llm_client

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("/")
async def health_check():
    """Health check endpoint to monitor backend and LLM readiness"""
    status = "healthy"
    issues = []

    llm_info = {"available": True}
    try:
        client = get_llm_client()
        llm_info.update({
            "server_url": client.server_url,
            "backend_type": client.backend_type
        })
    except Exception as exc:
        status = "degraded"
        llm_info["available"] = False
        issues.append(f"LLM service not initialized: {exc}")

    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "llm": llm_info,
        "issues": issues if issues else None
    }
