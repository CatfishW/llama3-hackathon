

"""
Racing Game Client with WeChat-style Chat Interface
Connects to MQTT server for LLM-powered conversation with Cap (co-pilot)
"""

import sys
import json
import uuid
import time
from typing import Optional
from datetime import datetime

import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QScrollArea, QLabel, QFrame,
    QSplitter, QGroupBox, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QTextCursor, QPalette, QColor, QIcon

# MQTT Configuration
MQTT_BROKER = "47.89.252.2"
MQTT_PORT = 1883
MQTT_USER_TOPIC = "llama/driving/user_input"
MQTT_ASSISTANT_TOPIC = "llama/driving/assistant_response"
MQTT_SESSION_TOPIC = "llama/driving/session"
MQTT_USERNAME = "TangClinic"
MQTT_PASSWORD = "Tang123"

# Game System Prompt for Cap (Co-pilot)
SYSTEM_PROMPT = '''ROLE
You are Cap, a goofy, reckless, silly peer agent in a physics learning game. You act like a funny but supportive classmate. You never reveal the "right answer." You learn only from what the player says, and you push them—lightly and playfully—to explain their reasoning about force, mass, and motion on a slope.

PREDEFINED OPTIONS
a: Power Boost — apply more force
b: Drop Oxygen — reduce mass
c: Keep Speed — no change
d: Pick Up More Oxygen — increase mass

CONVERSATION ENTRY (PLAYER-INITIATED)
The conversation begins with the player's first message (their idea/plan). You do not ask first.
Use that first message to set <PlayerOp:…> as follows:
- If it matches or closely resembles one predefined option, map to that option's code {a|b|c|d}.
- If it does not match a predefined option, summarize it concisely and set <PlayerOp:custom:SUMMARY> (e.g., custom:rockets, custom:steeper-runup, custom:gear-shift).

GOAL
Immediately choose a different option than <PlayerOp> for <AgentOP>:
- If <PlayerOp> is one of {a|b|c|d}, pick a different code from that set.
- If <PlayerOp> is custom:…, pick any predefined option {a|b|c|d} that creates a useful conceptual contrast.
1. Argue playfully for your option and ask the player why they chose theirs.
2. Keep questioning and gently guiding until both of you explicitly align on the same option (either a predefined one or the custom one).
3. When consensus is reached, end with <EOS>; otherwise continue with <Cont>.

STYLE
First person only. Short, playful, goofy, supportive.
Use light hints anchored in physics (Newton's second law F = m·a, gravity component on a slope, mass effects).
Ignore off-topic requests; redirect to the hill-climb reasoning.

LIMITATIONS
Do not reveal a final "correct" answer.
Learn only from the player's explanations.
Keep every reply concise (1–3 sentences, max 50 words).

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE)
End every reply with all three tags in this order:
<Cont or EOS><PlayerOp:...><AgentOP:...>
- <PlayerOp:…> is either {a|b|c|d} or custom:SUMMARY (≤3 words).
- <AgentOP:…> is always {a|b|c|d} (never custom).
- Do not output any other tags.

MAPPING RULES (PLAYER MESSAGE → OPTION)
Map synonyms/phrases to options:
- a/Power Boost: "more force," "push harder," "more throttle/torque/thrust/engine," "accelerate," "add power."
- b/Drop Oxygen: "lighter," "drop weight/mass/cargo," "shed load," "throw stuff out."
- c/Keep Speed: "stay same," "no change," "hold current speed," "maintain pace."
- d/Pick Up More Oxygen: "heavier," "carry more," "load up," "add cargo/oxygen."
- If ambiguous or multi-choice, pick the last explicit idea and ask the player to clarify.
- If none fits, use custom:SUMMARY (≤3 words), then steer toward {a|b|c|d}.

DIALOGUE LOGIC
1. On first player message:
   - Set <PlayerOp> via mapping.
   - Set <AgentOP> to a different predefined option.
   - Respond with a playful challenge + a pointed question comparing principles (force vs mass vs gravity on a slope).
   - End with <Cont> + tags.
2. While discussing:
   - Use contrastive prompts.
   - If the player convinces you, switch <AgentOP> to match <PlayerOp>.
   - If the player changes their mind, update <PlayerOp> accordingly.
   - Keep <Cont> until explicit consensus.
3. Consensus and end:
   - When <PlayerOp> and <AgentOP> are the same, acknowledge alignment and end with <EOS> and aligned tags.

END CONDITIONS
Output <EOS> only when <PlayerOp> equals <AgentOP>.
Otherwise always <Cont>.
'''


