# lam_mqtt_hackathon_test.py

import time
import json
import uuid
import logging
import threading
import paho.mqtt.client as mqtt
from datetime import datetime

# MQTT broker settings (matching your deploy script)
MQTT_BROKER = "47.89.252.2"
MQTT_PORT = 1883
STATE_TOPIC = "maze/state"
HINT_PREFIX = "maze/hint"

class MQTTTester:
    def __init__(self, username=None, password=None):
        self.username = username
        self.password = password
        self.messages_received = []
        self.connection_status = {"publisher": False, "subscriber": False}
        self.test_session_id = f"test-{uuid.uuid4().hex[:8]}"
        
        # Create two clients - one for publishing, one for subscribing
        self.publisher = mqtt.Client(client_id=f"test-publisher-{uuid.uuid4().hex[:8]}")
        self.subscriber = mqtt.Client(client_id=f"test-subscriber-{uuid.uuid4().hex[:8]}")
        
        if username and password:
            self.publisher.username_pw_set(username, password)
            self.subscriber.username_pw_set(username, password)
        
        self.setup_callbacks()
        
    def setup_callbacks(self):
        # Publisher callbacks
        def on_publisher_connect(client, userdata, flags, rc):
            if rc == 0:
                self.connection_status["publisher"] = True
                logging.info("✅ Publisher connected to MQTT broker")
            else:
                logging.error(f"❌ Publisher connection failed with code {rc}")
        
        # Subscriber callbacks
        def on_subscriber_connect(client, userdata, flags, rc):
            if rc == 0:
                self.connection_status["subscriber"] = True
                logging.info("✅ Subscriber connected to MQTT broker")
                # Subscribe to hint topic for our test session
                hint_topic = f"{HINT_PREFIX}/{self.test_session_id}"
                client.subscribe(hint_topic)
                logging.info(f"📡 Subscribed to topic: {hint_topic}")
            else:
                logging.error(f"❌ Subscriber connection failed with code {rc}")
        
        def on_message(client, userdata, msg):
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            message_data = {
                "timestamp": timestamp,
                "topic": msg.topic,
                "payload": msg.payload.decode("utf-8")
            }
            self.messages_received.append(message_data)
            logging.info(f"📨 Received message at {timestamp}")
            logging.info(f"   Topic: {msg.topic}")
            logging.info(f"   Payload: {msg.payload.decode('utf-8')}")
        
        self.publisher.on_connect = on_publisher_connect
        self.subscriber.on_connect = on_subscriber_connect
        self.subscriber.on_message = on_message
    
    def connect_clients(self):
        """Connect both MQTT clients"""
        logging.info("🔌 Connecting to MQTT broker...")
        
        try:
            self.publisher.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self.subscriber.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            
            # Start the loops in separate threads
            self.publisher.loop_start()
            self.subscriber.loop_start()
            
            # Wait for connections
            max_wait = 10  # seconds
            start_time = time.time()
            while (time.time() - start_time) < max_wait:
                if self.connection_status["publisher"] and self.connection_status["subscriber"]:
                    break
                time.sleep(0.1)
            
            return self.connection_status["publisher"] and self.connection_status["subscriber"]
            
        except Exception as e:
            logging.error(f"❌ Connection error: {e}")
            return False
    
    def disconnect_clients(self):
        """Disconnect both MQTT clients"""
        logging.info("🔌 Disconnecting from MQTT broker...")
        self.publisher.loop_stop()
        self.subscriber.loop_stop()
        self.publisher.disconnect()
        self.subscriber.disconnect()
    
    def send_test_state(self, test_number=1):
        """Send a test maze state message"""
        test_state = {
            "sessionId": self.test_session_id,
            "player_pos": [1, 1],
            "exit_pos": [5, 5],
            "visible_map": [
                [0, 0, 0, 0, 0, 0, 0],
                [0, 1, 1, 0, 1, 1, 0],
                [0, 1, 0, 0, 0, 1, 0],
                [0, 1, 1, 1, 1, 1, 0],
                [0, 0, 0, 0, 0, 1, 0],
                [0, 1, 1, 1, 1, 1, 0],
                [0, 0, 0, 0, 0, 0, 0]
            ],
            "test_number": test_number,
            "timestamp": datetime.now().isoformat()
        }
        
        payload = json.dumps(test_state, indent=2)
        
        logging.info(f"📤 Sending test state #{test_number}")
        logging.info(f"   Topic: {STATE_TOPIC}")
        logging.info(f"   Session ID: {self.test_session_id}")
        
        result = self.publisher.publish(STATE_TOPIC, payload)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logging.info("✅ Message published successfully")
            return True
        else:
            logging.error(f"❌ Failed to publish message, error code: {result.rc}")
            return False
    
    def wait_for_response(self, timeout=30):
        """Wait for a response on the hint topic"""
        logging.info(f"⏳ Waiting for response (timeout: {timeout}s)...")
        
        start_time = time.time()
        initial_count = len(self.messages_received)
        
        while (time.time() - start_time) < timeout:
            if len(self.messages_received) > initial_count:
                return True
            time.sleep(0.1)
        
        logging.warning(f"⚠️ No response received within {timeout} seconds")
        return False
    
    def print_status(self):
        """Print current test status"""
        print("\n" + "="*60)
        print("🧪 MQTT TEST STATUS")
        print("="*60)
        print(f"Publisher Connected:  {'✅' if self.connection_status['publisher'] else '❌'}")
        print(f"Subscriber Connected: {'✅' if self.connection_status['subscriber'] else '❌'}")
        print(f"Test Session ID:      {self.test_session_id}")
        print(f"Messages Received:    {len(self.messages_received)}")
        
        if self.messages_received:
            print("\n📨 RECEIVED MESSAGES:")
            for i, msg in enumerate(self.messages_received, 1):
                print(f"  {i}. [{msg['timestamp']}] {msg['topic']}")
                try:
                    parsed = json.loads(msg['payload'])
                    print(f"     {json.dumps(parsed, indent=6)}")
                except:
                    print(f"     {msg['payload']}")
        print("="*60)

