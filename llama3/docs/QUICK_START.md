# 🏎️ Blood Racing - Quick Start Guide

## What You Have

✅ **Racing Game Client** - WeChat-style chat interface (`racing_game_client.py`)
✅ **MQTT LLM Server** - Already configured (`mqtt_deploy_driving_scene4.py`)
✅ **System Prompt** - Cap's personality integrated

## Start Playing in 2 Steps

### Step 1: Start the Server (if not already running)

The server is already configured with Cap's personality. Choose your model:

**For Llama (if you have local model):**
```powershell
torchrun --nproc_per_node 1 mqtt_deploy_driving_scene4.py --model_type llama --ckpt_dir Llama3.1-8B-Instruct --tokenizer_path Llama3.1-8B-Instruct/tokenizer.model --max_batch_size 4 --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
```

**For QwQ with 4-bit quantization (recommended):**
```powershell
python mqtt_deploy_driving_scene4.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 4bit --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
```

### Step 2: Launch the Client

**Option A - Double-click:**
```
launch_client.bat
```

**Option B - Command line:**
```powershell
python racing_game_client.py
```

## How to Play

### 🎯 The Game Window

```
┌─────────────────────────────────────────────────────────────┐
│  🏎️ Chat with Cap (Co-pilot)                                │
├─────────────────────────┬───────────────────────────────────┤
│                         │  🎮 Game Scenarios                │
│   Chat Messages         │                                   │
│   (WeChat style)        │  ⛰️ Hill Climb Event              │
│                         │  ○ a: Power Boost (more force)    │
│   User: Green bubbles → │  ○ b: Drop Oxygen (less mass)     │
│ ← Cap: White bubbles    │  ○ c: Keep Speed (no change)      │
│                         │  ○ d: Pick Up More Oxygen         │
│                         │  [Submit Choice]                  │
│                         │                                   │
│                         │  💧 Slippery Road Event           │
│                         │  ...                              │
│                         │                                   │
│                         │  🚧 Blockage Event                │
│                         │  ...                              │
├─────────────────────────┴───────────────────────────────────┤
│  Type your message...              [Send]                   │
└─────────────────────────────────────────────────────────────┘
```

### 📝 Playing the Game

1. **Choose a scenario** - Select one of three events on the right panel
2. **Pick your option** - Click a radio button and press "Submit Choice"
3. **Chat with Cap** - He'll challenge your choice! Explain your reasoning
4. **Reach consensus** - Keep discussing physics until you agree
5. **See the outcome** - When you see `<EOS>`, consensus is reached! 🎉

### 💡 Example Conversation

```
You: For the hill climb, I choose Power Boost (more force)

Cap: I'd drop oxygen instead—lighter climbs cleaner. Why is more 
     force better here?
     <Cont><PlayerOp:a><AgentOP:b>

You: Because we need to overcome gravity pulling us backward. More 
     force means more acceleration up the slope according to F=ma.

Cap: Okay, that makes sense! More force beats gravity's pull. I'm 
     with Power Boost now—let's charge the hill.
     <EOS><PlayerOp:a><AgentOP:a>
```

## Understanding Cap's Responses

Cap's responses end with three tags:

- `<Cont>` - Discussion continues
- `<EOS>` - End Of Session, consensus reached! ✅
- `<PlayerOp:x>` - Your current choice (a/b/c/d or custom)
- `<AgentOP:y>` - Cap's current choice (a/b/c/d)

When both match → `<EOS>` → Decision made!

## Features

### ✨ WeChat-Style Interface
- Beautiful message bubbles (green for you, white for Cap)
- Smooth scrolling chat
- Professional, clean design

### 🧠 Smart AI Co-pilot
- Cap never gives direct answers
- Always challenges your thinking
- Uses physics principles (F=ma, momentum, friction)
- Goofy but supportive personality

### 🎮 Three Racing Scenarios
- **Hill Climb** - Learn about force vs mass on slopes
- **Slippery Road** - Understand friction and inertia
- **Blockage** - Master momentum concepts

### 🔄 Session Management
- Automatic session creation
- Maintains conversation history
- "New Session" button to start fresh

## Keyboard Shortcuts

- `Enter` - Send message
- `Escape` - Clear input field (when focused)

## Status Indicators

- 🟢 **Connected ✓** - Ready to play!
- 🔴 **Disconnected** - Check server connection
- 🟡 **Connecting...** - Please wait

## Tips for Best Experience

1. **Explain your reasoning** - Don't just pick options, tell Cap WHY
2. **Use physics terms** - Force, mass, acceleration, friction, momentum
3. **Ask questions back** - "What about gravity?" "Why lighter?"
4. **Be patient** - LLM responses may take 2-10 seconds
5. **Have fun!** - Cap's goofy personality makes learning physics enjoyable

## Troubleshooting

**Problem: "Status: Disconnected"**
- Check if MQTT server is running
- Verify broker address: `47.89.252.2:1883`

**Problem: No response from Cap**
- Wait 10-15 seconds (LLM may be processing)
- Check server terminal for errors
- Try "🔄 New Session" button

**Problem: Window doesn't open**
- Make sure PyQt5 is installed: `pip install PyQt5`
- Run `launch_client.bat`

**Problem: Cap's responses are incomplete**
- Server may need more memory
- Try reducing `--max_history_tokens` on server

## Game Design Philosophy

This game teaches physics through **peer learning**:
- Cap is your equal, not a teacher
- You convince each other through discussion
- Multiple valid reasoning paths
- Focus on understanding, not "right answers"

## Next Steps

After mastering the chat interface:
1. Full racing visualization (planned)
2. Multiple races with RBC opponents
3. Scoreboard and achievements
4. Multiplayer mode

---

**Have fun racing and learning physics with Cap! 🏎️💨**

Need help? Check `RACING_GAME_README.md` for detailed documentation.