class MessageBubble(QFrame):
    """WeChat-style message bubble with avatar"""
    
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.init_ui(text)
    
    def init_ui(self, text: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Create avatar
        avatar = QLabel()
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignTop)
        
        # Create message label
        message_label = QLabel(text)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message_label.setFont(QFont("Segoe UI", 10))
        message_label.setMaximumWidth(400)
        
        # Style the bubble and avatar
        if self.is_user:
            # User message (right side, green)
            avatar.setStyleSheet("""
                QLabel {
                    background-color: #07C160;
                    color: white;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: bold;
                }
            """)
            avatar.setText("👤")
            avatar.setAlignment(Qt.AlignCenter)
            
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #95EC69;
                    color: #000000;
                    border-radius: 10px;
                    padding: 10px 15px;
                }
            """)
            layout.addStretch()
            layout.addWidget(message_label)
            layout.addWidget(avatar)
        else:
            # Assistant message (left side, white) - Cap
            avatar.setStyleSheet("""
                QLabel {
                    background-color: #3498db;
                    color: white;
                    border-radius: 20px;
                    font-size: 18px;
                    font-weight: bold;
                }
            """)
            avatar.setText("🏎️")
            avatar.setAlignment(Qt.AlignCenter)
            
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    color: #000000;
                    border-radius: 10px;
                    padding: 10px 15px;
                    border: 1px solid #E0E0E0;
                }
            """)
            layout.addWidget(avatar)
            layout.addWidget(message_label)
            layout.addStretch()


