import asyncio
import json
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

from .config import settings


@dataclass
class _Pending:
    future: asyncio.Future
    session_key: str
    request_id: str
    created_at: float


unique_client_id = f"{settings.MQTT_CLIENT_ID}_{uuid.uuid4().hex[:8]}"
client = mqtt.Client(client_id=unique_client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

# Connection state tracking
_connected_event = threading.Event()
_stop_heartbeat = threading.Event()

_pending_by_request: dict[str, _Pending] = {}


def _on_connect(c, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        # Subscribe to assistant responses with proper wildcard pattern
        # Pattern: owogpt/assistant_response/{sessionId}/{clientId}/{requestId}
        base = settings.MQTT_TOPIC_ASSISTANT_RESPONSE.rstrip("/")
        c.subscribe(f"{base}/#", qos=1)
        _connected_event.set()
        print(f"[MQTT] Connected. Subscribed to {base}/#")
    else:
        print(f"[MQTT] Connect failed: {reason_code}")


def _on_message(c, userdata, msg):
    payload_text = msg.payload.decode("utf-8", errors="ignore")
    print(f"[MQTT] Received on {msg.topic}: {payload_text[:100]}...")
    
    # Extract request_id from topic: owogpt/assistant_response/{sessionId}/{clientId}/{requestId}
    topic_parts = msg.topic.split('/')
    req_id_from_topic = topic_parts[-1] if len(topic_parts) >= 5 else None
    
    try:
        data = json.loads(payload_text)
    except json.JSONDecodeError:
        data = {"response": payload_text}

    # Try to get request_id from payload or topic
    req_id = None
    if isinstance(data, dict):
        req_id = data.get("requestId") or data.get("request_id")
    if not req_id:
        req_id = req_id_from_topic

    if req_id and req_id in _pending_by_request:
        pending = _pending_by_request.pop(req_id)
        if not pending.future.done():
            pending.future.get_loop().call_soon_threadsafe(pending.future.set_result, data)
            print(f"[MQTT] Resolved request {req_id}")


def _on_disconnect(c, userdata, flags, reason_code, properties=None):
    # Mark as disconnected; loop_start with reconnect_delay will try to recover.
    _connected_event.clear()
    print(f"[MQTT] Disconnected (reason={reason_code}). Will attempt to reconnect automatically...")


def start() -> None:
    # Configure callbacks
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.on_disconnect = _on_disconnect

    # Make reconnection more resilient
    # Retry and backoff settings
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    try:
        client.max_inflight_messages_set(50)
        client.max_queued_messages_set(1000)
        client.enable_logger()
    except Exception:
        # Some versions may not have these APIs; ignore
        pass

    # Auth if present
    if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
        client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

    # LWT (optional): publish offline status if we drop unexpectedly
    try:
        will_topic = f"{settings.MQTT_TOPIC_USER_INPUT.rsplit('/', 1)[0]}/status"
        client.will_set(will_topic, payload=json.dumps({"clientId": unique_client_id, "status": "offline"}), qos=1, retain=False)
    except Exception:
        pass

    # Start network loop and connect asynchronously so it can auto-reconnect
    try:
        client.connect_async(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
        client.loop_start()
        print(f"[MQTT] Connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT} ...")
    except Exception as e:
        # Don't crash the API if MQTT broker is not available in dev
        print(f"[MQTT] Failed to start MQTT loop: {e}. Continuing without MQTT.")

    # Start a lightweight heartbeat publisher to keep the connection fresh
    def _heartbeat():
        topic_base = settings.MQTT_TOPIC_USER_INPUT.rsplit('/', 1)[0]
        hb_topic = f"{topic_base}/heartbeat/{unique_client_id}"
        while not _stop_heartbeat.is_set():
            if _connected_event.is_set():
                try:
                    client.publish(hb_topic, json.dumps({"ts": int(time.time())}), qos=0)
                except Exception:
                    pass
            _stop_heartbeat.wait(30)

    threading.Thread(target=_heartbeat, name="mqtt-heartbeat", daemon=True).start()


def stop() -> None:
    _stop_heartbeat.set()
    client.loop_stop()
    client.disconnect()


async def publish_chat(payload: Dict[str, Any], timeout: float = 45.0) -> Dict[str, Any]:
    session_id = payload.get("sessionId")
    if not session_id:
        raise ValueError("sessionId required")

    req_id = str(payload.get("requestId") or uuid.uuid4().hex[:16])
    payload["requestId"] = req_id
    payload["clientId"] = unique_client_id
    
    # Set replyTopic following the pattern: owogpt/assistant_response/{sessionId}/{clientId}/{requestId}
    base = settings.MQTT_TOPIC_ASSISTANT_RESPONSE.rstrip("/")
    reply_topic = f"{base}/{session_id}/{unique_client_id}/{req_id}"
    payload["replyTopic"] = reply_topic

    message = json.dumps(payload, ensure_ascii=False)
    print(f"[MQTT] Publishing to {settings.MQTT_TOPIC_USER_INPUT}, reply expected at {reply_topic}")

    # Ensure we're connected (or wait briefly for reconnection)
    if not _connected_event.wait(timeout=5):
        print("[MQTT] Broker not connected yet; will attempt publish with retries...")

    # Try to publish with small retries if initial attempt fails due to transient disconnect
    last_err: Optional[str] = None
    for attempt in range(5):
        result = client.publish(settings.MQTT_TOPIC_USER_INPUT, message, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            break
        last_err = f"rc={result.rc}"
        await asyncio.sleep(min(1 + attempt, 5))
    else:
        raise RuntimeError(f"Failed to publish after retries ({last_err})")

    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()
    _pending_by_request[req_id] = _Pending(future=fut, session_key=session_id, request_id=req_id, created_at=time.time())

    try:
        data = await asyncio.wait_for(fut, timeout=timeout)
        return {
            "request_id": req_id,
            "raw": data,
            "content": (data.get("response") or data.get("content") or data.get("hint") if isinstance(data, dict) else data),
        }
    except asyncio.TimeoutError:
        _pending_by_request.pop(req_id, None)
        raise


def publish_template_update(session_key: str, system_prompt: str, reset: bool = True) -> None:
    """
    Publish template update to MQTT.
    
    Args:
        session_key: Session identifier
        system_prompt: New system prompt
        reset: If True, clears conversation history on MQTT side
    """
    payload = {
        "sessionId": session_key,
        "systemPrompt": system_prompt,
        "template": {"content": system_prompt},
        "reset": reset,
    }
    topic = settings.MQTT_TOPIC_TEMPLATE
    client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)
    print(f"[MQTT] Published template update to {topic}, reset={reset}")


def publish_session_delete(session_key: str) -> None:
    """
    Publish session deletion message to MQTT to clear server-side history.
    
    Args:
        session_key: Session identifier to delete
    """
    # Try to determine delete topic from template topic
    # Following pattern: prompt_portal/delete_session
    base = settings.MQTT_TOPIC_TEMPLATE.rsplit('/', 1)[0]
    delete_topic = f"{base}/delete_session/{session_key}"
    
    payload = {
        "sessionId": session_key,
        "target": session_key,
    }
    client.publish(delete_topic, json.dumps(payload, ensure_ascii=False), qos=1)
    print(f"[MQTT] Published session delete to {delete_topic}")


