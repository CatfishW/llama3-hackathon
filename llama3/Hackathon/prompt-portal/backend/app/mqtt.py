import asyncio
import json
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Deque, Dict, Optional, Set

from fastapi import WebSocket
import paho.mqtt.client as mqtt

from .config import settings
from .database import SessionLocal
from .models import ChatMessage, ChatSession
import threading

@dataclass
class _PendingResponse:
    future: asyncio.Future
    loop: asyncio.AbstractEventLoop
    session_key: str
    request_id: str
    created_at: float


# In-memory store mapping session_id -> most recent hint JSON
LAST_HINTS: Dict[str, dict] = {}

# In-memory websocket subscribers per session_id
SUBSCRIBERS: Dict[str, Set[WebSocket]] = {}

# Pending chat completions keyed by request id/session id
_CHAT_PENDING_LOCK = threading.RLock()
_CHAT_PENDING_BY_REQUEST: Dict[str, _PendingResponse] = {}
_CHAT_PENDING_BY_SESSION: Dict[str, Deque[_PendingResponse]] = {}

# Cache last assistant response per session (useful for diagnostics)
CHAT_LAST_RESPONSES: Dict[str, Dict[str, Any]] = {}


def _normalize_topic_base(pattern: Optional[str]) -> str:
    if not pattern:
        return ""
    base = pattern.replace("/#", "").replace("/+", "").rstrip("/")
    return base


HINT_TOPIC_BASE = _normalize_topic_base(getattr(settings, "MQTT_TOPIC_HINT", ""))
CHAT_RESPONSE_BASE = _normalize_topic_base(getattr(settings, "MQTT_TOPIC_ASSISTANT_RESPONSE", ""))

# Generate a unique client ID to avoid conflicts during development/reload
unique_client_id = f"{settings.MQTT_CLIENT_ID}_{uuid.uuid4().hex[:8]}"
mqtt_client = mqtt.Client(client_id=unique_client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

def _on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        # Subscribe to maze hints (if configured)
        if getattr(settings, "MQTT_TOPIC_HINT", None):
            client.subscribe(settings.MQTT_TOPIC_HINT)
            print(f"MQTT connected and subscribed to {settings.MQTT_TOPIC_HINT}")
        else:
            print("MQTT connected but no hint topic configured")

        # Subscribe to assistant responses for chat portal
        if CHAT_RESPONSE_BASE:
            client.subscribe(f"{CHAT_RESPONSE_BASE}/#", qos=1)
            client.subscribe(CHAT_RESPONSE_BASE, qos=1)
            print(f"MQTT subscribed to chat responses at {CHAT_RESPONSE_BASE}/#")
        else:
            print("Warning: MQTT assistant response topic not configured; chat features disabled")
    else:
        print(f"MQTT connection failed with code {reason_code}")

def _on_disconnect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        # Provide more detailed error information
        error_messages = {
            1: "Unacceptable protocol version",
            2: "Identifier rejected", 
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized",
            7: "Connection lost",
            8: "Protocol error"
        }
        error_msg = error_messages.get(reason_code, f"Unknown error code {reason_code}")
        print(f"Unexpected MQTT disconnection: {error_msg} (code: {reason_code})")
        print(f"Client ID was: {unique_client_id}")
    else:
        print("MQTT client disconnected normally")

def _on_message(client, userdata, msg):
    payload_text = msg.payload.decode("utf-8", errors="ignore")
    print(f"[MQTT] Received message on topic '{msg.topic}': {payload_text[:200]}...")

    topic = msg.topic

    if HINT_TOPIC_BASE and topic.startswith(HINT_TOPIC_BASE):
        _handle_hint_message(topic, payload_text)
        return

    if CHAT_RESPONSE_BASE and topic.startswith(CHAT_RESPONSE_BASE):
        _handle_chat_response(topic, payload_text)
        return

    print(f"[MQTT] Unhandled topic '{topic}'")


def _handle_hint_message(topic: str, payload_text: str) -> None:
    try:
        data = json.loads(payload_text)
    except Exception as exc:
        print(f"[MQTT] Hint JSON parse error: {exc}")
        data = {"raw": payload_text}

    parts = topic.split("/")
    session_id = parts[-1] if len(parts) >= 3 else "unknown"
    LAST_HINTS[session_id] = data

    print(f"[MQTT] Hint session ID: {session_id}, Subscribers: {len(SUBSCRIBERS.get(session_id, set()))}")

    websockets = SUBSCRIBERS.get(session_id, set()).copy()
    if not websockets:
        print(f"[MQTT] No WebSocket subscribers for hint session '{session_id}'")
        return

    message_data = json.dumps({"topic": topic, "hint": data})

    for ws in websockets:
        try:
            def send_message() -> None:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(ws.send_text(message_data))
                    loop.close()
                except Exception as send_exc:
                    print(f"[MQTT] Failed to send hint to WebSocket: {send_exc}")

            threading.Thread(target=send_message, daemon=True).start()
            print(f"[MQTT] Sent hint to WebSocket for session '{session_id}'")
        except Exception as exc:
            print(f"[MQTT] Error starting thread for WebSocket hint send: {exc}")
            SUBSCRIBERS.get(session_id, set()).discard(ws)


def _extract_chat_topic_parts(topic: str) -> tuple[str, Optional[str], Optional[str]]:
    if not CHAT_RESPONSE_BASE:
        return ("unknown", None, None)
    suffix = topic[len(CHAT_RESPONSE_BASE):].strip("/") if topic.startswith(CHAT_RESPONSE_BASE) else topic
    parts = [part for part in suffix.split("/") if part]
    session_key = parts[0] if parts else "unknown"
    client_id = parts[1] if len(parts) > 1 else None
    request_id = parts[2] if len(parts) > 2 else None
    return (session_key, client_id, request_id)


def publish_template_update(session_key: str, new_system_prompt: str) -> bool:
    """Publish a system prompt update to MQTT so llama.cpp deployment updates its session."""
    try:
        topic = getattr(settings, "MQTT_TOPIC_TEMPLATE", "prompt_portal/template")
        if not topic:
            print("[MQTT] Template topic not configured; skipping prompt update")
            return False

        payload = {
            "sessionId": session_key,
            "systemPrompt": new_system_prompt,
            "template": {"content": new_system_prompt},
            "reset": False,
        }

        result = mqtt_client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)
        if result.rc == 0:
            print(f"[MQTT] Published system prompt update for session '{session_key}'")
            return True
        else:
            print(f"[MQTT] Failed to publish prompt update (rc={result.rc})")
            return False
    except Exception as e:
        print(f"[MQTT] Error publishing template update: {e}")
        return False