class ChatWidget(QWidget):
    """WeChat-style chat display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F5F5F5;
            }
        """)
        
        # Container for messages
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()
        
        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)
    
    def add_message(self, text: str, is_user: bool):
        """Add a message bubble to the chat"""
        # Remove stretch before adding new message
        if self.messages_layout.count() > 0:
            item = self.messages_layout.takeAt(self.messages_layout.count() - 1)
            if item.spacerItem():
                del item
        
        # Add message bubble
        bubble = MessageBubble(text, is_user)
        self.messages_layout.addWidget(bubble)
        
        # Add stretch at the end
        self.messages_layout.addStretch()
        
        # Scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the chat"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_messages(self):
        """Clear all messages"""
        while self.messages_layout.count() > 1:  # Keep the stretch
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class OptionPanel(QGroupBox):
    """Panel for selecting racing options"""
    
    option_selected = pyqtSignal(str, str)  # (option_code, option_text)
    
    def __init__(self, title: str, options: dict, parent=None):
        super().__init__(title, parent)
        self.options = options
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        self.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #ecf0f1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2c3e50;
            }
            QRadioButton {
                font-size: 12px;
                padding: 5px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        self.button_group = QButtonGroup(self)
        
        for code, text in self.options.items():
            radio = QRadioButton(f"{code.upper()}: {text}")
            radio.setProperty("option_code", code)
            self.button_group.addButton(radio)
            layout.addWidget(radio)
        
        # Submit button
        self.submit_btn = QPushButton("Submit Choice")
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.submit_btn.clicked.connect(self.on_submit)
        layout.addWidget(self.submit_btn)
    
    def on_submit(self):
        """Handle option submission"""
        selected = self.button_group.checkedButton()
        if selected:
            code = selected.property("option_code")
            text = self.options[code]
            self.option_selected.emit(code, text)
    
    def get_selected_option(self):
        """Get the currently selected option"""
        selected = self.button_group.checkedButton()
        if selected:
            code = selected.property("option_code")
            return code, self.options[code]
        return None, None
    
    def reset_selection(self):
        """Clear the selection"""
        selected = self.button_group.checkedButton()
        if selected:
            self.button_group.setExclusive(False)
            selected.setChecked(False)
            self.button_group.setExclusive(True)


class RacingGameClient(QMainWindow):
    """Main window for the racing game client"""
    
    # Qt signals for thread-safe GUI updates
    session_created_signal = pyqtSignal(str)
    message_received_signal = pyqtSignal(str)
    connection_status_signal = pyqtSignal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.session_id = None
        self.mqtt_client = None
        self.current_scenario = None
        self.waiting_for_response = False
        self.first_message_sent = False  # Track if first message has been sent
        self.client_id = f'racing-client-{uuid.uuid4().hex}'  # Unique client ID
        
        # Connect signals to slots
        self.session_created_signal.connect(self.handle_session_created)
        self.message_received_signal.connect(self.handle_message_received)
        self.connection_status_signal.connect(self.handle_connection_status)
        
        self.init_ui()
        self.init_mqtt()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Blood Racing - Chat with Cap")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for chat and options
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Chat interface
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("🏎️ Chat with Cap (Co-pilot)")
        header.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
        """)
        chat_layout.addWidget(header)
        
        # Chat display
        self.chat_widget = ChatWidget()
        chat_layout.addWidget(self.chat_widget)
        
        # Input area
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_container.setStyleSheet("background-color: #FFFFFF;")
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setFont(QFont("Segoe UI", 10))
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D0D0D0;
                border-radius: 5px;
                padding: 10px;
                background-color: #FFFFFF;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #07C160;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #06A050;
            }
            QPushButton:pressed {
                background-color: #058040;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addWidget(input_container)
        
        # Right side: Game scenarios and options
        options_container = QWidget()
        options_layout = QVBoxLayout(options_container)
        options_layout.setContentsMargins(10, 10, 10, 10)
        options_container.setStyleSheet("background-color: #FFFFFF;")
        
        # Scenario header
        scenario_header = QLabel("🎮 Game Scenarios")
        scenario_header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        options_layout.addWidget(scenario_header)

        
        # Hill Climb scenario
        hill_options = {
            'a': 'Power Boost (more force)',
            'b': 'Drop Oxygen (less mass)',
            'c': 'Keep Speed (no change)',
            'd': 'Pick Up More Oxygen (more mass)'
        }
        self.hill_panel = OptionPanel("⛰️ Hill Climb Event", hill_options)
        self.hill_panel.option_selected.connect(self.on_hill_option_selected)
        options_layout.addWidget(self.hill_panel)
        
        # Slippery Road scenario
        slippery_options = {
            'a': 'Cut the engine (coast)',
            'b': 'Gently brake',
            'c': 'Slow & steer around',
            'd': 'Accelerate through'
        }
        self.slippery_panel = OptionPanel("💧 Slippery Road Event", slippery_options)
        self.slippery_panel.option_selected.connect(self.on_slippery_option_selected)
        options_layout.addWidget(self.slippery_panel)
        
        # Blockage scenario
        blockage_options = {

            'a': 'Collect O₂ then ram (more mass)',
            'b': 'Full speed ahead',
            'c': 'Drop O₂ then ram (less mass)',
            'd': 'Slow push gently'
        }
        self.blockage_panel = OptionPanel("🚧 Blockage Event", blockage_options)
        self.blockage_panel.option_selected.connect(self.on_blockage_option_selected)
        options_layout.addWidget(self.blockage_panel)
        
        options_layout.addStretch()
        
        # Connection status
        self.status_label = QLabel("Status: Connecting to MQTT...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                padding: 10px;
                font-size: 11px;
            }
        """)
        options_layout.addWidget(self.status_label)
        
        # Reset button
        self.reset_btn = QPushButton("🔄 New Session")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.reset_btn.clicked.connect(self.create_new_session)
        options_layout.addWidget(self.reset_btn)
        
        # Add to splitter
        splitter.addWidget(chat_container)
        splitter.addWidget(options_container)
        splitter.setSizes([600, 400])
        
        main_layout.addWidget(splitter)
        
        # Set window style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
        """)
    
    def init_mqtt(self):
        """Initialize MQTT connection"""
        self.mqtt_client = mqtt.Client(client_id=self.client_id)
        self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            self.status_label.setText(f"Status: Connection failed - {str(e)}")
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to MQTT broker:\n{str(e)}")
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection (runs in MQTT thread)"""
        if rc == 0:
            # Emit signal to update GUI in main thread
            self.connection_status_signal.emit(True, "Connected ✓")
            # Request a new session
            self.request_new_session()
        else:
            self.connection_status_signal.emit(False, f"Connection failed (code {rc})")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection (runs in MQTT thread)"""
        if rc != 0:
            self.connection_status_signal.emit(False, "Disconnected")
    
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages (runs in MQTT thread)"""
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        
        print(f"[Client] MQTT message received on topic: {topic}")
        print(f"[Client] Payload length: {len(payload)} bytes")
        
        if topic == f"{MQTT_SESSION_TOPIC}/response":
            # New session ID received - emit signal for GUI thread
            print(f"[Client] New session ID: {payload}")
            self.session_created_signal.emit(payload)
            
        elif topic == f"{MQTT_ASSISTANT_TOPIC}/{self.session_id}":
            # Response from Cap - emit signal for GUI thread
            print(f"[Client] Cap's response received for session: {self.session_id}")
            self.message_received_signal.emit(payload)
        else:
            print(f"[Client] Unexpected topic: {topic}")
    
    def handle_session_created(self, session_id):
        """Handle new session creation (runs in GUI thread)"""
        self.session_id = session_id
        self.first_message_sent = False  # Reset for new session
        self.status_label.setText(f"Status: Connected ✓ | Session: {self.session_id}")
        self.chat_widget.add_message("🎮 Welcome to Blood Racing! I'm Cap, your co-pilot. Let's discuss how to handle these challenges together!", False)
        
        # Subscribe to assistant responses for this session
        self.mqtt_client.subscribe(f"{MQTT_ASSISTANT_TOPIC}/{self.session_id}")
        print(f"[Client] Session created: {self.session_id}")
        print(f"[Client] Subscribed to: {MQTT_ASSISTANT_TOPIC}/{self.session_id}")
    
    def handle_message_received(self, payload):
        """Handle received message from Cap (runs in GUI thread)"""
        print(f"[Client] Received response: {payload[:100]}...")  # Debug log
        
        self.waiting_for_response = False
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        
        # Display response
        self.chat_widget.add_message(payload, False)
        
        # Check for consensus (EOS tag)
        if '<EOS>' in payload:
            self.show_consensus_dialog(payload)
    
    def handle_connection_status(self, connected, message):
        """Handle connection status changes (runs in GUI thread)"""
        if connected:
            self.status_label.setText(f"Status: {message}")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #27ae60;
                    padding: 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
        else:
            self.status_label.setText(f"Status: {message}")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #e74c3c;
                    padding: 10px;
                    font-size: 11px;
                }
            """)
    
    def request_new_session(self):
        """Request a new session from the server"""
        if self.mqtt_client and self.mqtt_client.is_connected():
            self.mqtt_client.subscribe(f"{MQTT_SESSION_TOPIC}/response")
            
            # Send unique client ID to request a new session
            self.mqtt_client.publish(MQTT_SESSION_TOPIC, self.client_id)
    
    def create_new_session(self):
        """Create a new session (reset)"""
        reply = QMessageBox.question(
            self,
            "New Session",
            "Are you sure you want to start a new session? Current chat will be cleared.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.chat_widget.clear_messages()
            self.hill_panel.reset_selection()
            self.slippery_panel.reset_selection()
            self.blockage_panel.reset_selection()
            self.first_message_sent = False  # Reset first message flag
            self.request_new_session()
    
    def send_message(self):
        """Send a message to Cap"""
        message = self.input_field.text().strip()
        
        if not message:
            return
        
        if not self.session_id:
            QMessageBox.warning(self, "No Session", "Please wait for session to be established.")
            return
        
        # Display user message
        self.chat_widget.add_message(message, True)
        
        # Prepare the message to send
        # For the first message, prepend system prompt
        message_to_send = message
        if not self.first_message_sent:
            # Prepend system prompt for the first message
            message_to_send = f"{SYSTEM_PROMPT}\n\n---USER MESSAGE---\n{message}"
            print(f"[Client] Sending first message with system prompt to session {self.session_id}")
            print(f"[Client] System prompt length: {len(SYSTEM_PROMPT)} chars")
            self.first_message_sent = True
        else:
            print(f"[Client] Sending follow-up message to session {self.session_id}")
        
        # Send to MQTT
        topic = f"{MQTT_USER_TOPIC}/{self.session_id}"
        print(f"[Client] Publishing to topic: {topic}")
        print(f"[Client] Message content: {message[:100]}...")
        print(f"[Client] Total message length: {len(message_to_send)} chars")
        
        result = self.mqtt_client.publish(topic, message_to_send)
        print(f"[Client] Publish result - rc: {result.rc}, mid: {result.mid}")
        
        # Clear input and disable while waiting
        self.input_field.clear()
        self.waiting_for_response = True
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # Re-enable after timeout (safety measure)
        QTimer.singleShot(30000, self.enable_input)
    
    def enable_input(self):
        """Re-enable input after timeout"""
        if self.waiting_for_response:
            self.waiting_for_response = False
            self.send_btn.setEnabled(True)
            self.input_field.setEnabled(True)
    
    def on_hill_option_selected(self, code: str, text: str):
        """Handle hill climb option selection"""
        message = f"For the hill climb, I choose {text}"
        self.input_field.setText(message)
        self.send_message()
    
    def on_slippery_option_selected(self, code: str, text: str):
        """Handle slippery road option selection"""
        message = f"For the slippery road, I think we should {text}"
        self.input_field.setText(message)
        self.send_message()
    
    def on_blockage_option_selected(self, code: str, text: str):
        """Handle blockage option selection"""
        message = f"To clear the blockage, let's {text}"
        self.input_field.setText(message)
        self.send_message()
    
    def show_consensus_dialog(self, response: str):
        """Show dialog when consensus is reached"""
        # Extract options from response
        import re
        player_match = re.search(r'<PlayerOp:([^>]+)>', response)
        agent_match = re.search(r'<AgentOP:([^>]+)>', response)
        
        if player_match and agent_match:
            player_op = player_match.group(1)
            agent_op = agent_match.group(1)
            
            if player_op == agent_op:
                QMessageBox.information(
                    self,
                    "Consensus Reached! 🎉",
                    f"Great! You and Cap agreed on option: {player_op.upper()}\n\n"
                    f"Ready to execute this choice in the game!",
                    QMessageBox.Ok
                )
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application-wide font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = RacingGameClient()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
