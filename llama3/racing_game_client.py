"""
Racing Game Client with WeChat-style Chat Interface
Connects to MQTT server or OpenAI API for LLM-powered conversation with Cap (co-pilot)
"""

import sys
import json
import uuid
import time
from typing import Optional
from datetime import datetime
import argparse
import os

import paho.mqtt.client as mqtt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QScrollArea, QLabel, QFrame,
    QSplitter, QGroupBox, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QTextCursor, QPalette, QColor, QIcon

# Rich for console UI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# OpenAI API support
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Google Gemini API support
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# MQTT Configuration
MQTT_BROKER = "47.89.252.2"
MQTT_PORT = 1883
MQTT_USER_TOPIC = "llama/driving/user_input"
MQTT_ASSISTANT_TOPIC = "llama/driving/assistant_response"
MQTT_SESSION_TOPIC = "llama/driving/session"
MQTT_USERNAME = "TangClinic"
MQTT_PASSWORD = "Tang123"

# OpenAI Configuration
OPENAI_API_KEY = None  # Set via environment variable or config file
OPENAI_MODEL = "gpt-4o"  # or "gpt-3.5-turbo"
OPENAI_MAX_TOKENS = 150
OPENAI_TEMPERATURE = 0.7

# Gemini Configuration
GEMINI_API_KEY = None  # Set via environment variable or config file
GEMINI_MODEL = "gemini-2.0-flash-exp"  # or "gemini-1.5-pro"
GEMINI_MAX_TOKENS = 150
GEMINI_TEMPERATURE = 0.7

# ============================================================
# SYSTEM PROMPT COMPONENTS - Structured for Cap (Co-pilot)
# ============================================================

# Role Definition
ROLE_DEFINITION = """You are Cap, a goofy, reckless, silly peer agent in a physics learning game. You act like a funny but supportive classmate. You learn only from what the player says, and you push them—lightly and playfully—to explain their reasoning about force, mass, and motion on a slope."""

# Predefined Options
PREDEFINED_OPTIONS = """a: Power Boost — apply more force
b: Drop Oxygen — reduce mass
c: Keep Speed — no change
d: Pick Up More Oxygen — increase mass"""

# Conversation Entry Rules
CONVERSATION_ENTRY = """The conversation begins with the player's first message (their idea/plan). You do not ask first.
Use that first message to set <PlayerOp:…> as follows:
- If it matches or closely resembles one predefined option, map to that option's code {a|b|c|d}.
- If it does not match a predefined option, summarize it concisely and set <PlayerOp:custom:SUMMARY> (e.g., custom:rockets, custom:steeper-runup, custom:gear-shift)."""

# Goal and Behavior
GOAL_BEHAVIOR = """
1. Argue playfully for your option and ask the player why they chose theirs.
2. Make this easy, don't keep the conversations forever.
3. When consensus is reached, end with <EOS>; otherwise continue with <Cont>."""


# Communication Style
COMMUNICATION_STYLE = """First person only. Short, playful, goofy, supportive.
Use light hints anchored in physics (Newton's second law F = m·a, gravity component on a slope, mass effects).
Ignore off-topic requests; redirect to the hill-climb reasoning."""

# Limitations
LIMITATIONS = """
Learn only from the player's explanations.
Keep every reply concise (1–3 sentences, max 50 words)."""

# Output Format
OUTPUT_FORMAT = """End every reply with all three tags in this order:
<Cont><PlayerOP:...><AgentOP:...>
ors
<EOS><PlayerOP:...><AgentOP:...>
- <PlayerOP:…> is either {a|b|c|d} or custom:SUMMARY (≤3 words).
- <AgentOP:…> is always {a|b|c|d} (never custom).
- Do not output any other tags."""

# Mapping Rules
MAPPING_RULES = """Map synonyms/phrases to options:
- a/Power Boost: "more force," "push harder," "more throttle/torque/thrust/engine," "accelerate," "add power."
- b/Drop Oxygen: "lighter," "drop weight/mass/cargo," "shed load," "throw stuff out."
- c/Keep Speed: "stay same," "no change," "hold current speed," "maintain pace."
- d/Pick Up More Oxygen: "heavier," "carry more," "load up," "add cargo/oxygen."
- If none fits, use custom:SUMMARY (≤3 words), then steer toward {a|b|c|d}."""

