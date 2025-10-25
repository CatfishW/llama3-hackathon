"""
Test script for MQTT message flow between web game and LLM backend.

This script simulates the web game publishing state messages and monitors
the responses to verify the integration is working correctly.
"""

import paho.mqtt.client as mqtt
import json
import time
import uuid

# MQTT Configuration
MQTT_BROKER = "47.89.252.2"
MQTT_PORT = 1883
MQTT_USERNAME = "TangClinic"
MQTT_PASSWORD = "Tang123"

# Test session ID
TEST_SESSION_ID = f"test-{uuid.uuid4().hex[:8]}"

# Response received flag
response_received = False

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback for MQTT connection."""
    if rc == 0:
        print(f"✓ Connected to MQTT broker")
        # Subscribe to response topics
        client.subscribe(f"maze/hint/+", qos=1)
        client.subscribe(f"maze/assistant_response/+", qos=1)
        print(f"✓ Subscribed to maze/hint/+ and maze/assistant_response/+")
    else:
        print(f"✗ Connection failed with code: {rc}")

def on_message(client, userdata, msg):
    """Callback for incoming messages."""
    global response_received
    print(f"\n{'='*60}")
    print(f"📨 RESPONSE RECEIVED")
    print(f"{'='*60}")
    print(f"Topic: {msg.topic}")
    print(f"Payload:")
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        print(json.dumps(data, indent=2))
    except:
        print(msg.payload.decode('utf-8'))
    print(f"{'='*60}\n")
    response_received = True

def test_state_message():
    """Test sending a maze state message."""
    print("\n" + "="*60)
    print("TEST 1: Maze State Message")
    print("="*60)
    
    client = mqtt.Client(client_id=f"test-state-{uuid.uuid4().hex[:8]}", 
                        callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    
    # Wait for connection
    time.sleep(2)
    
    # Create test state message
    state_message = {
        "sessionId": TEST_SESSION_ID,
        "player_pos": {"x": 1, "y": 1},
        "exit_pos": {"x": 8, "y": 8},
        "visible_map": [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0, 1, 1, 1, 1, 0],
            [0, 1, 0, 1, 0, 1, 0, 0, 1, 0],
            [0, 1, 0, 1, 1, 1, 1, 0, 1, 0],
            [0, 1, 0, 0, 0, 0, 1, 0, 1, 0],
            [0, 1, 1, 1, 1, 1, 1, 0, 1, 0],
            [0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
            [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
            [0, 1, 0, 0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        ],
        "germs": [
            {"x": 5, "y": 3},
            {"x": 7, "y": 5}
        ],
        "oxygenPellets": [
            {"x": 3, "y": 2},
            {"x": 6, "y": 4}
        ],
        "oxygenCollected": 0
    }
    
    print(f"\nPublishing state message to: maze/state")
    print(f"Session ID: {TEST_SESSION_ID}")
    print(f"Player at: ({state_message['player_pos']['x']}, {state_message['player_pos']['y']})")
    print(f"Exit at: ({state_message['exit_pos']['x']}, {state_message['exit_pos']['y']})")
    
    result = client.publish("maze/state", json.dumps(state_message), qos=0)
    
    if result.rc == 0:
        print("✓ Message published successfully")
    else:
        print(f"✗ Publish failed with code: {result.rc}")
    
    # Wait for response (up to 30 seconds)
    print("\nWaiting for response from LLM (up to 30 seconds)...")
    global response_received
    response_received = False
    
    for i in range(30):
        if response_received:
            print("\n✓ Test PASSED: Response received!")
            break
        time.sleep(1)
        if i % 5 == 4:
            print(f"  Still waiting... ({i+1}s)")
    else:
        print("\n✗ Test FAILED: No response received within 30 seconds")
        print("\nTroubleshooting:")
        print("1. Check if llamacpp_mqtt_deploy.py is running")
        print("2. Verify it subscribed to 'maze/state' topic")
        print("3. Check logs for errors")
        print("4. Ensure LLM server is running on http://localhost:8080")
    
    client.loop_stop()
    client.disconnect()

def test_user_input_message():
    """Test sending a direct user input message."""
    print("\n" + "="*60)
    print("TEST 2: Direct User Input Message")
    print("="*60)
    
    client = mqtt.Client(client_id=f"test-input-{uuid.uuid4().hex[:8]}", 
                        callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    
    # Wait for connection
    time.sleep(2)
    
    # Create test user input message
    user_message = {
        "sessionId": TEST_SESSION_ID,
        "message": "Hello! Please guide me through the maze from (1,1) to (8,8)."
    }
    
    print(f"\nPublishing user input to: maze/user_input")
    print(f"Session ID: {TEST_SESSION_ID}")
    print(f"Message: {user_message['message']}")
    
    result = client.publish("maze/user_input", json.dumps(user_message), qos=0)
    
    if result.rc == 0:
        print("✓ Message published successfully")
    else:
        print(f"✗ Publish failed with code: {result.rc}")
    
    # Wait for response (up to 30 seconds)
    print("\nWaiting for response from LLM (up to 30 seconds)...")
    global response_received
    response_received = False
    
    for i in range(30):
        if response_received:
            print("\n✓ Test PASSED: Response received!")
            break
        time.sleep(1)
        if i % 5 == 4:
            print(f"  Still waiting... ({i+1}s)")
    else:
        print("\n✗ Test FAILED: No response received within 30 seconds")
    
    client.loop_stop()
    client.disconnect()

def monitor_topics():
    """Monitor all maze topics for debugging."""
    print("\n" + "="*60)
    print("MONITOR MODE: Listening to all maze topics")
    print("="*60)
    print("Press Ctrl+C to stop\n")
    
    def on_monitor_message(client, userdata, msg):
        print(f"\n[{time.strftime('%H:%M:%S')}] Topic: {msg.topic}")
        try:
            data = json.loads(msg.payload.decode('utf-8'))
            print(json.dumps(data, indent=2)[:500])
        except:
            print(msg.payload.decode('utf-8')[:500])
    
    client = mqtt.Client(client_id=f"monitor-{uuid.uuid4().hex[:8]}", 
                        callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_message = on_monitor_message
    
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    
    # Subscribe to all maze topics
    topics = [
        ("maze/#", 1),  # All maze topics
    ]
    client.subscribe(topics)
    print("Subscribed to: maze/#")
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        client.disconnect()

if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("MQTT Integration Test Suite")
    print("="*60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        monitor_topics()
    else:
        print("\nRunning automated tests...")
        print("\nPrerequisites:")
        print("1. llamacpp_mqtt_deploy.py is running with --projects maze")
        print("2. LLM server is running on http://localhost:8080")
        print("3. MQTT broker is accessible at 47.89.252.2:1883")
        
        input("\nPress Enter to start tests...")
        
        # Run tests
        test_state_message()
        
        print("\n" + "-"*60)
        time.sleep(2)
        
        test_user_input_message()
        
        print("\n" + "="*60)
        print("Test suite complete!")
        print("="*60)
        
        print("\nTo monitor topics in real-time, run:")
        print("  python test_mqtt_integration.py monitor")
