import json
import uuid
import logging
import threading

import paho.mqtt.client as mqtt

class MazeLAMClient:
    """
    MQTT client to receive LAM guidance for a maze game.
    Call register_handler() for 'hint', 'path', 'break_wall', 'breaks_remaining',
    then call start().
    """

    def __init__(
        self,
        session_id: str,
        broker_host: str = "127.0.0.1",
        broker_port: int = 1883,
        mqtt_username: str = None,
        mqtt_password: str = None,
    ):
        self.session_id = session_id
        self.broker_host = broker_host
        self.broker_port = broker_port

        self.handlers = {
            "hint": None,
            "path": None,
            "break_wall": None,
            "breaks_remaining": None,
        }

        client_id = f"maze-client-{uuid.uuid4().hex[:6]}"
        self.client = mqtt.Client(client_id=client_id)
        if mqtt_username and mqtt_password:
            self.client.username_pw_set(mqtt_username, mqtt_password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def register_handler(self, key: str, fn):
        if key not in self.handlers:
            raise ValueError(f"Invalid handler key: {key}")
        self.handlers[key] = fn

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logging.error(f"LAM client failed to connect (rc={rc})")
            return
        topic = f"maze/hint/{self.session_id}"
        client.subscribe(topic)
        logging.info(f"LAM client subscribed to {topic}")

    def _on_message(self, client, userdata, msg):
        try:
            guidance = json.loads(msg.payload.decode("utf-8"))
        except Exception as e:
            logging.error(f"Failed to parse guidance: {e}")
            return

        if "hint" in guidance and self.handlers["hint"]:
            self.handlers["hint"](guidance["hint"])
        if "path" in guidance and self.handlers["path"]:
            self.handlers["path"](guidance["path"])
        if "break_wall" in guidance and self.handlers["break_wall"]:
            self.handlers["break_wall"](tuple(guidance["break_wall"]))
        if "breaks_remaining" in guidance and self.handlers["breaks_remaining"]:
            self.handlers["breaks_remaining"](guidance["breaks_remaining"])

    def start(self):
        def _run():
            logging.info(f"Connecting to MQTT {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_forever()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        logging.info("LAM client loop started in background thread.")
