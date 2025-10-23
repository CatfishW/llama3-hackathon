"""
Example MQTT Client for vLLM Deployment

This script demonstrates how to interact with the vLLM deployment service.
You can use it to test the deployment and as a reference for building your own clients.

Usage:
    python vllm_test_client.py --project maze --session my_session
"""

import json
import time
import uuid
from typing import Optional

import fire
import paho.mqtt.client as mqtt


class vLLMClient:
    """Simple client for interacting with vLLM MQTT deployment."""
    
    def __init__(
        self,
        broker: str = "47.89.252.2",
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize MQTT client.
        
        Args:
            broker: MQTT broker address
            port: MQTT broker port
            username: MQTT username (optional)
            password: MQTT password (optional)
        """
        self.broker = broker
        self.port = port
        self.connected = False
        self.responses = {}
        
        # Create MQTT client
        client_id = f"vllm-test-{uuid.uuid4().hex[:8]}"
        self.client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        
        # Set authentication if provided
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for connection."""
        if rc == 0:
            print(f"✓ Connected to MQTT broker at {self.broker}:{self.port}")
            self.connected = True
        else:
            print(f"✗ Failed to connect to MQTT broker, code: {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback for disconnection."""
        self.connected = False
        if rc != 0:
            print(f"✗ Unexpected disconnect from MQTT broker, code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for incoming messages."""
        session_id = msg.topic.split('/')[-1]
        response = msg.payload.decode('utf-8')
        
        if session_id not in self.responses:
            self.responses[session_id] = []
        self.responses[session_id].append(response)
        
        print(f"\n🤖 Assistant: {response}\n")
    
    def connect(self):
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 5
            start = time.time()
            while not self.connected and time.time() - start < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                raise Exception("Connection timeout")
            
            return True
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()
    
    def send_message(
        self,
        project: str,
        session_id: str,
        message: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Send a message to the vLLM service.
        
        Args:
            project: Project name (maze, driving, bloodcell, racing, general)
            session_id: Session identifier
            message: User message
            temperature: Sampling temperature (optional)
            top_p: Top-p sampling (optional)
            max_tokens: Maximum tokens to generate (optional)
        """
        # Subscribe to response topic
        response_topic = f"{project}/assistant_response/{session_id}"
        self.client.subscribe(response_topic, qos=1)
        
        # Prepare payload
        payload = {
            "sessionId": session_id,
            "message": message
        }
        
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["topP"] = top_p
        if max_tokens is not None:
            payload["maxTokens"] = max_tokens
        
        # Send message
        user_topic = f"{project}/user_input"
        self.client.publish(user_topic, json.dumps(payload), qos=1)
        
        print(f"👤 You: {message}")
    
    def chat(
        self,
        project: str = "general",
        session_id: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Start an interactive chat session.
        
        Args:
            project: Project name
            session_id: Session identifier (auto-generated if not provided)
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens to generate
        """
        if not session_id:
            session_id = f"user-{uuid.uuid4().hex[:8]}"
        
        print("=" * 60)
        print(f"vLLM Chat Client")
        print(f"Project: {project}")
        print(f"Session: {session_id}")
        print("=" * 60)
        print("Type your message and press Enter.")
        print("Type 'exit' or 'quit' to end the session.")
        print("=" * 60)
        print()
        
        # Connect to broker
        if not self.connect():
            return
        
        try:
            while True:
                # Get user input
                user_input = input("👤 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\nGoodbye!")
                    break
                
                # Send message
                self.send_message(
                    project=project,
                    session_id=session_id,
                    message=user_input,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens
                )
                
                # Wait for response (with timeout)
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            self.disconnect()


def main(
    project: str = "general",
    session: Optional[str] = None,
    broker: str = "47.89.252.2",
    port: int = 1883,
    username: Optional[str] = None,
    password: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
):
    """
    Start an interactive chat session with the vLLM deployment.
    
    Args:
        project: Project name (maze, driving, bloodcell, racing, general)
        session: Session identifier (auto-generated if not provided)
        broker: MQTT broker address
        port: MQTT broker port
        username: MQTT username (optional)
        password: MQTT password (optional)
        temperature: Sampling temperature (optional)
        top_p: Top-p sampling (optional)
        max_tokens: Maximum tokens to generate (optional)
    
    Examples:
        # Start a general chat
        python vllm_test_client.py
        
        # Chat with the driving project
        python vllm_test_client.py --project driving --session my_session
        
        # With custom parameters
        python vllm_test_client.py --project maze --temperature 0.8 --max_tokens 256
        
        # With authentication
        python vllm_test_client.py --project bloodcell --username user --password pass
    """
    client = vLLMClient(broker, port, username, password)
    client.chat(project, session, temperature, top_p, max_tokens)


if __name__ == "__main__":
    fire.Fire(main)