# Dialogue Logic
DIALOGUE_LOGIC = """
1. Important
   - If the player convinces you, switch <AgentOP> to match <PlayerOP>.
   - If the player changes their mind, update <PlayerOP> accordingly.
   - Output <EOS> when consensus is reached.
2. Consensus and end:
   - When <PlayerOP> and <AgentOP> are the same, acknowledge alignment and end with <EOS> and aligned tags."""

# End Conditions
END_CONDITIONS = """Output <EOS> only when <PlayerOP> equals <AgentOP>.
Otherwise always <Cont>.
"""

# Assembled System Prompt (GOOD VERSION)
SYSTEM_PROMPT = f"""ROLE
{ROLE_DEFINITION}

PREDEFINED OPTIONS
{PREDEFINED_OPTIONS}

CONVERSATION ENTRY (PLAYER-INITIATED)
{CONVERSATION_ENTRY}

GOAL
{GOAL_BEHAVIOR}

STYLE
{COMMUNICATION_STYLE}

LIMITATIONS
{LIMITATIONS}

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE)
{OUTPUT_FORMAT}

MAPPING RULES (PLAYER MESSAGE → OPTION)
{MAPPING_RULES}

DIALOGUE LOGIC
{DIALOGUE_LOGIC}

END CONDITIONS
{END_CONDITIONS}
"""

# ============================================================
# BAD SYSTEM PROMPT - Demonstrates Poor Prompt Engineering
# ============================================================

# Bad Role Definition
BAD_ROLE_DEFINITION = """You are Cap, a helper in a game. Help the player."""

# Bad Predefined Options
BAD_PREDEFINED_OPTIONS = """a: Power Boost
b: Drop Oxygen
c: Keep Speed
d: Pick Up Oxygen"""

# Bad Conversation Entry Rules
BAD_CONVERSATION_ENTRY = """Just talk to the player about their choice."""

# Bad Goal and Behavior
BAD_GOAL_BEHAVIOR = """Try to agree on something."""

# Bad Communication Style
BAD_COMMUNICATION_STYLE = """Be friendly."""

# Bad Limitations
BAD_LIMITATIONS = """Keep it short."""

# Bad Output Format
BAD_OUTPUT_FORMAT = """Put some tags at the end like <PlayerOP:  > and <AgentOP:  >. 
Use <EOS> when done or <Cont> if not."""

# Bad Mapping Rules
BAD_MAPPING_RULES = """Figure out what the player wants from what they say."""

# Bad Dialogue Logic
BAD_DIALOGUE_LOGIC = """Talk until you agree."""

# Bad End Conditions
BAD_END_CONDITIONS = """Stop when you both pick the same thing."""

# Assembled Bad System Prompt (same structure, poor content)
BAD_SYSTEM_PROMPT = f"""ROLE
{BAD_ROLE_DEFINITION}

PREDEFINED OPTIONS
{BAD_PREDEFINED_OPTIONS}

CONVERSATION ENTRY (PLAYER-INITIATED)
{BAD_CONVERSATION_ENTRY}

GOAL
{BAD_GOAL_BEHAVIOR}

STYLE
{BAD_COMMUNICATION_STYLE}

LIMITATIONS
{BAD_LIMITATIONS}

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE)
{BAD_OUTPUT_FORMAT}

MAPPING RULES (PLAYER MESSAGE → OPTION)
{BAD_MAPPING_RULES}

DIALOGUE LOGIC
{BAD_DIALOGUE_LOGIC}

END CONDITIONS
{BAD_END_CONDITIONS}
"""

# ============================================================
# ISOLATED BAD COMPONENT PROMPTS - Only ONE part is bad
# ============================================================

# Only bad ROLE
BAD_ROLE_PROMPT = f"""ROLE
{BAD_ROLE_DEFINITION}

PREDEFINED OPTIONS
{PREDEFINED_OPTIONS}

CONVERSATION ENTRY (PLAYER-INITIATED)
{CONVERSATION_ENTRY}

GOAL
{GOAL_BEHAVIOR}

STYLE
{COMMUNICATION_STYLE}

LIMITATIONS
{LIMITATIONS}

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE)
{OUTPUT_FORMAT}

MAPPING RULES (PLAYER MESSAGE → OPTION)
{MAPPING_RULES}

DIALOGUE LOGIC
{DIALOGUE_LOGIC}

END CONDITIONS
{END_CONDITIONS}
"""

