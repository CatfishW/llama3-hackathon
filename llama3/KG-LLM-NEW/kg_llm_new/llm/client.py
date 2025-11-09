"""LLM client abstractions supporting HTTP and MQTT backends."""

from __future__ import annotations

import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Sequence, Tuple

from openai import OpenAI

from kg_llm_new.logging_utils import get_logger

LOGGER = get_logger(__name__)


class LLMMode(str, Enum):
	"""Supported communication modes."""

	HTTP = "http"
	MQTT = "mqtt"
	KG_ONLY = "kg-only"


@dataclass
class LLMClientConfig:
	"""Configuration for LLM client."""

	mode: LLMMode = LLMMode.HTTP
	server_url: str | None = None
	timeout: int = 120
	model_name: str = "default"
	project: str = "general"
	session_id: str | None = None
	client_id: str | None = None
	min_request_interval: float = 0.1
	mqtt_broker: str | None = None
	mqtt_port: int = 1883
	mqtt_username: str | None = None
	mqtt_password: str | None = None


class LLMClient:
	"""Unified client bridging HTTP llama.cpp and MQTT gateway."""

	def __init__(self, config: LLMClientConfig) -> None:
		self.config = config
		if config.mode == LLMMode.HTTP:
			if not config.server_url:
				raise ValueError("server_url required for HTTP mode")
			base_url = config.server_url.rstrip("/")
			self.client = OpenAI(base_url=base_url, api_key="not-needed")
			LOGGER.info("Initialized HTTP LLM client for %s", base_url)
		elif config.mode == LLMMode.MQTT:
			self._init_mqtt(config)
		elif config.mode == LLMMode.KG_ONLY:
			self.client = None
			LOGGER.info("Initialized KG-only mode; no external LLM backend will be used")
		else:  # pragma: no cover - defensive guard
			raise ValueError(f"Unsupported LLM mode: {config.mode}")

	# ------------------------------------------------------------------
	# HTTP path
	# ------------------------------------------------------------------
	def _generate_http(self, messages: Sequence[Dict[str, str]], **kwargs) -> str:
		response = self.client.chat.completions.create(
			model=self.config.model_name,
			messages=list(messages),
			max_tokens=kwargs.get("max_tokens", 512),
			temperature=kwargs.get("temperature", 0.1),
			top_p=kwargs.get("top_p", 0.9),
		)
		return response.choices[0].message.content or ""

	# ------------------------------------------------------------------
	# MQTT path
	# ------------------------------------------------------------------
	def _init_mqtt(self, config: LLMClientConfig) -> None:
		try:
			import paho.mqtt.client as mqtt  # type: ignore
		except ImportError as exc:  # pragma: no cover - dependency guard
			raise RuntimeError("paho-mqtt is required for MQTT mode") from exc

		if not config.mqtt_broker:
			raise ValueError("mqtt_broker required for MQTT mode")

		self.project = (config.project or "general").strip()
		if not self.project:
			raise ValueError("project cannot be empty for MQTT mode")

		# Session/client identifiers mirror the reference MQTT client
		self.session_id = config.session_id or f"session-{uuid.uuid4().hex[:8]}"
		self.client_id = config.client_id or f"kg-llm-{uuid.uuid4().hex[:8]}"
		self.user_topic = f"{self.project}/user_input"
		self.response_prefix = f"{self.project}/assistant_response/{self.session_id}/{self.client_id}"

		self._pending: Dict[str, "queue.Queue[str]"] = {}
		self._pending_lock = threading.Lock()
		self._connect_event = threading.Event()
		self._connected = False
		self._min_interval = max(config.min_request_interval, 0.0)
		self._last_request_ts = 0.0

		self._mqtt = mqtt.Client(
			client_id=self.client_id,
			callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
		)
		if config.mqtt_username and config.mqtt_password:
			self._mqtt.username_pw_set(config.mqtt_username, config.mqtt_password)

		self._mqtt.on_connect = self._on_connect
		self._mqtt.on_disconnect = self._on_disconnect
		self._mqtt.on_message = self._on_message
		self._mqtt.on_subscribe = self._on_subscribe

		# Improve resilience on flakey networks
		self._mqtt.reconnect_delay_set(min_delay=1, max_delay=60)

		LOGGER.info(
			"Connecting to MQTT broker %s:%d as %s", config.mqtt_broker, config.mqtt_port, self.client_id
		)
		self._mqtt.connect(config.mqtt_broker, config.mqtt_port, keepalive=60)
		self._mqtt.loop_start()

		if not self._connect_event.wait(timeout=config.timeout):
			raise TimeoutError("Timed out while connecting to MQTT broker")

	def _generate_mqtt(self, messages: Sequence[Dict[str, str]], **kwargs) -> str:
		system_prompt, user_message = self._extract_chat_segments(messages)
		if not user_message:
			raise ValueError("At least one user message is required for MQTT generation")

		wait = self._min_interval - (time.time() - self._last_request_ts)
		if wait > 0:
			time.sleep(wait)
		self._last_request_ts = time.time()

		request_id = uuid.uuid4().hex[:16]
		response_topic = f"{self.response_prefix}/{request_id}"
		payload = {
			"sessionId": self.session_id,
			"message": user_message,
			"replyTopic": response_topic,
			"clientId": self.client_id,
			"requestId": request_id,
		}

		if system_prompt:
			payload["systemPrompt"] = system_prompt
		if "temperature" in kwargs and kwargs["temperature"] is not None:
			payload["temperature"] = kwargs["temperature"]
		if "top_p" in kwargs and kwargs["top_p"] is not None:
			payload["topP"] = kwargs["top_p"]
		if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
			payload["maxTokens"] = kwargs["max_tokens"]

		response_queue: "queue.Queue[str]" = queue.Queue(maxsize=1)
		with self._pending_lock:
			self._pending[request_id] = response_queue

		LOGGER.debug("Publishing request %s to %s", request_id, self.user_topic)
		self._mqtt.publish(self.user_topic, json.dumps(payload), qos=0)

		try:
			return response_queue.get(timeout=self.config.timeout)
		except queue.Empty as exc:
			raise TimeoutError("Timed out waiting for MQTT response") from exc
		finally:
			with self._pending_lock:
				self._pending.pop(request_id, None)

	def _extract_chat_segments(
		self, messages: Sequence[Dict[str, str]]
	) -> Tuple[Optional[str], str]:
		system_prompt: Optional[str] = None
		last_user: Optional[str] = None
		for message in messages:
			role = message.get("role")
			content = message.get("content", "")
			if role == "system" and system_prompt is None:
				system_prompt = content
			elif role == "user":
				last_user = content
		if last_user is None and messages:
			last_user = messages[-1].get("content", "")
		return system_prompt, last_user or ""

	# ------------------------------------------------------------------
	# MQTT callbacks (mirror reference client behaviour)
	# ------------------------------------------------------------------
	def _on_connect(self, client, userdata, flags, rc, properties=None):  # pragma: no cover - callback
		if rc == 0:
			LOGGER.info("Connected to MQTT broker; subscribing to %s/#", self.response_prefix)
			self._connected = True
			client.subscribe(f"{self.response_prefix}/#", qos=1)
		else:
			LOGGER.warning("MQTT connection failed with code %s", rc)
		self._connect_event.set()

	def _on_disconnect(self, client, userdata, rc, properties=None):  # pragma: no cover - callback
		self._connected = False
		if rc != 0:
			LOGGER.warning("Unexpected MQTT disconnect (rc=%s)", rc)

	def _on_subscribe(self, client, userdata, mid, granted_qos, properties=None):  # pragma: no cover - callback
		LOGGER.debug("Subscription acknowledged (mid=%s, qos=%s)", mid, granted_qos)

	def _on_message(self, client, userdata, message):  # pragma: no cover - callback
		topic = message.topic
		if not topic.startswith(self.response_prefix):
			return
		try:
			request_id = topic.split("/")[-1]
			text = message.payload.decode("utf-8")
		except Exception as exc:  # Defensive guard against malformed payloads
			LOGGER.error("Failed to decode MQTT response: %s", exc)
			return

		with self._pending_lock:
			queue_obj = self._pending.get(request_id)
			if not queue_obj:
				LOGGER.debug("Dropping unmatched MQTT response for %s", request_id)
				return
			try:
				queue_obj.put_nowait(text)
			except queue.Full:  # pragma: no cover - defensive guard
				LOGGER.debug("Queue already satisfied for request %s", request_id)

	# ------------------------------------------------------------------
	# Public API
	# ------------------------------------------------------------------
	def generate(self, messages: Sequence[Dict[str, str]], **kwargs) -> str:
		if self.config.mode == LLMMode.HTTP:
			return self._generate_http(messages, **kwargs)
		if self.config.mode == LLMMode.MQTT:
			return self._generate_mqtt(messages, **kwargs)
		raise RuntimeError("generate() is unsupported in KG-only mode")

	def close(self) -> None:
		if self.config.mode == LLMMode.MQTT and hasattr(self, "_mqtt"):
			self._mqtt.loop_stop()
			try:
				self._mqtt.disconnect()
			except Exception:  # pragma: no cover - avoid noisy teardown errors
				pass
