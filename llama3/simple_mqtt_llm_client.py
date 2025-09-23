"""
Simple MQTT client for your LLM service.

What it does:
- Connects to the MQTT broker
- Creates a new chat session
- Sends a user prompt
- Waits for and returns the assistant response

Beginner-friendly usage:
    from simple_mqtt_llm_client import LLMClient

    client = LLMClient(username="<mqtt_user>", password="<mqtt_pass>")
    session_id = client.create_session()
    reply = client.send("Hello! Please help me understand RBCs.", session_id=session_id)
    print("Assistant:", reply)
    client.close()

Notes:
- The server resets the dialog when it receives an empty message.
- You can call client.reset(session_id) to clear the conversation state.
"""

from __future__ import annotations

import uuid
import time
import threading
import contextlib
from typing import Dict, Optional
import os

import paho.mqtt.client as mqtt


DEFAULT_BROKER = "47.89.252.2"
DEFAULT_PORT = 1883
USER_TOPIC = "llama/user_input"
ASSISTANT_TOPIC = "llama/assistant_response"
SESSION_TOPIC = "llama/session"
SESSION_RESPONSE_TOPIC = f"{SESSION_TOPIC}/response"


class LLMClient:
    """Minimal MQTT client for the LLM service.

    Contract:
    - connect() happens in __init__ (loop runs in the background)
    - create_session(timeout) -> session_id
    - send(prompt, session_id, timeout) -> assistant response (str)
    - reset(session_id, timeout) -> reset ack text
    - close() -> stop background loop and disconnect
    """

    def __init__(
        self,
        broker: str = DEFAULT_BROKER,
        port: int = DEFAULT_PORT,
        username: Optional[str] = None,
        password: Optional[str] = None,
        keepalive: int = 60,
        connect_timeout: float = 10.0,
    ) -> None:
        # Allow env overrides for convenience/safety
        env_broker = os.getenv("MQTT_BROKER")
        env_port = os.getenv("MQTT_PORT")
        env_user = os.getenv("MQTT_USERNAME")
        env_pass = os.getenv("MQTT_PASSWORD")

        self._broker = env_broker or broker
        try:
            self._port = int(env_port) if env_port else port
        except ValueError:
            self._port = port

        self._username = username if username is not None else env_user
        self._password = password if password is not None else env_pass
        self._keepalive = keepalive

        # Queues/state
        self._session_queue = _SimpleQueue(maxsize=10)
        self._response_queues: Dict[str, _SimpleQueue] = {}
        self._resp_lock = threading.Lock()
        self._connected = threading.Event()

        # MQTT client
        client_id = f"llm-client-{uuid.uuid4().hex[:8]}"
        self._client = mqtt.Client(client_id=client_id)
        if self._username is not None and self._password is not None:
            self._client.username_pw_set(self._username, self._password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        # Connect and start loop
        self._client.connect(self._broker, self._port, self._keepalive)
        self._client.loop_start()

        # Wait for connection
        if not self._connected.wait(timeout=connect_timeout):
            raise TimeoutError("MQTT connect timeout")

    # ------------------- Public API -------------------
    def create_session(self, timeout: float = 5.0) -> str:
        """Request a new session ID from the server."""
        # Publish any payload (server only checks topic)
        self._client.publish(SESSION_TOPIC, payload="new")
        session_id = self._session_queue.get(timeout=timeout)
        return session_id

    def send(self, prompt: str, session_id: Optional[str] = None, timeout: float = 30.0) -> str:
        """Send a user prompt and wait for the assistant's reply.

        If no session_id is provided, a new session is created automatically.
        """
        if session_id is None:
            session_id = self.create_session()

        q = self._get_or_create_response_queue(session_id)
        self._client.publish(f"{USER_TOPIC}/{session_id}", payload=str(prompt))
        return q.get(timeout=timeout)

    def reset(self, session_id: str, timeout: float = 5.0) -> str:
        """Reset the dialog for this session (server responds with a short ack)."""
        q = self._get_or_create_response_queue(session_id)
        self._client.publish(f"{USER_TOPIC}/{session_id}", payload="")
        return q.get(timeout=timeout)

    def close(self) -> None:
        try:
            self._client.loop_stop()
        finally:
            with contextlib.suppress(Exception):
                self._client.disconnect()

    # ------------------- MQTT callbacks -------------------
    def _on_connect(self, client, userdata, flags, rc):  # noqa: D401
        # 0 means success
        if rc == 0:
            # Subscribe when connected
            client.subscribe([(SESSION_RESPONSE_TOPIC, 0), (f"{ASSISTANT_TOPIC}/#", 0)])
            self._connected.set()

    def _on_disconnect(self, client, userdata, rc):  # noqa: D401
        # Keep it quiet for simplicity; reconnection is handled by paho if you call reconnect
        pass

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="replace")

        if topic == SESSION_RESPONSE_TOPIC:
            # New session id
            self._session_queue.put(payload)
            return

        if topic.startswith(f"{ASSISTANT_TOPIC}/"):
            session_id = topic.split("/", 2)[-1]
            q = self._get_or_create_response_queue(session_id)
            q.put(payload)

    # ------------------- Internals -------------------
    def _get_or_create_response_queue(self, session_id: str) -> "_SimpleQueue":
        with self._resp_lock:
            q = self._response_queues.get(session_id)
            if q is None:
                q = _SimpleQueue(maxsize=5)
                self._response_queues[session_id] = q
            return q


class _SimpleQueue:
    """Tiny blocking queue using Events; avoids bringing full queue.Queue for clarity."""

    def __init__(self, maxsize: int = 10):
        self._maxsize = maxsize
        self._items = []  # type: list[str]
        self._event = threading.Event()
        self._lock = threading.Lock()

    def put(self, item: str) -> None:
        with self._lock:
            if len(self._items) >= self._maxsize:
                # Drop the oldest to keep it simple
                self._items.pop(0)
            self._items.append(item)
            self._event.set()

    def get(self, timeout: Optional[float] = None) -> str:
        if not self._event.wait(timeout=timeout):
            raise TimeoutError("Timed out waiting for message")
        with self._lock:
            value = self._items.pop(0)
            if not self._items:
                self._event.clear()
            return value

if __name__ == "__main__":
    # Tiny demo that works well for beginners
    import contextlib
    import getpass

    print("Connecting to the LLM service over MQTT…")


    client = LLMClient(username="TangClinic", password="Tang123")
    try:
        sid = client.create_session() 
        print(f"Session: {sid}")  
        while True:
            prompt = input("You: ").strip()
            if prompt.lower() in {"/quit", ":q", "exit"}:
                break
            if prompt.lower() in {"/reset", ":r"}:
                print("Resetting session…")
                print("Assistant:", client.reset(sid))
                continue
            reply = client.send(prompt, session_id=sid)
            print("Assistant:", reply)
    finally:
        client.close()
