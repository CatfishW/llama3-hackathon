"""
Llama.cpp Web Server - Flask Backend
Provides WebSocket and HTTP API for the web chat interface
Communicates with MQTT broker to interface with llama.cpp backend
"""

import json
import logging
import os
import uuid
import threading
import time
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import paho.mqtt.client as mqtt

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """Application configuration"""
    
    # Flask
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # MQTT
    MQTT_BROKER = os.getenv('MQTT_BROKER', '47.89.252.2')
    MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
    MQTT_USERNAME = "TangClinic"
    MQTT_PASSWORD = "Tang123"
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # Projects
    PROJECTS = {
        'general': {
            'name': 'General',
            'description': 'General-purpose AI assistant'
        },
        'maze': {
            'name': 'Maze Game',
            'description': 'Strategic hints for maze solving'
        },
        'driving': {
            'name': 'Driving Simulator',
            'description': 'Physics learning for driving'
        },
        'bloodcell': {
            'name': 'Blood Cell Education',
            'description': 'Educational game about blood cells'
        },
        'racing': {
            'name': 'Racing Game',
            'description': 'Physics concepts in racing'
        }
    }


# ============================================================================
# Setup Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Flask App Initialization
# ============================================================================

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static',
            static_url_path='/static')
app.config.from_object(Config)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


# ============================================================================
# MQTT Client
# ============================================================================

class MQTTClient:
    """MQTT client for backend communication"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = mqtt.Client(
            client_id=f"web-server-{uuid.uuid4().hex[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set credentials if provided
        if config.MQTT_USERNAME and config.MQTT_PASSWORD:
            logger.info(f"Setting MQTT credentials: username={config.MQTT_USERNAME}")
            self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        else:
            logger.warning("No MQTT credentials provided, connecting anonymously")
        
        self.connected = False
        self.message_handlers = {}  # topic -> callback mapping
        
    def connect(self):
        """Connect to MQTT broker"""
        try:
            logger.info(f"Attempting to connect to MQTT broker at {self.config.MQTT_BROKER}:{self.config.MQTT_PORT}")
            logger.info(f"Using credentials: username={self.config.MQTT_USERNAME}")
            
            # Set reconnect delay
            self.client.reconnect_delay_set(min_delay=1, max_delay=32)
            
            # Set enable logging for debugging
            self.client.enable_logger(logger)
            
            # Attempt connection
            self.client.connect(self.config.MQTT_BROKER, self.config.MQTT_PORT, keepalive=60)
            self.client.loop_start()
            
            logger.info(f"MQTT connection initiated to {self.config.MQTT_BROKER}:{self.config.MQTT_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {type(e).__name__}: {e}")
            logger.warning("Will retry automatically...")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
    
    def subscribe(self, topic: str, callback=None):
        """Subscribe to a topic"""
        try:
            self.client.subscribe(topic, qos=1)
            if callback:
                self.message_handlers[topic] = callback
            logger.debug(f"Subscribed to topic: {topic}")
        except Exception as e:
            logger.error(f"Error subscribing to {topic}: {e}")
    
    def publish(self, topic: str, message: Dict, qos: int = 0):
        """Publish message to a topic"""
        try:
            payload = json.dumps(message) if isinstance(message, dict) else str(message)
            self.client.publish(topic, payload, qos=qos)
            logger.debug(f"Published to {topic}: {message}")
            return True
        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for connection"""
        # MQTT return codes
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
            self.connected = True
            logger.info("✓ MQTT broker connected successfully")
        else:
            self.connected = False
            error_msg = rc_codes.get(rc, f"Unknown error code: {rc}")
            logger.error(f"✗ MQTT connection failed: [{rc}] {error_msg}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback for disconnection"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnect, code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for message arrival"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            try:
                message = json.loads(payload)
            except:
                message = payload
            
            # Call registered handler
            if topic in self.message_handlers:
                self.message_handlers[topic](topic, message)
            
            logger.debug(f"Received from {topic}: {message}")
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")


# ============================================================================
# Session Manager
# ============================================================================

class SessionManager:
    """Manages user sessions and chat contexts"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def create_session(self, user_id: str, project: str) -> str:
        """Create new session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'id': session_id,
            'user_id': user_id,
            'project': project,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'message_count': 0
        }
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session info"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str):
        """Update session activity"""
        if session_id in self.sessions:
            self.sessions[session_id]['last_activity'] = datetime.now().isoformat()
            self.sessions[session_id]['message_count'] += 1
    
    def delete_session(self, session_id: str):
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")