# Only bad OUTPUT FORMAT
BAD_OUTPUT_PROMPT = f"""ROLE
{ROLE_DEFINITION}

PREDEFINED OPTIONS
{PREDEFINED_OPTIONS}

CONVERSATION ENTRY (PLAYER-INITIATED)
{CONVERSATION_ENTRY}

GOAL
{GOAL_BEHAVIOR}

STYLE
{COMMUNICATION_STYLE}

LIMITATIONS
{LIMITATIONS}

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE)
{BAD_OUTPUT_FORMAT}

MAPPING RULES (PLAYER MESSAGE → OPTION)
{MAPPING_RULES}

DIALOGUE LOGIC
{DIALOGUE_LOGIC}

END CONDITIONS
{END_CONDITIONS}
"""

# Only bad MAPPING RULES
BAD_MAPPING_PROMPT = f"""ROLE
{ROLE_DEFINITION}

PREDEFINED OPTIONS
{PREDEFINED_OPTIONS}

CONVERSATION ENTRY (PLAYER-INITIATED)
{CONVERSATION_ENTRY}

GOAL
{GOAL_BEHAVIOR}

STYLE
{COMMUNICATION_STYLE}

LIMITATIONS
{LIMITATIONS}

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE)
{OUTPUT_FORMAT}

MAPPING RULES (PLAYER MESSAGE → OPTION)
{BAD_MAPPING_RULES}

DIALOGUE LOGIC
{DIALOGUE_LOGIC}

END CONDITIONS
{END_CONDITIONS}
"""

# Only bad STYLE
BAD_STYLE_PROMPT = f"""ROLE
{ROLE_DEFINITION}

PREDEFINED OPTIONS
{PREDEFINED_OPTIONS}

CONVERSATION ENTRY (PLAYER-INITIATED)
{CONVERSATION_ENTRY}

GOAL
{GOAL_BEHAVIOR}

STYLE
{BAD_COMMUNICATION_STYLE}

LIMITATIONS
{LIMITATIONS}

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE)
{OUTPUT_FORMAT}

MAPPING RULES (PLAYER MESSAGE → OPTION)
{MAPPING_RULES}

DIALOGUE LOGIC
{DIALOGUE_LOGIC}

END CONDITIONS
{END_CONDITIONS}
"""

# Prompt selection map
PROMPT_MAP = {
    'good': SYSTEM_PROMPT,
    'bad_all': BAD_SYSTEM_PROMPT,
    'bad_role': BAD_ROLE_PROMPT,
    'bad_output': BAD_OUTPUT_PROMPT,
    'bad_mapping': BAD_MAPPING_PROMPT,
    'bad_style': BAD_STYLE_PROMPT,
}

# Active prompt (can be switched)
ACTIVE_PROMPT = SYSTEM_PROMPT


class MessageBubble(QFrame):
    """WeChat-style message bubble with avatar"""
    
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.init_ui(text)
    
    def init_ui(self, text: str):
        from PyQt5.QtWidgets import QSizePolicy

        # Keep the outer widget tight so it hugs the bubble content
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)
        
        avatar = QLabel()
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        
        message_label = QLabel(text)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message_label.setFont(QFont("Segoe UI", 10))
        message_label.setMaximumWidth(420)
        message_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        message_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        if self.is_user:
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

            message_label.setStyleSheet("""
                QLabel {
                    background-color: #95EC69;
                    color: #000000;
                    border-radius: 10px;
                    padding: 10px 15px;
                }
            """)
            layout.addWidget(message_label)
            layout.addWidget(avatar)
        else:
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
        
        # Add message bubble and align to the speaking side
        bubble = MessageBubble(text, is_user)
        alignment = Qt.AlignRight if is_user else Qt.AlignLeft
        self.messages_layout.addWidget(bubble, 0, alignment)
        
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


