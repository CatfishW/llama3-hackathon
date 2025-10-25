# Blood Racing Game - Client Interface Preview

## Main Window Layout

```
╔════════════════════════════════════════════════════════════════════════════════╗
║  🏎️ Chat with Cap (Co-pilot)                                                  ║
╠═══════════════════════════════════╦════════════════════════════════════════════╣
║                                   ║  🎮 Game Scenarios                         ║
║                                   ║                                            ║
║  [Chat Area - WeChat Style]       ║  ⛰️ Hill Climb Event                       ║
║                                   ║  ┌────────────────────────────────────┐   ║
║  ┌──────────────────────────┐    ║  │ ○ a: Power Boost (more force)      │   ║
║  │ Welcome to Blood Racing! │    ║  │ ○ b: Drop Oxygen (less mass)       │   ║
║  │ I'm Cap, your co-pilot.  │    ║  │ ○ c: Keep Speed (no change)        │   ║
║  │ Let's discuss how to     │    ║  │ ○ d: Pick Up More Oxygen (more mass)│  ║
║  │ handle these challenges! │    ║  │                                    │   ║
║  └──────────────────────────┘    ║  │      [Submit Choice]               │   ║
║                                   ║  └────────────────────────────────────┘   ║
║             ┌─────────────────┐  ║                                            ║
║             │ I choose Power  │  ║  💧 Slippery Road Event                    ║
║             │ Boost!          │  ║  ┌────────────────────────────────────┐   ║
║             └─────────────────┘  ║  │ ○ a: Cut the engine (coast)        │   ║
║                                   ║  │ ○ b: Gently brake                  │   ║
║  ┌──────────────────────────┐    ║  │ ○ c: Slow & steer around           │   ║
║  │ I'd drop oxygen instead— │    ║  │ ○ d: Accelerate through            │   ║
║  │ lighter climbs cleaner.  │    ║  │                                    │   ║
║  │ Why is more force better?│    ║  │      [Submit Choice]               │   ║
║  │ <Cont><PlayerOp:a>       │    ║  └────────────────────────────────────┘   ║
║  │ <AgentOP:b>              │    ║                                            ║
║  └──────────────────────────┘    ║  🚧 Blockage Event                         ║
║                                   ║  ┌────────────────────────────────────┐   ║
║             ┌─────────────────┐  ║  │ ○ a: Collect O₂ then ram (more mass)│  ║
║             │ Because F=ma!   │  ║  │ ○ b: Full speed ahead              │   ║
║             │ More force means│  ║  │ ○ c: Drop O₂ then ram (less mass)  │   ║
║             │ more acceleration│  ║  │ ○ d: Slow push gently              │   ║
║             └─────────────────┘  ║  │                                    │   ║
║                                   ║  │      [Submit Choice]               │   ║
║  ┌──────────────────────────┐    ║  └────────────────────────────────────┘   ║
║  │ Okay, you're right! Let's│    ║                                            ║
║  │ go with Power Boost.     │    ║                                            ║
║  │ <EOS><PlayerOp:a>        │    ║  ┌────────────────────────────────────┐   ║
║  │ <AgentOP:a>              │    ║  │ Status: Connected ✓                │   ║
║  └──────────────────────────┘    ║  │ Session: abc123xyz                 │   ║
║                                   ║  └────────────────────────────────────┘   ║
║                                   ║                                            ║
║                                   ║  ┌────────────────────────────────────┐   ║
║                                   ║  │      🔄 New Session                │   ║
║                                   ║  └────────────────────────────────────┘   ║
╠═══════════════════════════════════╩════════════════════════════════════════════╣
║  Type your message here...                                     [Send]          ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

## Color Scheme

### Chat Bubbles
- **User Messages**: 
  - Background: #95EC69 (WeChat green)
  - Text: Black
  - Position: Right-aligned
  
- **Cap Messages**:
  - Background: White
  - Border: #E0E0E0 (light gray)
  - Text: Black
  - Position: Left-aligned

### UI Elements
- **Header**: #2c3e50 (dark blue-gray)
- **Background**: #F5F5F5 (light gray)
- **Scenario Panels**: #ecf0f1 (light blue-gray)
- **Panel Borders**: #3498db (bright blue)
- **Send Button**: #07C160 (WeChat green)
- **Reset Button**: #e74c3c (red)
- **Submit Buttons**: #3498db (blue)

## Feature Highlights

### 1. Auto-scrolling Chat
- Automatically scrolls to newest message
- Smooth animation
- Shows conversation history

### 2. Session Management
- Unique session ID for each game
- Displays current session in status bar
- "New Session" button to reset

### 3. Quick Option Selection
- Three scenario panels always visible
- Radio buttons for easy selection
- One-click submission

### 4. Real-time Status
- Connection indicator (green ✓)
- Session ID display
- Disconnection warnings

### 5. Message Input
- Large text field
- "Send" button with hover effects
- Enter key support
- Auto-clear after sending

## Window Properties
- **Size**: 1000x700 pixels
- **Resizable**: Yes
- **Splitter**: Adjustable between chat (600px) and options (400px)
- **Font**: Segoe UI (Windows native)
- **Style**: Modern Flat Design (Fusion style)

## Message Flow Indicators

User sends:
```
"I choose Power Boost"
```

Cap responds with tags:
```
I'd drop oxygen instead—lighter climbs cleaner. 
Why is more force better here?
<Cont><PlayerOp:a><AgentOP:b>
```

After consensus:
```
Okay, you're right! Let's go with Power Boost.
<EOS><PlayerOp:a><AgentOP:a>
```

## Animations & Effects

1. **Message Appearance**: Smooth fade-in as bubbles are added
2. **Auto-scroll**: Gentle scroll to bottom after new message
3. **Button Hover**: Color change on mouse over
4. **Button Press**: Visual feedback on click
5. **Status Update**: Smooth transition between states

## Accessibility Features

- Text is selectable in chat bubbles
- Clear visual hierarchy
- High contrast text
- Keyboard shortcuts (Enter to send)
- Screen reader friendly (proper labels)

## Technical Implementation

### PyQt5 Widgets Used:
- `QMainWindow` - Main window container
- `QSplitter` - Resizable chat/options split
- `QScrollArea` - Scrollable chat display
- `QLabel` - Message bubbles, headers
- `QLineEdit` - Message input
- `QPushButton` - Send, Submit, Reset buttons
- `QRadioButton` - Option selection
- `QGroupBox` - Scenario panels
- `QButtonGroup` - Radio button management

### MQTT Integration:
- `paho.mqtt.client` - MQTT communication
- Topics:
  - Subscribe: `llama/driving/assistant_response/{session_id}`
  - Publish: `llama/driving/user_input/{session_id}`
  - Session: `llama/driving/session`

### Threading:
- Main GUI thread (PyQt event loop)
- MQTT network thread (client.loop_start())
- Message callbacks in GUI thread (Qt signals)

---

This design creates an engaging, intuitive interface that makes learning physics through conversation feel natural and fun! 🎮🏎️
