from fastapi import APIRouter
from datetime import datetime
import time

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("/")
async def health_check():
    """Health check endpoint to monitor backend and MQTT connection status"""
    from ..mqtt import mqtt_client, _mqtt_last_activity, _mqtt_reconnect_attempts
    from .. import mqtt
    
    mqtt_connected = mqtt_client.is_connected() if mqtt_client else False
    time_since_activity = time.time() - _mqtt_last_activity
    
    # Determine overall health status
    status = "healthy"
    issues = []
    
    if not mqtt_connected:
        status = "unhealthy"
        issues.append("MQTT disconnected")
    elif time_since_activity > 300:  # No activity for 5+ minutes
        status = "degraded"
        issues.append(f"No MQTT activity for {time_since_activity:.0f}s")
    
    if _mqtt_reconnect_attempts > 0:
        issues.append(f"Recent reconnection attempts: {_mqtt_reconnect_attempts}")
        if status == "healthy":
            status = "degraded"
    
    # Count pending requests
    with mqtt._CHAT_PENDING_LOCK:
        pending_requests = len(mqtt._CHAT_PENDING_BY_REQUEST)
    
    if pending_requests > 50:
        issues.append(f"High number of pending requests: {pending_requests}")
        if status == "healthy":
            status = "degraded"
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "mqtt": {
            "connected": mqtt_connected,
            "last_activity_seconds_ago": round(time_since_activity, 1),
            "reconnect_attempts": _mqtt_reconnect_attempts,
            "pending_requests": pending_requests
        },
        "issues": issues if issues else None
    }

@router.get("/mqtt")
async def mqtt_health():
    """Detailed MQTT connection health information"""
    from ..mqtt import mqtt_client, _mqtt_last_activity, _mqtt_reconnect_attempts, unique_client_id
    from .. import mqtt
    
    mqtt_connected = mqtt_client.is_connected() if mqtt_client else False
    time_since_activity = time.time() - _mqtt_last_activity
    
    with mqtt._CHAT_PENDING_LOCK:
        pending_by_request = len(mqtt._CHAT_PENDING_BY_REQUEST)
        pending_by_session = {k: len(v) for k, v in mqtt._CHAT_PENDING_BY_SESSION.items()}
    
    return {
        "connected": mqtt_connected,
        "client_id": unique_client_id,
        "last_activity": {
            "timestamp": datetime.fromtimestamp(_mqtt_last_activity).isoformat(),
            "seconds_ago": round(time_since_activity, 1)
        },
        "reconnection": {
            "attempts": _mqtt_reconnect_attempts,
            "max_attempts": mqtt._mqtt_max_reconnect_attempts
        },
        "pending_requests": {
            "total": pending_by_request,
            "by_session": pending_by_session
        },
        "subscribers": {
            "hint_sessions": len(mqtt.SUBSCRIBERS),
            "total_websockets": sum(len(ws_set) for ws_set in mqtt.SUBSCRIBERS.values())
        }
    }