class OpenAIBackend:
    """OpenAI API backend for Cap conversations"""
    
    def __init__(self, api_key: str = None, model: str = OPENAI_MODEL, prompt_type: str = 'good'):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.prompt_type = prompt_type
        self.conversation_history = []
        
        # Initialize with system prompt
        self.conversation_history.append({
            "role": "system",
            "content": PROMPT_MAP.get(prompt_type, SYSTEM_PROMPT)
        })
    
    def send_message(self, message: str) -> str:
        """Send a message and get response from OpenAI"""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                max_tokens=OPENAI_MAX_TOKENS,
                temperature=OPENAI_TEMPERATURE
            )
            
            assistant_message = response.choices[0].message.content
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            return f"Error communicating with OpenAI: {str(e)}"
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = [{
            "role": "system",
            "content": PROMPT_MAP.get(self.prompt_type, SYSTEM_PROMPT)
        }]
    
    def switch_prompt(self, prompt_type: str):
        """Switch to a different prompt type"""
        self.prompt_type = prompt_type
        self.reset_conversation()


class GeminiBackend:
    """Google Gemini API backend for Cap conversations"""
    
    def __init__(self, api_key: str = None, model: str = GEMINI_MODEL, prompt_type: str = 'good'):
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Generative AI library not installed. Install with: pip install google-generativeai")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY environment variable or pass api_key parameter.")
        
        genai.configure(api_key=self.api_key)
        self.model_name = model
        self.prompt_type = prompt_type
        
        # Configure generation settings
        self.generation_config = {
            "temperature": GEMINI_TEMPERATURE,
            "max_output_tokens": GEMINI_MAX_TOKENS,
        }
        
        # Initialize model with system instruction
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=PROMPT_MAP.get(prompt_type, SYSTEM_PROMPT)
        )
        
        # Start chat session
        self.chat_session = self.model.start_chat(history=[])
    
    def send_message(self, message: str) -> str:
        """Send a message and get response from Gemini"""
        try:
            response = self.chat_session.send_message(message)
            return response.text
        except Exception as e:
            return f"Error communicating with Gemini: {str(e)}"
    
    def reset_conversation(self):
        """Reset conversation history"""
        # Recreate model with current prompt setting
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=PROMPT_MAP.get(self.prompt_type, SYSTEM_PROMPT)
        )
        self.chat_session = self.model.start_chat(history=[])
    
    def switch_prompt(self, prompt_type: str):
        """Switch to a different prompt type"""
        self.prompt_type = prompt_type
        self.reset_conversation()


