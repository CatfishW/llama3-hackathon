#!/usr/bin/env python3
"""
Test script to verify MQTT connection and credentials
"""

import paho.mqtt.client as mqtt
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
MQTT_BROKER = "47.89.252.2"
MQTT_PORT = 1883
MQTT_USERNAME = "TangClinic"
MQTT_PASSWORD = "Tang123"

def on_connect(client, userdata, flags, rc, properties=None):
    """Connection callback"""
    rc_codes = {
        0: "Connection successful",
        1: "Incorrect protocol version",
        2: "Invalid client identifier",
        3: "Server unavailable",
        4: "Bad username or password",
        5: "Not authorised",
        6: "Client Identifier not valid"
    }
    
    if rc == 0:
        logger.info("✓ Connected to MQTT broker")
    else:
        error_msg = rc_codes.get(rc, f"Unknown error code: {rc}")
        logger.error(f"✗ Connection failed: [{rc}] {error_msg}")

def on_disconnect(client, userdata, flags, rc, properties=None):
    """Disconnection callback"""
    if rc != 0:
        logger.warning(f"Unexpected disconnect, code: {rc}")
    else:
        logger.info("Disconnected from MQTT broker")

def on_message(client, userdata, msg):
    """Message callback"""
    logger.info(f"Message received: {msg.topic} = {msg.payload.decode()}")

def test_connection():
    """Test MQTT connection"""
    logger.info("=" * 80)
    logger.info("MQTT Connection Test")
    logger.info("=" * 80)
    logger.info(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    logger.info(f"Username: {MQTT_USERNAME}")
    logger.info(f"Password: {'*' * len(MQTT_PASSWORD)}")
    logger.info("-" * 80)
    
    # Create client
    client = mqtt.Client(
        client_id="test-client",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    # Enable logging
    client.enable_logger(logger)
    
    # Set credentials
    logger.info(f"Setting credentials: {MQTT_USERNAME}:****")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    # Set reconnect delay
    client.reconnect_delay_set(min_delay=1, max_delay=5)
    
    # Attempt connection
    try:
        logger.info(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
        
        # Wait for connection
        logger.info("Waiting for connection response (10 seconds)...")
        time.sleep(10)
        
        if client.is_connected():
            logger.info("✓ Successfully connected to MQTT broker!")
            
            # Test publish
            logger.info("Testing message publish...")
            client.publish("test/topic", "Hello MQTT!", qos=0)
            
            time.sleep(2)
        else:
            logger.error("✗ Connection failed or timed out")
        
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        logger.error(f"Error during connection test: {type(e).__name__}: {e}")
    
    logger.info("=" * 80)

if __name__ == '__main__':
    test_connection()
