"""LLM client abstractions supporting HTTP and MQTT backends."""

from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Optional, Sequence

from openai import OpenAI

from kg_llm_new.logging_utils import get_logger

LOGGER = get_logger(__name__)


class LLMMode(str, Enum):
    """Supported communication modes."""

    HTTP = "http"
    MQTT = "mqtt"


@dataclass
class LLMClientConfig:
    """Configuration for LLM client."""

    mode: LLMMode = LLMMode.HTTP
    server_url: str | None = None
    timeout: int = 120
    mqtt_broker: str | None = None
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_request_topic: str = "kg_llm_new/request"
    mqtt_response_topic: str = "kg_llm_new/response"


class LLMClient:
    """Unified client bridging HTTP llama.cpp and MQTT gateway."""

    def __init__(self, config: LLMClientConfig) -> None:
        self.config = config
        if config.mode == LLMMode.HTTP:
            if not config.server_url:
                raise ValueError("server_url required for HTTP mode")
            self.client = OpenAI(base_url=config.server_url.rstrip("/"), api_key="not-needed")
            LOGGER.info("Initialized HTTP LLM client for %s", config.server_url)
        elif config.mode == LLMMode.MQTT:
            try:
                import paho.mqtt.client as mqtt  # type: ignore
            except ImportError as exc:  # pragma: no cover - dependency guard
                raise RuntimeError("paho-mqtt is required for MQTT mode") from exc
            if not config.mqtt_broker:
                raise ValueError("mqtt_broker required for MQTT mode")
            self._mqtt = mqtt.Client()
            if config.mqtt_username and config.mqtt_password:
                self._mqtt.username_pw_set(config.mqtt_username, config.mqtt_password)
            self._response_queue: "queue.Queue[str]" = queue.Queue(maxsize=1)
            self._mqtt.on_message = self._on_message
            self._mqtt.connect(config.mqtt_broker, config.mqtt_port, keepalive=60)
            self._mqtt.subscribe(config.mqtt_response_topic)
            self._mqtt.loop_start()
            LOGGER.info(
                "Initialized MQTT LLM client for broker %s:%d",
                config.mqtt_broker,
                config.mqtt_port,
            )
        else:
            raise ValueError(f"Unsupported LLM mode: {config.mode}")

    def generate(self, messages: Sequence[Dict[str, str]], **kwargs) -> str:
        """Generate response text."""

        if self.config.mode == LLMMode.HTTP:
            response = self.client.chat.completions.create(
                model="default",
                messages=list(messages),
                max_tokens=kwargs.get("max_tokens", 512),
                temperature=kwargs.get("temperature", 0.1),
                top_p=kwargs.get("top_p", 0.9),
            )
            return response.choices[0].message.content or ""

        # MQTT mode: publish request and wait for response
        payload = json.dumps({"messages": list(messages), "params": kwargs})
        self._mqtt.publish(self.config.mqtt_request_topic, payload, qos=0)
        try:
            return self._response_queue.get(timeout=self.config.timeout)
        except queue.Empty as exc:
            raise TimeoutError("Timed out waiting for MQTT response") from exc

    # ------------------------------------------------------------------
    # MQTT callback handlers
    # ------------------------------------------------------------------
    def _on_message(self, client, userdata, message) -> None:  # pragma: no cover - callback
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            text = payload.get("content") or ""
            self._response_queue.put_nowait(text)
        except Exception as exc:
            LOGGER.error("Failed to decode MQTT response: %s", exc)

    def close(self) -> None:
        if self.config.mode == LLMMode.MQTT and hasattr(self, "_mqtt"):
            self._mqtt.loop_stop()
            self._mqtt.disconnect()