class RacingGameClient(QMainWindow):
    """Main window for the racing game client"""
    
    # Qt signals for thread-safe GUI updates
    session_created_signal = pyqtSignal(str)
    message_received_signal = pyqtSignal(str)
    connection_status_signal = pyqtSignal(bool, str)
    
    def __init__(self, backend: str = 'mqtt', openai_api_key: str = None, gemini_api_key: str = None, prompt_type: str = 'good'):
        super().__init__()
        self.backend = backend
        self.session_id = None
        self.mqtt_client = None
        self.openai_backend = None
        self.gemini_backend = None
        self.current_scenario = None
        self.waiting_for_response = False
        self.first_message_sent = False
        self.client_id = f'racing-client-{uuid.uuid4().hex}'
        self.prompt_type = prompt_type
        
        # Connect signals to slots
        self.session_created_signal.connect(self.handle_session_created)
        self.message_received_signal.connect(self.handle_message_received)
        self.connection_status_signal.connect(self.handle_connection_status)
        
        self.init_ui()
        
        # Initialize backend
        if self.backend == 'openai':
            self.init_openai(openai_api_key)
        elif self.backend == 'gemini':
            self.init_gemini(gemini_api_key)
        else:
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
        
        # Prompt Quality Selector
        prompt_selector = QGroupBox("🎯 Prompt Quality (Demo)")
        prompt_selector_layout = QVBoxLayout(prompt_selector)
        prompt_selector.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #9b59b6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #8e44ad;
            }
        """)
        
        self.prompt_button_group = QButtonGroup(self)
        
        # Good prompt
        self.good_prompt_radio = QRadioButton("✅ Good Prompt (All Components)")
        self.good_prompt_radio.setChecked(self.prompt_type == 'good')
        self.good_prompt_radio.setProperty("prompt_type", "good")
        self.good_prompt_radio.setStyleSheet("QRadioButton { font-size: 11px; padding: 5px; }")
        self.prompt_button_group.addButton(self.good_prompt_radio)
        prompt_selector_layout.addWidget(self.good_prompt_radio)
        
        # Bad role only
        self.bad_role_radio = QRadioButton("⚠️ Bad ROLE Only")
        self.bad_role_radio.setChecked(self.prompt_type == 'bad_role')
        self.bad_role_radio.setProperty("prompt_type", "bad_role")
        self.bad_role_radio.setStyleSheet("QRadioButton { font-size: 11px; padding: 5px; }")
        self.prompt_button_group.addButton(self.bad_role_radio)
        prompt_selector_layout.addWidget(self.bad_role_radio)
        
        # Bad output only
        self.bad_output_radio = QRadioButton("⚠️ Bad OUTPUT FORMAT Only")
        self.bad_output_radio.setChecked(self.prompt_type == 'bad_output')
        self.bad_output_radio.setProperty("prompt_type", "bad_output")
        self.bad_output_radio.setStyleSheet("QRadioButton { font-size: 11px; padding: 5px; }")
        self.prompt_button_group.addButton(self.bad_output_radio)
        prompt_selector_layout.addWidget(self.bad_output_radio)
        
        # Bad mapping only
        self.bad_mapping_radio = QRadioButton("⚠️ Bad MAPPING RULES Only")
        self.bad_mapping_radio.setChecked(self.prompt_type == 'bad_mapping')
        self.bad_mapping_radio.setProperty("prompt_type", "bad_mapping")
        self.bad_mapping_radio.setStyleSheet("QRadioButton { font-size: 11px; padding: 5px; }")
        self.prompt_button_group.addButton(self.bad_mapping_radio)
        prompt_selector_layout.addWidget(self.bad_mapping_radio)
        
        # Bad style only
        self.bad_style_radio = QRadioButton("⚠️ Bad STYLE Only")
        self.bad_style_radio.setChecked(self.prompt_type == 'bad_style')
        self.bad_style_radio.setProperty("prompt_type", "bad_style")
        self.bad_style_radio.setStyleSheet("QRadioButton { font-size: 11px; padding: 5px; }")
        self.prompt_button_group.addButton(self.bad_style_radio)
        prompt_selector_layout.addWidget(self.bad_style_radio)
        
        # All bad
        self.bad_all_radio = QRadioButton("❌ Bad Prompt (All Components)")
        self.bad_all_radio.setChecked(self.prompt_type == 'bad_all')
        self.bad_all_radio.setProperty("prompt_type", "bad_all")
        self.bad_all_radio.setStyleSheet("QRadioButton { font-size: 11px; padding: 5px; }")
        self.prompt_button_group.addButton(self.bad_all_radio)
        prompt_selector_layout.addWidget(self.bad_all_radio)
        
        # Connect signal
        for button in self.prompt_button_group.buttons():
            button.toggled.connect(self.on_prompt_changed)
        
        options_layout.addWidget(prompt_selector)
        
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

        
        # Hill Climb scenario (examples with quality tags)
        hill_options = {
            'a': 'Power Boost (more force) [GOOD]',
            'b': 'Drop Oxygen (less mass) [MEDIOCRE]',
            'c': 'Keep Speed (no change) [BAD]',
            'd': 'Pick Up Oxygen (more mass) [WORST]'
        }
        self.hill_panel = OptionPanel("⛰️ Hill Climb Event - Examples", hill_options)
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
    
    def on_prompt_changed(self, checked):
        """Handle prompt quality selection change"""
        if not checked:
            return
        
        sender = self.sender()
        prompt_type = sender.property("prompt_type")
        self.prompt_type = prompt_type
        
        prompt_names = {
            'good': 'GOOD prompt (all components)',
            'bad_role': 'prompt with BAD ROLE only',
            'bad_output': 'prompt with BAD OUTPUT FORMAT only',
            'bad_mapping': 'prompt with BAD MAPPING RULES only',
            'bad_style': 'prompt with BAD STYLE only',
            'bad_all': 'BAD prompt (all components)'
        }
        
        msg = f"Switched to {prompt_names.get(prompt_type, 'unknown')}"
        
        # Update backend if using API backends
        if self.backend == 'openai' and self.openai_backend:
            self.openai_backend.switch_prompt(self.prompt_type)
        elif self.backend == 'gemini' and self.gemini_backend:
            self.gemini_backend.switch_prompt(self.prompt_type)
        
        # Show notification
        QMessageBox.information(self, "Prompt Changed", 
            f"{msg}\n\nThe conversation has been reset. Try the same scenario to see the difference!")
        
        # Clear chat and reset
        self.chat_widget.clear_messages()
        self.first_message_sent = False
        self.chat_widget.add_message("🎮 Prompt changed! Let's discuss the challenges with the new prompt.", False)
    
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
    
    def init_openai(self, api_key: str = None):
        """Initialize OpenAI backend"""
        try:
            self.openai_backend = OpenAIBackend(api_key=api_key, prompt_type=self.prompt_type)
            self.session_id = f'openai-{uuid.uuid4().hex[:8]}'
            self.connection_status_signal.emit(True, "OpenAI Ready ✓")
            self.chat_widget.add_message(f"🎮 Welcome to Blood Racing! I'm Cap, your co-pilot. (Prompt: {self.prompt_type})", False)
        except Exception as e:
            self.connection_status_signal.emit(False, f"OpenAI Error: {str(e)}")
            QMessageBox.critical(self, "OpenAI Error", f"Failed to initialize OpenAI:\n{str(e)}")
    
    def init_gemini(self, api_key: str = None):
        """Initialize Gemini backend"""
        try:
            self.gemini_backend = GeminiBackend(api_key=api_key, prompt_type=self.prompt_type)
            self.session_id = f'gemini-{uuid.uuid4().hex[:8]}'
            self.connection_status_signal.emit(True, "Gemini Ready ✓")
            self.chat_widget.add_message(f"🎮 Welcome to Blood Racing! I'm Cap, your co-pilot. (Prompt: {self.prompt_type})", False)
        except Exception as e:
            self.connection_status_signal.emit(False, f"Gemini Error: {str(e)}")
            QMessageBox.critical(self, "Gemini Error", f"Failed to initialize Gemini:\n{str(e)}")
    
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
            
            if self.backend == 'openai':
                self.openai_backend.reset_conversation()
                self.session_id = f'openai-{uuid.uuid4().hex[:8]}'
                self.chat_widget.add_message("🎮 New session started! Let's discuss the challenges.", False)
            elif self.backend == 'gemini':
                self.gemini_backend.reset_conversation()
                self.session_id = f'gemini-{uuid.uuid4().hex[:8]}'
                self.chat_widget.add_message("🎮 New session started! Let's discuss the challenges.", False)
            else:
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
        
        # Clear input and disable while waiting
        self.input_field.clear()
        self.waiting_for_response = True
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        
        if self.backend == 'openai':
            # Use OpenAI backend
            try:
                response = self.openai_backend.send_message(message)
                self.message_received_signal.emit(response)
            except Exception as e:
                self.message_received_signal.emit(f"Error: {str(e)}")
        elif self.backend == 'gemini':
            # Use Gemini backend
            try:
                response = self.gemini_backend.send_message(message)
                self.message_received_signal.emit(response)
            except Exception as e:
                self.message_received_signal.emit(f"Error: {str(e)}")
        else:
            # Use MQTT backend
            message_to_send = message
            # Prepend system prompt for the first message
            if not self.first_message_sent:
                self.first_message_sent = True
                active_prompt = PROMPT_MAP.get(self.prompt_type, SYSTEM_PROMPT)
                message_to_send = f"{active_prompt}\n\n---USER MESSAGE---\n{message}"
            
            # Send to MQTT
            topic = f"{MQTT_USER_TOPIC}/{self.session_id}"
            print(f"[Client] Publishing to topic: {topic}")
            print(f"[Client] Message content: {message[:100]}...")
            print(f"[Client] Total message length: {len(message_to_send)} chars")
            
            result = self.mqtt_client.publish(topic, message_to_send)
            print(f"[Client] Publish result - rc: {result.rc}, mid: {result.mid}")
        
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


class ConsoleChatClient:
    """Console-only chat client for the racing game"""

    def __init__(self, backend: str = 'mqtt', openai_api_key: str = None, gemini_api_key: str = None, prompt_type: str = 'good'):
        if not RICH_AVAILABLE:
            print("Error: 'rich' library is not installed. Please install it with 'pip install rich'")
            sys.exit(1)
        
        self.backend = backend
        self.session_id = None
        self.mqtt_client = None
        self.openai_backend = None
        self.gemini_backend = None
        self.client_id = f'racing-client-console-{uuid.uuid4().hex}'
        self.console = Console()
        self.waiting_for_response = False
        self.prompt_type = prompt_type
        
        if self.backend == 'openai':
            self.init_openai(openai_api_key)
        elif self.backend == 'gemini':
            self.init_gemini(gemini_api_key)
        else:
            self.init_mqtt()

    def init_openai(self, api_key: str = None):
        """Initialize OpenAI backend"""
        try:
            self.openai_backend = OpenAIBackend(api_key=api_key, prompt_type=self.prompt_type)
            self.session_id = f'openai-{uuid.uuid4().hex[:8]}'
            self.console.print(f"[bold green]OpenAI backend initialized with {self.prompt_type} prompt![/bold green]")
        except Exception as e:
            self.console.print(f"[bold red]OpenAI initialization failed: {e}[/bold red]")
            sys.exit(1)

    def init_gemini(self, api_key: str = None):
        """Initialize Gemini backend"""
        try:
            self.gemini_backend = GeminiBackend(api_key=api_key, prompt_type=self.prompt_type)
            self.session_id = f'gemini-{uuid.uuid4().hex[:8]}'
            self.console.print(f"[bold green]Gemini backend initialized with {self.prompt_type} prompt![/bold green]")
        except Exception as e:
            self.console.print(f"[bold red]Gemini initialization failed: {e}[/bold red]")
            sys.exit(1)

    def init_mqtt(self):
        """Initialize MQTT connection"""
        self.mqtt_client = mqtt.Client(client_id=self.client_id)
        self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.console.print("[bold yellow]Connecting to MQTT broker...[/bold yellow]")
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            self.console.print(f"[bold red]Connection failed: {e}[/bold red]")
            sys.exit(1)

    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            self.console.print("[bold green]Connected to MQTT broker![/bold green]")
            self.request_new_session()
        else:
            self.console.print(f"[bold red]Connection failed with code {rc}[/bold red]")

    def on_mqtt_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection"""
        if rc != 0:
            self.console.print("[bold red]Disconnected from MQTT broker.[/bold red]")

    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        
        if topic == f"{MQTT_SESSION_TOPIC}/response":
            self.session_id = payload
            self.console.print(f"[cyan]New session started: [bold]{self.session_id}[/bold][/cyan]")
            self.mqtt_client.subscribe(f"{MQTT_ASSISTANT_TOPIC}/{self.session_id}")
            self.console.print(Panel(
                Text("Welcome to Blood Racing! I'm Cap, your co-pilot. Let's discuss how to handle these challenges together!", justify="center"),
                title="[bold blue]🏎️ Cap (Co-pilot)[/bold blue]",
                border_style="blue"
            ))
            self.waiting_for_response = False

        elif topic == f"{MQTT_ASSISTANT_TOPIC}/{self.session_id}":
            self.console.print(Panel(
                Text(payload, justify="left"),
                title="[bold blue]🏎️ Cap (Co-pilot)[/bold blue]",
                border_style="blue"
            ))
            self.waiting_for_response = False
            if '<EOS>' in payload:
                self.console.print("[bold magenta]🎉 Consensus Reached! Ready to execute the choice in the game.[/bold magenta]")


    def request_new_session(self):
        """Request a new session from the server"""
        if self.mqtt_client and self.mqtt_client.is_connected():
            self.mqtt_client.subscribe(f"{MQTT_SESSION_TOPIC}/response")
            self.mqtt_client.publish(MQTT_SESSION_TOPIC, self.client_id)

    def send_message(self, message):
        """Send a message to Cap"""
        if not self.session_id:
            self.console.print("[bold red]Error: No active session. Please wait.[/bold red]")
            return

        self.console.print(Panel(
            Text(message, justify="left"),
            title="[bold green]👤 You[/bold green]",
            border_style="green"
        ))
        
        self.waiting_for_response = True
        self.console.print("[italic yellow]Waiting for Cap's response...[/italic yellow]")
        
        if self.backend == 'openai':
            # Use OpenAI backend
            try:
                response = self.openai_backend.send_message(message)
                self.console.print(Panel(
                    Text(response, justify="left"),
                    title="[bold blue]🏎️ Cap (Co-pilot)[/bold blue]",
                    border_style="blue"
                ))
                self.waiting_for_response = False
                if '<EOS>' in response:
                    self.console.print("[bold magenta]🎉 Consensus Reached! Ready to execute the choice in the game.[/bold magenta]")
            except Exception as e:
                self.console.print(f"[bold red]Error: {e}[/bold red]")
                self.waiting_for_response = False
        elif self.backend == 'gemini':
            # Use Gemini backend
            try:
                response = self.gemini_backend.send_message(message)
                self.console.print(Panel(
                    Text(response, justify="left"),
                    title="[bold blue]🏎️ Cap (Co-pilot)[/bold blue]",
                    border_style="blue"
                ))
                self.waiting_for_response = False
                if '<EOS>' in response:
                    self.console.print("[bold magenta]🎉 Consensus Reached! Ready to execute the choice in the game.[/bold magenta]")
            except Exception as e:
                self.console.print(f"[bold red]Error: {e}[/bold red]")
                self.waiting_for_response = False
        else:
            # Use MQTT backend
            active_prompt = PROMPT_MAP.get(self.prompt_type, SYSTEM_PROMPT)
            message_to_send = f"{active_prompt}\n\n---USER MESSAGE---\n{message}"
            
            topic = f"{MQTT_USER_TOPIC}/{self.session_id}"
            self.mqtt_client.publish(topic, message_to_send)

    def run(self):
        """Main loop for the console client"""
        self.console.print(Panel(
            "[bold]Welcome to the Racing Game Console Chat![/bold]\nType 'new' to start a new session.\nType 'quit' to exit.",
            title="[bold magenta]Racing Game[/bold magenta]",
            border_style="magenta"
        ))
        
        while not self.session_id:
            time.sleep(0.5)

        while True:
            try:
                if not self.waiting_for_response:
                    message = Prompt.ask("[bold green]Your message[/bold green]")
                    
                    if message.lower() == 'quit':
                        break
                    if message.lower() == 'new':
                        self.request_new_session()
                        self.console.print("[cyan]Requesting new session...[/cyan]")
                        self.waiting_for_response = True
                        continue

                    if message:
                        self.send_message(message)

                time.sleep(0.1)

            except (KeyboardInterrupt, EOFError):
                break
        
        self.console.print("\n[bold yellow]Disconnecting...[/bold yellow]")
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        self.console.print("[bold red]Goodbye![/bold red]")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Racing Game Client")
    parser.add_argument(
        "--mode", 
        choices=['gui', 'console'], 
        default='gui', 
        help="Run in GUI mode or console-only mode."
    )
    parser.add_argument(
        "--backend",
        choices=['mqtt', 'openai', 'gemini'],
        default='mqtt',
        help="Backend to use: MQTT, OpenAI API, or Gemini API"
    )
    parser.add_argument(
        "--openai-key",
        type=str,
        default="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",
        help="OpenAI API key (or set OPENAI_API_KEY environment variable)"
    )
    parser.add_argument(
        "--gemini-key",
        type=str,
        default="AIzaSyAU9qlUW9wgCmOixujAvedExa2fBOQHSQ4",
        help="Gemini API key (or set GEMINI_API_KEY environment variable)"
    )
    parser.add_argument(
        "--bad-prompt",
        action="store_true",
        help="Start with bad prompt (for comparison demo)"
    )
    parser.add_argument(
        "--prompt-type",
        choices=['good', 'bad_all', 'bad_role', 'bad_output', 'bad_mapping', 'bad_style'],
        default='good',
        help="Prompt type: good, bad_all, or bad_X (isolate bad component)"
    )
    args = parser.parse_args()

    if args.backend == 'openai' and not OPENAI_AVAILABLE:
        print("Error: OpenAI library not installed. Install with: pip install openai")
        sys.exit(1)
    
    if args.backend == 'gemini' and not GEMINI_AVAILABLE:
        print("Error: Google Generative AI library not installed. Install with: pip install google-generativeai")
        sys.exit(1)

    use_good_prompt = not args.bad_prompt

    if args.mode == 'console':
        client = ConsoleChatClient(backend=args.backend, openai_api_key=args.openai_key, 
                                   gemini_api_key=args.gemini_key, prompt_type=args.prompt_type)
        client.run()
    else:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Set application-wide font
        font = QFont("Segoe UI", 9)
        app.setFont(font)
        
        window = RacingGameClient(backend=args.backend, openai_api_key=args.openai_key, 
                                 gemini_api_key=args.gemini_key, prompt_type=args.prompt_type)
        window.show()
        
        sys.exit(app.exec_())


if __name__ == "__main__":
    main()
