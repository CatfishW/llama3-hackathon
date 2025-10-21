# Blood Racing Game - Setup Guide

A physics-based racing game with an AI co-pilot (Cap) powered by LLM. Player and Cap race together, making decisions about force, mass, and motion through interactive conversations.

## Architecture

The game consists of two main components:

1. **MQTT Server (`mqtt_deploy_driving_scene4.py`)**: Runs the LLM backend (Llama or QwQ model) that powers Cap's personality and physics reasoning
2. **Game Client (`racing_game_client.py`)**: WeChat-style GUI where players chat with Cap and make racing decisions

## Prerequisites

- Python 3.8+
- CUDA-capable GPU (for running LLM server)
- MQTT Broker running at `47.89.252.2:1883` (or update broker address in code)

## Installation

### 1. Install Server Dependencies

```powershell
# Install PyTorch with CUDA support (adjust for your CUDA version)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other server dependencies
pip install -r requirements.txt
```

### 2. Install Client Dependencies

```powershell
pip install -r requirements_client.txt
```

## Running the Game

### Step 1: Start the MQTT LLM Server

You have two options for the backend model:

#### Option A: Llama Model (Local)

```powershell
torchrun --nproc_per_node 1 mqtt_deploy_driving_scene4.py --model_type llama --ckpt_dir Llama3.1-8B-Instruct --tokenizer_path Llama3.1-8B-Instruct/tokenizer.model --max_batch_size 4 --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
```

#### Option B: QwQ Model (Hugging Face)

**Full Precision (requires ~60GB+ GPU memory):**
```powershell
python mqtt_deploy_driving_scene4.py --model_type qwq --model_name Qwen/QwQ-32B --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
```

**4-bit Quantized (requires ~20GB GPU memory):**
```powershell
python mqtt_deploy_driving_scene4.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 4bit --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
```

**8-bit Quantized (requires ~35GB GPU memory):**
```powershell
python mqtt_deploy_driving_scene4.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 8bit --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
```

### Step 2: Launch the Game Client

In a new terminal:

```powershell
python racing_game_client.py
```

## Game Features

### 🎮 Chat Interface
- **WeChat-style bubbles**: User messages in green (right), Cap's messages in white (left)
- **Real-time conversation**: Chat with Cap about racing strategies
- **Session management**: Each game session maintains conversation history

### 🏁 Racing Scenarios

#### 1. ⛰️ Hill Climb Event
Options:
- **a) Power Boost** (more force) - Best choice
- **b) Drop Oxygen** (less mass) - Good choice
- **c) Keep Speed** (no change) - Poor choice
- **d) Pick Up More Oxygen** (more mass) - Worst choice

Physics concept: F = ma and gravity on slopes

#### 2. 💧 Slippery Road Event
Options:
- **a) Cut the engine** (coast) - Best choice
- **b) Gently brake** - Good choice
- **c) Slow & steer around** - Poor choice
- **d) Accelerate through** - Worst choice

Physics concept: Friction and Newton's First Law

#### 3. 🚧 Blockage Event
Options:
- **a) Collect O₂ then ram** (more mass) - Best choice
- **b) Full speed ahead** - Good choice
- **c) Drop O₂ then ram** (less mass) - Poor choice
- **d) Slow push gently** - Worst choice

Physics concept: Momentum and force

### 🤖 Cap's Personality

Cap is your goofy, reckless co-pilot who:
- Never directly gives the right answer
- Always picks a different option from you initially
- Argues playfully for their choice
- Asks questions to make you explain physics principles
- Eventually reaches consensus through discussion

### 🎯 How to Play

1. **Select a scenario**: Click on one of the three event panels on the right
2. **Choose your option**: Select a radio button and click "Submit Choice"
3. **Chat with Cap**: Cap will challenge your choice - explain your reasoning!
4. **Reach consensus**: Keep discussing until you both agree (marked with <EOS>)
5. **Execute**: Once consensus is reached, the game applies your choice

## Message Flow

```
Player → [racing_game_client.py] → MQTT Topic: llama/driving/user_input/{session_id}
                                         ↓
                                   [mqtt_deploy_driving_scene4.py]
                                         ↓
                                      LLM Model (Llama/QwQ)
                                         ↓
                                   MQTT Topic: llama/driving/assistant_response/{session_id}
                                         ↓
Cap's Response ← [racing_game_client.py]
```

## Technical Details

### System Prompt Structure

Cap follows these rules:
- Maps player choices to options {a, b, c, d} or custom
- Always picks a different option initially
- Uses physics-based questioning
- Tracks state with tags: `<Cont>` or `<EOS>`, `<PlayerOp:x>`, `<AgentOP:y>`
- Reaches `<EOS>` only when both agree

### Session Management

- Each client gets a unique session ID
- Server maintains up to 30 concurrent sessions
- Oldest sessions auto-expire when limit is reached
- Dialog history is trimmed to fit `max_history_tokens`

### Performance Tuning

Server parameters you can adjust:
- `--max_batch_size`: Number of concurrent inference batches (default: 4)
- `--max_history_tokens`: Max tokens in conversation history (default: 1500)
- `--num_workers`: Worker threads for processing (default: 4)
- `--use_batching`: Enable batch processing (default: True)
- `--temperature`: Sampling temperature (default: 0.6)
- `--top_p`: Nucleus sampling parameter (default: 0.9)

## Troubleshooting

### Client won't connect
- Check MQTT broker is running at `47.89.252.2:1883`
- Verify username/password: `TangClinic` / `Tang123`
- Check firewall settings

### Server crashes with OOM
- Try using quantization: `--quantization 4bit`
- Reduce `--max_batch_size`
- Reduce `--max_history_tokens`

### Cap's responses are cut off
- Increase `--max_gen_len` (default: None = model default)
- Check `--max_seq_len` is sufficient (default: 2048)

### No response from Cap
- Check server terminal for errors
- Verify session ID in client status bar
- Try creating a new session with "🔄 New Session" button

## Game Design Document Reference

This implementation follows the Blood Racing Game Design Document, featuring:
- Opening & Launch sequence
- Routine Run with Force button
- Three main events (Hill Climb, Slippery Road, Blockage)
- Final Sprint & Finish
- Player vs RBC races (to be implemented in full game client)

## Future Enhancements

- [ ] Full racing visualization with car animations
- [ ] RBC opponent AI
- [ ] Scoreboard and timing system
- [ ] Sound effects and background music
- [ ] Multi-player support
- [ ] Achievement system
- [ ] Replay system

## Credits

Developed for physics education through interactive gaming.

---

**Ready to race? Start the server, launch the client, and let's go! 🏎️💨**