def _handle_chat_response(topic: str, payload_text: str) -> None:
    session_key, client_id, request_id = _extract_chat_topic_parts(topic)

    raw_object: Any
    response_text: str
    metadata: Optional[Dict[str, Any]]

    try:
        raw_object = json.loads(payload_text)
    except json.JSONDecodeError:
        raw_object = payload_text

    if isinstance(raw_object, dict):
        metadata = raw_object
        response_text = (
            raw_object.get("response")
            or raw_object.get("content")
            or raw_object.get("hint")
            or payload_text
        )
    elif isinstance(raw_object, str):
        metadata = {"response": raw_object}
        response_text = raw_object
    else:
        metadata = None
        response_text = payload_text

    print(
        f"[MQTT] Chat response for session '{session_key}' (client={client_id}, request={request_id})"
    )

    message_payload = {
        "session_key": session_key,
        "client_id": client_id,
        "request_id": request_id,
        "topic": topic,
        "content": response_text,
        "raw": metadata,
    }

    # Persist to database if the session exists
    db = SessionLocal()
    try:
        session_obj = (
            db.query(ChatSession)
            .filter(ChatSession.session_key == session_key)
            .first()
        )

        if session_obj:
            chat_message = ChatMessage(
                session_id=session_obj.id,
                role="assistant",
                content=response_text,
                metadata_json=json.dumps(metadata) if isinstance(metadata, dict) else None,
                request_id=request_id,
            )
            session_obj.message_count = (session_obj.message_count or 0) + 1
            session_obj.updated_at = datetime.utcnow()
            session_obj.last_used_at = datetime.utcnow()
            db.add(chat_message)
            db.commit()
            db.refresh(chat_message)
            db.refresh(session_obj)

            message_payload["assistant_message"] = {
                "id": chat_message.id,
                "session_id": chat_message.session_id,
                "role": chat_message.role,
                "content": chat_message.content,
                "metadata": metadata if isinstance(metadata, dict) else None,
                "request_id": chat_message.request_id,
                "created_at": chat_message.created_at.isoformat(),
            }
            message_payload["session"] = {
                "id": session_obj.id,
                "message_count": session_obj.message_count,
                "updated_at": session_obj.updated_at.isoformat(),
                "last_used_at": session_obj.last_used_at.isoformat(),
            }
        else:
            db.rollback()
            print(f"[MQTT] Chat session '{session_key}' not found in database")
    except Exception as exc:
        db.rollback()
        print(f"[MQTT] Failed to persist chat response: {exc}")
    finally:
        db.close()

    CHAT_LAST_RESPONSES[session_key] = message_payload

    # Resolve pending futures awaiting this response
    pending: Optional[_PendingResponse] = None
    with _CHAT_PENDING_LOCK:
        if request_id and request_id in _CHAT_PENDING_BY_REQUEST:
            pending = _CHAT_PENDING_BY_REQUEST.pop(request_id, None)
            if pending:
                queue = _CHAT_PENDING_BY_SESSION.get(pending.session_key)
                if queue:
                    try:
                        queue.remove(pending)
                    except ValueError:
                        pass
                    if not queue:
                        _CHAT_PENDING_BY_SESSION.pop(pending.session_key, None)
        else:
            queue = _CHAT_PENDING_BY_SESSION.get(session_key)
            if queue:
                pending = queue.popleft()
                _CHAT_PENDING_BY_REQUEST.pop(pending.request_id, None)
                if not queue:
                    _CHAT_PENDING_BY_SESSION.pop(session_key, None)

    if pending and not pending.future.done():
        pending.loop.call_soon_threadsafe(pending.future.set_result, message_payload)
    elif not pending:
        print(f"[MQTT] No pending caller for session '{session_key}' (request={request_id})")