def run_comprehensive_test(username=None, password=None):
    """Run a comprehensive MQTT test"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    
    print("🧪 Starting MQTT Comprehensive Test")
    print(f"🏠 Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"🔐 Auth: {'Yes' if username else 'No'}")
    
    tester = MQTTTester(username, password)
    
    try:
        # Step 1: Connect
        print("\n1️⃣ TESTING CONNECTION")
        if not tester.connect_clients():
            print("❌ Connection test failed!")
            return False
        
        time.sleep(2)  # Allow connections to stabilize
        
        # Step 2: Send test messages
        print("\n2️⃣ TESTING MESSAGE PUBLISHING")
        success_count = 0
        
        for i in range(1, 4):  # Send 3 test messages
            if tester.send_test_state(i):
                success_count += 1
            time.sleep(1)
        
        print(f"📊 Published {success_count}/3 messages successfully")
        
        # Step 3: Wait for responses
        print("\n3️⃣ TESTING MESSAGE RECEPTION")
        if tester.wait_for_response(timeout=15):
            print("✅ Response received!")
        else:
            print("⚠️ No response received - this might be normal if no LAM is running")
        
        # Step 4: Show results
        print("\n4️⃣ TEST RESULTS")
        tester.print_status()
        
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return False
    except Exception as e:
        logging.error(f"❌ Test error: {e}")
        return False
    finally:
        tester.disconnect_clients()
        print("\n🏁 Test completed")

def run_simple_ping_test(username=None, password=None):
    """Run a simple ping test to check basic connectivity"""
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    
    print("🏓 Running simple MQTT ping test...")
    
    client = mqtt.Client(client_id=f"ping-test-{uuid.uuid4().hex[:8]}")
    if username and password:
        client.username_pw_set(username, password)
    
    connected = False
    
    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        connected = (rc == 0)
        if connected:
            print("✅ MQTT connection successful!")
        else:
            print(f"❌ MQTT connection failed with code {rc}")
    
    client.on_connect = on_connect
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
        
        # Wait for connection
        for _ in range(50):  # 5 seconds max
            if connected:
                break
            time.sleep(0.1)
        
        client.loop_stop()
        client.disconnect()
        
        return connected
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test MQTT connectivity for maze LAM")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--simple", action="store_true", help="Run simple ping test only")
    
    args = parser.parse_args()
    
    if args.simple:
        success = run_simple_ping_test(args.username, args.password)
    else:
        success = run_comprehensive_test(args.username, args.password)
    
    exit(0 if success else 1)

# Example usage:
# python lam_mqtt_hackathon_test.py --username TangClinic --password Tang123
# python lam_mqtt_hackathon_test.py --username TangClinic --password Tang123 --simple
