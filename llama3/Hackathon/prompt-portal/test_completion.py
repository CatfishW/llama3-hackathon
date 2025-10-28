#!/usr/bin/env python3
"""
Test script for the MQTT-based completion service

This script tests the completion service by sending completion requests
and verifying the responses.
"""

import json
import time
import uuid
from typing import Optional

import paho.mqtt.client as mqtt


class CompletionTester:
    """Test client for the completion service."""
    
    def __init__(
        self,
        broker: str = "47.89.252.2",
        port: int = 1883,
        username: Optional[str] = "TangClinic",
        password: Optional[str] = "Tang123"
    ):
        self.broker = broker
        self.port = port
        self.connected = False
        self.responses = {}
        self.client_id = f"completion-tester-{uuid.uuid4().hex[:8]}"
        
        # Create MQTT client
        self.client = mqtt.Client(client_id=self.client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        
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
            print(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
            self.connected = True
            
            # Subscribe to completion responses
            client.subscribe(f"completion/response/{self.client_id}/+", qos=1)
            print(f"✓ Subscribed to completion responses: completion/response/{self.client_id}/+")
        else:
            print(f"❌ Failed to connect to MQTT broker, code: {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback for disconnection."""
        self.connected = False
        if rc != 0:
            print(f"\n⚠️  Unexpected disconnect from MQTT broker, code: {rc}\n")
    
    def _on_message(self, client, userdata, msg):
        """Callback for incoming messages."""
        try:
            response = json.loads(msg.payload.decode('utf-8'))
            
            # Extract request ID from topic
            topic_parts = msg.topic.split('/')
            request_id = topic_parts[3]
            
            print(f"\n📨 Received completion response for request: {request_id}")
            print(f"   Completion: {response.get('completion', '')}")
            if response.get('error'):
                print(f"   Error: {response['error']}")
            
            # Store response
            self.responses[request_id] = response
            
        except Exception as e:
            print(f"Error handling completion response: {e}")
    
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
            print(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()
    
    def test_completion(
        self,
        text: str,
        completion_type: str = "general",
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
        timeout: float = 10.0
    ) -> Optional[str]:
        """
        Test completion for the given text.
        
        Args:
            text: Text to complete
            completion_type: Type of completion
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens to generate
            timeout: Timeout in seconds
            
        Returns:
            Completion text or None if failed
        """
        if not self.connected:
            print("❌ Not connected to MQTT broker")
            return None
        
        # Generate unique request ID
        request_id = uuid.uuid4().hex[:16]
        
        # Prepare request payload
        request_payload = {
            "text": text,
            "completion_type": completion_type,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }
        
        # Send request
        request_topic = f"completion/request/{self.client_id}/{request_id}"
        print(f"\n📤 Sending completion request: {request_id}")
        print(f"   Text: {text}")
        print(f"   Type: {completion_type}")
        
        self.client.publish(request_topic, json.dumps(request_payload), qos=0)
        
        # Wait for response
        start_time = time.time()
        while request_id not in self.responses and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if request_id in self.responses:
            response = self.responses[request_id]
            if response.get('error'):
                print(f"❌ Completion error: {response['error']}")
                return None
            return response.get('completion', '')
        else:
            print(f"⏰ Timeout waiting for completion response")
            return None


def main():
    """Run completion tests."""
    print("=" * 80)
    print("MQTT Completion Service Tester")
    print("=" * 80)
    
    # Create tester
    tester = CompletionTester()
    
    # Connect to broker
    if not tester.connect():
        print("Failed to connect to MQTT broker. Exiting.")
        return
    
    print("\n" + "=" * 80)
    print("Running completion tests...")
    print("=" * 80)
    
    # Test cases
    test_cases = [
        {
            "text": "Hello, how are you",
            "type": "message",
            "description": "Message completion"
        },
        {
            "text": "def calculate_sum",
            "type": "code",
            "description": "Code completion"
        },
        {
            "text": "You are a helpful assistant that",
            "type": "prompt",
            "description": "Prompt completion"
        },
        {
            "text": "Search for",
            "type": "search",
            "description": "Search completion"
        },
        {
            "text": "Dear Sir/Madam,",
            "type": "email",
            "description": "Email completion"
        },
        {
            "text": "The weather today is",
            "type": "general",
            "description": "General completion"
        }
    ]
    
    # Run tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['description']} ---")
        
        completion = tester.test_completion(
            text=test_case["text"],
            completion_type=test_case["type"],
            timeout=15.0
        )
        
        if completion:
            print(f"✅ Success: {completion}")
            results.append(True)
        else:
            print(f"❌ Failed")
            results.append(False)
        
        # Small delay between tests
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the completion service.")
    
    # Disconnect
    tester.disconnect()
    print("\nDisconnected from MQTT broker.")


if __name__ == "__main__":
    main()