# ============================================================================
# Global Instances
# ============================================================================

mqtt_client = MQTTClient(Config)
session_manager = SessionManager()


# ============================================================================
# HTTP Routes
# ============================================================================

@app.route('/')
def index():
    """Serve main chat interface"""
    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get application configuration"""
    return jsonify({
        'mqtt_broker': Config.MQTT_BROKER,
        'mqtt_port': Config.MQTT_PORT,
        'projects': Config.PROJECTS,
        'version': '1.0.0',
        'server_time': datetime.now().isoformat()
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'mqtt_connected': mqtt_client.connected,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get available projects"""
    return jsonify({
        'projects': Config.PROJECTS,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get server statistics"""
    return jsonify({
        'active_sessions': len(session_manager.sessions),
        'mqtt_connected': mqtt_client.connected,
        'timestamp': datetime.now().isoformat()
    })


# ============================================================================
# WebSocket Events (SocketIO)
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    user_id = request.sid
    logger.info(f"Client connected: {user_id}")
    emit('connect_response', {
        'data': 'Connected to server',
        'mqtt_connected': mqtt_client.connected
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    user_id = request.sid
    logger.info(f"Client disconnected: {user_id}")


@socketio.on('send_message')
def handle_send_message(data):
    """Handle message from client"""
    try:
        session_id = data.get('session_id')
        project = data.get('project', 'general')
        message = data.get('message', '')
        
        if not session_id:
            session_id = session_manager.create_session(request.sid, project)
        
        session_manager.update_session(session_id)
        
        if not message.strip():
            emit('error', {'message': 'Empty message'})
            return
        
        # Prepare MQTT message
        mqtt_payload = {
            'sessionId': session_id,
            'message': message,
            'clientId': request.sid,
            'temperature': data.get('temperature'),
            'topP': data.get('topP'),
            'maxTokens': data.get('maxTokens'),
            'systemPrompt': data.get('systemPrompt'),
            'replyTopic': f"{project}/assistant_response/{session_id}"
        }
        
        # Publish to MQTT
        user_topic = f"{project}/user_input"
        if mqtt_client.publish(user_topic, mqtt_payload):
            emit('message_sent', {'session_id': session_id})
        else:
            emit('error', {'message': 'Failed to send message'})
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        emit('error', {'message': str(e)})


@socketio.on('create_session')
def handle_create_session(data):
    """Create new chat session"""
    project = data.get('project', 'general')
    session_id = session_manager.create_session(request.sid, project)
    emit('session_created', {'session_id': session_id, 'project': project})


@socketio.on('subscribe_response')
def handle_subscribe_response(data):
    """Subscribe to response topic"""
    session_id = data.get('session_id')
    project = data.get('project', 'general')
    
    response_topic = f"{project}/assistant_response/{session_id}"
    
    def on_response(topic, message):
        # Emit response to client via WebSocket
        socketio.emit('response_received', {
            'session_id': session_id,
            'message': message,
            'topic': topic
        }, to=request.sid)
    
    mqtt_client.subscribe(response_topic, on_response)


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Startup & Shutdown
# ============================================================================

@app.before_request
def before_request():
    """Before request hook"""
    if request.path.startswith('/api/'):
        logger.debug(f"{request.method} {request.path}")


@app.after_request
def after_request(response):
    """After request hook"""
    if request.path.startswith('/api/'):
        logger.debug(f"Response: {response.status_code}")
    return response


def initialize_app():
    """Initialize application"""
    logger.info("=" * 80)
    logger.info("Llama.cpp Web Server Starting")
    logger.info("=" * 80)
    logger.info(f"Flask Debug: {Config.DEBUG}")
    logger.info(f"MQTT Broker: {Config.MQTT_BROKER}:{Config.MQTT_PORT}")
    logger.info(f"Server: {Config.HOST}:{Config.PORT}")
    
    # Connect to MQTT with retry logic
    logger.info("Attempting to connect to MQTT broker...")
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        if mqtt_client.connect():
            logger.info("✓ MQTT connected successfully")
            break
        else:
            retry_count += 1
            if retry_count < max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(f"MQTT connection attempt {retry_count}/{max_retries} failed. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.warning("✗ MQTT connection failed after retries. App will continue, MQTT will retry automatically.")
    
    logger.info("=" * 80)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    initialize_app()
    
    try:
        socketio.run(
            app,
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        mqtt_client.disconnect()
        logger.info("Server stopped")
