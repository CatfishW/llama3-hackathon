import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
import paho.mqtt.client as mqtt
from .config import settings
import threading

# In-memory store mapping session_id -> most recent hint JSON
LAST_HINTS: Dict[str, dict] = {}

# In-memory websocket subscribers per session_id
SUBSCRIBERS: Dict[str, Set[WebSocket]] = {}

mqtt_client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

def _on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        # Subscribe to hints
        client.subscribe(settings.MQTT_TOPIC_HINT)
        print(f"MQTT connected and subscribed to {settings.MQTT_TOPIC_HINT}")
    else:
        print(f"MQTT connection failed with code {reason_code}")

def _on_disconnect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        print(f"Unexpected MQTT disconnection: {reason_code}")

def _on_message(client, userdata, msg):
    print(f"[MQTT] Received message on topic '{msg.topic}': {msg.payload.decode('utf-8')[:200]}...")
    
    try:
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
    except Exception as e:
        print(f"[MQTT] JSON parse error: {e}")
        data = {"raw": msg.payload.decode("utf-8", errors="ignore")}

    # sessionId extraction: expecting topic like maze/hint/{sessionId}
    topic = msg.topic
    parts = topic.split("/")
    session_id = parts[-1] if len(parts) >= 3 else "unknown"
    LAST_HINTS[session_id] = data

    print(f"[MQTT] Session ID: {session_id}, Subscribers: {len(SUBSCRIBERS.get(session_id, set()))}")

    # Broadcast to all websocket subscribers for this session
    websockets = SUBSCRIBERS.get(session_id, set()).copy()
    if not websockets:
        print(f"[MQTT] No WebSocket subscribers for session '{session_id}'")
        return
        
    message_data = json.dumps({"topic": topic, "hint": data})
    for ws in websockets:
        try:
            # Use threading to handle the async call from sync context
            def send_message():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(ws.send_text(message_data))
                    loop.close()
                except Exception as e:
                    print(f"[MQTT] Failed to send message to WebSocket: {e}")
            
            threading.Thread(target=send_message, daemon=True).start()
            print(f"[MQTT] Sent message to WebSocket for session '{session_id}'")
        except Exception as e:
            print(f"[MQTT] Error starting thread for WebSocket send: {e}")
            # Remove broken WebSocket
            SUBSCRIBERS.get(session_id, set()).discard(ws)

def start_mqtt():
    mqtt_client.on_connect = _on_connect
    mqtt_client.on_disconnect = _on_disconnect
    mqtt_client.on_message = _on_message
    
    # Set up authentication
    if hasattr(settings, 'MQTT_USERNAME') and hasattr(settings, 'MQTT_PASSWORD'):
        mqtt_client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        print(f"MQTT authentication configured for user: {settings.MQTT_USERNAME}")
    
    print(f"Connecting to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
    mqtt_client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, 60)
    mqtt_client.loop_start()

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