def start_mqtt():
    mqtt_client.on_connect = _on_connect
    mqtt_client.on_disconnect = _on_disconnect
    mqtt_client.on_message = _on_message
    
    # Set up authentication
    if hasattr(settings, 'MQTT_USERNAME') and hasattr(settings, 'MQTT_PASSWORD'):
        mqtt_client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        print(f"MQTT authentication configured for user: {settings.MQTT_USERNAME}")
    
    print(f"Connecting to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
    print(f"Using client ID: {unique_client_id}")
    
    try:
        mqtt_client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, 60)
        mqtt_client.loop_start()
        print("MQTT loop started successfully")
    except Exception as e:
        print(f"Failed to start MQTT connection: {e}")

def stop_mqtt():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

def publish_state(state: dict):
    # Publish to 'maze/state' by default
    mqtt_client.publish(settings.MQTT_TOPIC_STATE, json.dumps(state), qos=0, retain=False)

def publish_template(template_payload: dict, session_id: str | None = None):
    """Publish a template update to the LAM over MQTT. If session_id is provided, target that session."""
    topic = settings.MQTT_TOPIC_TEMPLATE
    if session_id:
        # allow per-session override by suffixing session id
        if not topic.endswith("/"):
            topic = topic + "/" + session_id
        else:
            topic = topic + session_id
    mqtt_client.publish(topic, json.dumps(template_payload), qos=0, retain=False)


async def send_chat_message(payload: Dict[str, Any], timeout: float = 45.0) -> Dict[str, Any]:
    """Publish a chat message via MQTT and wait for the assistant response."""
    if not getattr(settings, "MQTT_TOPIC_USER_INPUT", None):
        raise RuntimeError("MQTT_TOPIC_USER_INPUT is not configured")
    if not CHAT_RESPONSE_BASE:
        raise RuntimeError("MQTT_TOPIC_ASSISTANT_RESPONSE is not configured")

    session_key = str(payload.get("sessionId") or "").strip()
    if not session_key:
        raise ValueError("payload.sessionId is required")

    request_id = str(payload.get("requestId") or uuid.uuid4().hex[:12])
    payload["requestId"] = request_id
    payload["clientId"] = unique_client_id

    reply_topic = payload.get("replyTopic")
    if not isinstance(reply_topic, str) or not reply_topic.strip():
        reply_topic = f"{CHAT_RESPONSE_BASE}/{session_key}/{unique_client_id}/{request_id}"
        payload["replyTopic"] = reply_topic

    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    pending = _PendingResponse(
        future=future,
        loop=loop,
        session_key=session_key,
        request_id=request_id,
        created_at=time.time(),
    )

    with _CHAT_PENDING_LOCK:
        _CHAT_PENDING_BY_REQUEST[request_id] = pending
        _CHAT_PENDING_BY_SESSION.setdefault(session_key, deque()).append(pending)

    message = json.dumps(payload, ensure_ascii=False)
    result = mqtt_client.publish(settings.MQTT_TOPIC_USER_INPUT, message, qos=0)

    if result.rc != 0:
        with _CHAT_PENDING_LOCK:
            _CHAT_PENDING_BY_REQUEST.pop(request_id, None)
            queue = _CHAT_PENDING_BY_SESSION.get(session_key)
            if queue:
                try:
                    queue.remove(pending)
                except ValueError:
                    pass
                if not queue:
                    _CHAT_PENDING_BY_SESSION.pop(session_key, None)
        raise RuntimeError(f"Failed to publish chat message via MQTT (rc={result.rc})")

    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        with _CHAT_PENDING_LOCK:
            _CHAT_PENDING_BY_REQUEST.pop(request_id, None)
            queue = _CHAT_PENDING_BY_SESSION.get(session_key)
            if queue:
                try:
                    queue.remove(pending)
                except ValueError:
                    pass
                if not queue:
                    _CHAT_PENDING_BY_SESSION.pop(session_key, None)
        raise
