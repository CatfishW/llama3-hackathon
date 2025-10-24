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
        password: Optional[str] = None,
        min_request_interval: float = 0.1  # Minimum seconds between requests (reduced from 0.5)
    ):
        """
        Initialize MQTT client.
        
        Args:
            broker: MQTT broker address
            port: MQTT broker port
            username: MQTT username (optional)
            password: MQTT password (optional)
            min_request_interval: Minimum seconds between requests (rate limiting)
        """
        self.broker = broker
        self.port = port
        self.connected = False
        self.responses = {}
        self._subscriptions = set()
        self.waiting_for_response = False
        self.current_session = None
        self.min_request_interval = min_request_interval
        self.last_request_time = 0.0
        
        # Create MQTT client
        client_id = f"vllm-test-{uuid.uuid4().hex[:8]}"
        self.client_id = client_id
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
            print(f"✅ Connected to MQTT broker at {self.broker}:{self.port}\n")
            self.connected = True
        else:
            print(f"❌ Failed to connect to MQTT broker, code: {rc}\n")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback for disconnection."""
        self.connected = False
        if rc != 0:
            print(f"\n⚠️  Unexpected disconnect from MQTT broker, code: {rc}\n")
    
    def _on_message(self, client, userdata, msg):
        """Callback for incoming messages."""
        topic_parts = msg.topic.split('/')

        session_id = topic_parts[-1]
        client_segment = None

        # Expected topic layout: <project>/assistant_response/<session>/<client>
        if len(topic_parts) >= 4:
            client_segment = topic_parts[-1]
            session_id = topic_parts[-2]

        # Drop responses that do not target this client instance
        if client_segment and client_segment != self.client_id:
            return
        response = msg.payload.decode('utf-8')
        
        # Only process if this is the current session to avoid duplicates
        if session_id != self.current_session:
            return
        
        # Check if we've already received this response
        if session_id not in self.responses:
            self.responses[session_id] = []
        
        # Avoid duplicate responses
        if response in self.responses[session_id]:
            return
            
        self.responses[session_id].append(response)
        
        # Display response with nice formatting
        if self.waiting_for_response:
            print(f"\n┌{'─' * 58}┐")
            print(f"│ 🤖 Assistant{' ' * 45}│")
            print(f"├{'─' * 58}┤")
            
            # Word wrap the response for better readability
            words = response.split()
            line = "│ "
            for word in words:
                if len(line) + len(word) + 1 > 58:
                    print(f"{line}{' ' * (59 - len(line))}│")
                    line = "│ " + word + " "
                else:
                    line += word + " "
            if len(line) > 2:
                print(f"{line}{' ' * (59 - len(line))}│")
            
            print(f"└{'─' * 58}┘\n")
            self.waiting_for_response = False
    
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
            print(f"❌ Connection error: {e}\n")
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
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
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
            system_prompt: Custom system prompt (optional)
        """
        # Rate limiting: wait if necessary
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
        
        # Set current session to filter messages
        self.current_session = session_id
        self.waiting_for_response = True
        
        # Subscribe to response topic (only once per session)
        response_topic = f"{project}/assistant_response/{session_id}/{self.client_id}"
        if response_topic not in self._subscriptions:
            self.client.subscribe(response_topic, qos=1)
            self._subscriptions.add(response_topic)
        
        # Prepare payload
        payload = {
            "sessionId": session_id,
            "message": message,
            "replyTopic": response_topic,
            "clientId": self.client_id
        }
        
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["topP"] = top_p
        if max_tokens is not None:
            payload["maxTokens"] = max_tokens
        if system_prompt is not None:
            payload["systemPrompt"] = system_prompt
        
        # Send message with QoS 0 for better performance
        user_topic = f"{project}/user_input"
        self.client.publish(user_topic, json.dumps(payload), qos=0)
        
        # Display user message with formatting
        print(f"\n┌{'─' * 58}┐")
        print(f"│ 👤 You{' ' * 51}│")
        print(f"├{'─' * 58}┤")
        
        # Word wrap the message
        words = message.split()
        line = "│ "
        for word in words:
            if len(line) + len(word) + 1 > 58:
                print(f"{line}{' ' * (59 - len(line))}│")
                line = "│ " + word + " "
            else:
                line += word + " "
        if len(line) > 2:
            print(f"{line}{' ' * (59 - len(line))}│")
        
        print(f"└{'─' * 58}┘")
        print("\n⏳ Waiting for response...", end='', flush=True)
    
    def chat(
        self,
        project: str = "general",
        session_id: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Start an interactive chat session.
        
        Args:
            project: Project name
            session_id: Session identifier (auto-generated if not provided)
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens to generate
            system_prompt: Custom system prompt (optional)
        """
        if not session_id:
            session_id = f"user-{uuid.uuid4().hex[:8]}"
        
        # Set current session
        self.current_session = session_id
        
        # Display welcome banner
        print("\n" + "═" * 60)
        print("║" + " " * 58 + "║")
        print("║" + "🚀 vLLM Chat Client".center(58) + "║")
        print("║" + " " * 58 + "║")
        print("╠" + "═" * 58 + "╣")
        print("║" + f" 📁 Project: {project}".ljust(58) + "║")
        print("║" + f" 🔑 Session: {session_id}".ljust(58) + "║")
        if system_prompt:
            # Show first 40 chars of custom system prompt
            prompt_preview = system_prompt[:40] + "..." if len(system_prompt) > 40 else system_prompt
            print("║" + f" 🎯 Custom Prompt: {prompt_preview}".ljust(58) + "║")
        print("║" + " " * 58 + "║")
        print("╠" + "═" * 58 + "╣")
        print("║" + " 💡 Commands:".ljust(58) + "║")
        print("║" + "    • Type your message and press Enter".ljust(58) + "║")
        print("║" + "    • Type 'exit', 'quit', or 'q' to end session".ljust(58) + "║")
        print("║" + "    • Type 'clear' to clear conversation history".ljust(58) + "║")
        if not system_prompt:
            print("║" + "    • Type 'prompt <text>' to set custom system prompt".ljust(58) + "║")
        print("║" + " " * 58 + "║")
        print("═" * 60 + "\n")
        
        # Connect to broker
        if not self.connect():
            return
        
        # Subscribe to response topic immediately
        response_topic = f"{project}/assistant_response/{session_id}/{self.client_id}"
        if response_topic not in self._subscriptions:
            self.client.subscribe(response_topic, qos=1)
            self._subscriptions.add(response_topic)
        
        message_count = 0
        current_system_prompt = system_prompt  # Track current system prompt
        
        try:
            while True:
                # Get user input with prompt
                try:
                    user_input = input("� > ").strip()
                except EOFError:
                    break
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n" + "─" * 60)
                    print(f"👋 Session ended. Total messages: {message_count}")
                    print("─" * 60 + "\n")
                    break
                
                if user_input.lower() == 'clear':
                    print("\n" * 50)  # Clear screen
                    print("✓ Conversation history cleared (locally)\n")
                    continue
                
                if user_input.lower() in ['help', '?']:
                    print("\n📖 Available commands:")
                    print("  • exit/quit/q - End the chat session")
                    print("  • clear - Clear the screen")
                    print("  • prompt <text> - Set custom system prompt")
                    print("  • help/? - Show this help message\n")
                    continue
                
                # Handle custom system prompt command
                if user_input.lower().startswith('prompt '):
                    new_prompt = user_input[7:].strip()
                    if new_prompt:
                        current_system_prompt = new_prompt
                        print(f"\n✓ System prompt updated: {new_prompt[:60]}...\n" if len(new_prompt) > 60 else f"\n✓ System prompt updated: {new_prompt}\n")
                    else:
                        print("\n⚠️  Please provide a prompt text after 'prompt' command\n")
                    continue
                
                # Send message
                self.send_message(
                    project=project,
                    session_id=session_id,
                    message=user_input,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    system_prompt=current_system_prompt
                )
                
                message_count += 1
                
                # Wait for response with timeout
                timeout = 60  # 60 seconds timeout
                start_time = time.time()
                while self.waiting_for_response and (time.time() - start_time) < timeout:
                    time.sleep(0.1)
                
                if self.waiting_for_response:
                    print("\n⚠️  Timeout waiting for response\n")
                    self.waiting_for_response = False
                
        except KeyboardInterrupt:
            print("\n\n" + "─" * 60)
            print("⚠️  Interrupted by user")
            print("─" * 60 + "\n")
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
    system_prompt: Optional[str] = None,
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
        system_prompt: Custom system prompt (optional)
    
    Examples:
        # Start a general chat
        python vllm_test_client.py
        
        # Chat with the driving project
        python vllm_test_client.py --project driving --session my_session
        
        # With custom parameters
        python vllm_test_client.py --project maze --temperature 0.8 --max_tokens 256
        
        # With authentication
        python vllm_test_client.py --project driving --username TangClinic --password Tang123
        
        # With custom system prompt
        python vllm_test_client.py --project general --system_prompt "You are a helpful coding assistant"
    """
    client = vLLMClient(broker, port, username, password)
    client.chat(project, session, temperature, top_p, max_tokens, system_prompt)


if __name__ == "__main__":
    fire.Fire(main)
