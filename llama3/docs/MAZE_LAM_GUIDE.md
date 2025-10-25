# Maze LAM Hackathon Guide

## 🎮 How It Works

This is a **stateless Large Action Model (LAM)** that helps you navigate mazes. The key innovation: **NO CONVERSATION MEMORY** - each guidance request is completely independent. Your success depends entirely on crafting the perfect **prompt template**.

### Core Concept
- **Your Prompt = Your Strategy**: The system prompt you provide determines how the LLM analyzes game states
- **Stateless Processing**: Each turn, the LLM sees only your prompt + current game state (no history)
- **Iterate & Optimize**: Refine your prompt based on performance stats and results

## 🚀 Quick Start

### 1. Run the LAM Server

```bash
# For Llama models
torchrun --nproc_per_node 1 lam_mqtt_hackathon_deploy.py \
  --model_type llama \
  --ckpt_dir Llama3.1-8B-Instruct \
  --tokenizer_path Llama3.1-8B-Instruct/tokenizer.model \
  --max_batch_size 2 \
  --mqtt_username YourUsername \
  --mqtt_password YourPassword

# For Phi models (smaller, faster)
python lam_mqtt_hackathon_deploy.py \
  --model_type phi \
  --hf_model microsoft/phi-1_5 \
  --mqtt_username YourUsername \
  --mqtt_password YourPassword
```

### 2. Submit Your Prompt Template

Send to MQTT topic `maze/template` or `maze/template/{session_id}`:

```json
{
  "template": "Your strategic system prompt here...",
  "reset": true,
  "max_breaks": 3
}
```

### 3. Play and Iterate

The game automatically sends state updates to `maze/state`, and the LAM responds with guidance on `maze/hint/{session_id}`.

## 📝 Prompt Engineering Tips

### Essential Elements

Your prompt should guide the LLM to:
1. **Parse the state correctly** (player_pos, exit_pos, visible_map, germs, oxygen, breaks_remaining)
2. **Output valid JSON** with required fields (path, hint, break_wall)
3. **Apply strategy** (avoid germs, collect oxygen, use breaks wisely)

### Example Prompt Templates

#### Basic Template (Good Starting Point)
```
You are a maze navigation AI. Given the current game state, output JSON with:
- "path": array of [x,y] coordinates from player to exit
- "hint": brief strategic advice (optional)
- "break_wall": [x,y] to break a wall if helpful (optional)

Analyze the visible_map (0=wall, 1=floor), avoid germs, collect oxygen when safe.
Always output valid JSON only.
```

#### Advanced Template (More Strategic)
```
You are an expert maze solver. Analyze the state and provide optimal guidance.

Strategy priorities:
1. Safety: Avoid germs (high priority if distance ≤ 3)
2. Efficiency: Shortest safe path to exit
3. Resources: Collect oxygen if path doesn't add >5 steps
4. Wall breaks: Use only for shortcuts >10 steps or critical escapes

Output format (JSON only):
{
  "path": [[x1,y1], ...],      // Full path from player to exit
  "hint": "Strategy summary",   // Brief explanation
  "break_wall": [x, y]          // Only if saves >5 steps
}

Current state fields:
- player_pos, exit_pos, visible_map (0=wall, 1=floor)
- germs: positions to avoid, oxygen: power-ups to collect
- breaks_remaining: wall breaks available
```

#### Specialized Template (Germ Avoidance Focus)
```
You are a defensive maze navigator specializing in germ avoidance.

Rules:
1. Never plan paths closer than 2 cells to any germ
2. If no safe path exists, use wall breaks to create escape routes
3. Prioritize oxygen collection to extend survival time
4. Output JSON: {"path": [...], "hint": "...", "break_wall": [x,y]}

Analyze visible_map (0=wall, 1=floor), germs list, player_pos, exit_pos.
```

## 📊 Performance Monitoring

### View Session Stats

Send to `maze/stats/{session_id}`:
```json
{}
```

Response includes:
- `requests`: Total guidance requests
- `errors`: Failed generations
- `avg_response_ms`: Average response time
- `prompt_length`: Current template size
- `breaks_remaining`: Remaining wall breaks

### Metrics to Track

1. **Response Time**: Faster = better player experience (aim for <500ms)
2. **Error Rate**: Lower = more robust prompt design
3. **Path Length**: Shorter paths = better efficiency
4. **Success Rate**: Track maze completions with your prompt

## 🎯 Output Format

### Guidance Object (Sent to `maze/hint/{session_id}`)

```json
{
  "path": [[x1, y1], [x2, y2], ...],
  "hint": "Strategic advice text",
  "break_wall": [x, y],
  "breaks_remaining": 3,
  "show_path": true,
  "highlight_zone": [[x1,y1], ...],
  "highlight_ms": 6000,
  "freeze_germs_ms": 2500,
  "slow_germs_ms": 3000,
  "speed_boost_ms": 2000,
  "oxygen_hint": "💨 Oxygen at [5,3], 4 steps away",
  "response_time_ms": 234,
  "session_stats": {
    "requests": 15,
    "errors": 1,
    "avg_response_ms": 287
  }
}
```

### Field Descriptions

- **path** (required): Complete path from player to exit
- **hint** (optional): Text guidance for player
- **break_wall** (optional): Suggest wall to break [x, y]
- **show_path** (default true): Display path overlay
- **highlight_zone**: Cells to highlight (next 15 steps)
- **freeze_germs_ms**: Duration to freeze germs (danger response)
- **slow_germs_ms**: Duration to slow germs (caution response)
- **speed_boost_ms**: Player speed boost duration
- **oxygen_hint**: Hint about nearby oxygen pellets
- **session_stats**: Real-time performance metrics

## 🔧 Advanced Features

### Dynamic Game Effects

The LAM automatically adds game effects based on situation:
- **Freeze germs** (2.5s): When germs are ≤2 cells away
- **Slow germs** (3s): When germs are ≤3 cells away
- **Speed boost** (2s): For long paths (≥25 steps) or near exit
- **Highlight zone**: Shows next 15 path steps
- **Oxygen hints**: Suggests nearby oxygen (≤6 steps away)

### Session Management

- **Stateless Design**: No conversation history = predictable, fast responses
- **Per-Session Prompts**: Each session can have unique prompts
- **Global Prompts**: Apply one prompt to all sessions
- **Break Tracking**: Each session independently tracks wall breaks

## 🐛 Troubleshooting

### Common Issues

1. **LLM returns invalid JSON**
   - Solution: Make your prompt more explicit about JSON format
   - Fallback: System automatically computes valid path

2. **Responses too slow**
   - Use smaller model (phi-1_5 instead of llama)
   - Reduce prompt length
   - Decrease max_gen_len parameter

3. **Paths avoid germs too conservatively**
   - Adjust your prompt's distance thresholds
   - Add risk/reward logic

4. **Wall breaks not used effectively**
   - Make break conditions more explicit in prompt
   - Set numeric thresholds (e.g., "use if saves >5 steps")

### Debug Mode

Check `debug_dialogs/` folder for saved request/response pairs when LLM fails.

## 🏆 Optimization Strategies

### Prompt Length vs Quality
- Longer prompts ≠ better results
- Focus on clear, specific instructions
- Test with different lengths to find sweet spot

### Temperature & Top-P
- Lower temperature (0.3-0.5) = more consistent paths
- Higher temperature (0.7-0.9) = more creative solutions
- Default: temperature=0.6, top_p=0.9

### Iterative Refinement
1. Start with basic prompt
2. Play several mazes, collect stats
3. Identify failure patterns
4. Refine prompt to address failures
5. A/B test different versions

## 📡 MQTT Topics Reference

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `maze/state` | Game → LAM | Current game state |
| `maze/hint/{session_id}` | LAM → Game | Guidance output |
| `maze/template` | Client → LAM | Global prompt update |
| `maze/template/{session_id}` | Client → LAM | Session prompt update |
| `maze/stats/{session_id}` | Client → LAM | Request stats |

## 🎓 Learning Resources

### Prompt Engineering Principles
1. **Specificity**: Be explicit about output format
2. **Context**: Provide all necessary state interpretation
3. **Constraints**: Set clear boundaries (avoid germs, use breaks wisely)
4. **Examples**: Include format examples in your prompt
5. **Priorities**: Rank goals (safety > efficiency > collection)

### Best Practices
- Test prompts incrementally (add one feature at a time)
- Monitor error rates to catch prompt issues early
- Use session stats to measure improvement
- Share successful prompts with your team

---

## 💡 Pro Tips

1. **Start simple**: Get basic path generation working, then add strategy
2. **Use numbers**: Specific thresholds work better than vague terms ("distance ≤ 2" vs "very close")
3. **Handle edge cases**: What if no safe path exists? What if at exit already?
4. **Test systematically**: Change one variable at a time
5. **Learn from errors**: Check debug logs to see what the LLM actually generated

Good luck optimizing your maze strategy! 🎮✨
