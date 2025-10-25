# 🎮 Maze LAM Quick Reference Card

## 🚀 Getting Started (30 seconds)

1. **LAM is running** → Game sends states automatically
2. **Submit your prompt** → `maze/template/{your_session_id}`
3. **Play & iterate** → Refine prompt based on performance

---

## 📤 Submit a Prompt Template

### MQTT Topic
```
maze/template/{session_id}
```

### Payload
```json
{
  "template": "Your system prompt here...",
  "reset": true,
  "max_breaks": 3
}
```

### Example
```json
{
  "template": "You are a maze AI. Output JSON: {\"path\": [[x,y],...], \"hint\": \"text\", \"break_wall\": [x,y]}. Avoid germs, collect oxygen, reach exit efficiently.",
  "reset": true
}
```

---

## 📥 Guidance Response Format

### Topic
```
maze/hint/{session_id}
```

### Response
```json
{
  "path": [[x1,y1], [x2,y2], ...],     // Required: Full path
  "hint": "Strategic advice",           // Optional: Text guidance
  "break_wall": [x, y],                 // Optional: Wall to break
  "breaks_remaining": 2,                // Breaks left
  "response_time_ms": 234,              // LLM speed
  "session_stats": {                    // Your performance
    "requests": 10,
    "errors": 1,
    "avg_response_ms": 287
  }
}
```

---

## 📊 Check Your Stats

### Topic
```
maze/stats/{session_id}
```

### Payload
```json
{}
```

### Response
```json
{
  "session_id": "abc123",
  "prompt_length": 156,
  "breaks_remaining": 3,
  "stats": {
    "requests": 10,
    "errors": 1,
    "avg_response_ms": 287
  }
}
```

---

## 🎯 Prompt Engineering Cheat Sheet

### ✅ DO
- ✅ Be specific about JSON format
- ✅ Use numbers ("distance ≤ 2" not "very close")
- ✅ Set clear priorities (safety > efficiency > collection)
- ✅ Handle edge cases (no path, at exit, etc.)
- ✅ Keep it under 1000 chars for speed

### ❌ DON'T
- ❌ Make it too vague ("be smart about it")
- ❌ Forget to specify JSON output format
- ❌ Overload with unnecessary details
- ❌ Exceed 10,000 chars (will be truncated)
- ❌ Forget error handling instructions

---

## 🏆 Optimization Workflow

```
1. Start with basic prompt
   ↓
2. Play 5-10 mazes
   ↓
3. Check stats (errors, response time)
   ↓
4. Identify failure patterns
   ↓
5. Refine prompt (one change at a time)
   ↓
6. Repeat until optimal
```

---

## 🎨 Starter Prompt Templates

### 🥉 Bronze (Basic)
```
You are a maze AI. Output JSON only:
{"path": [[x,y],...], "hint": "text", "break_wall": [x,y]}
Analyze player_pos, exit_pos, visible_map (0=wall, 1=floor), germs, oxygen.
Provide shortest path to exit.
```

### 🥈 Silver (Strategic)
```
You are a maze AI. Analyze state and output JSON:
{"path": [[x,y],...], "hint": "text", "break_wall": [x,y]}

Priorities:
1. Avoid germs (stay >2 cells away)
2. Shortest safe path to exit
3. Collect oxygen if adds <5 steps
4. Use breaks for >10 step shortcuts

State: player_pos, exit_pos, visible_map, germs, oxygen, breaks_remaining
```

### 🥇 Gold (Advanced)
```
You are an expert maze AI. Output JSON only:
{"path": [[x,y],...], "hint": "strategic summary", "break_wall": [x,y]}

Strategy:
- Safety: Distance to nearest germ:
  • <2 cells: Emergency escape, use breaks if needed
  • 2-3 cells: Defensive path, avoid closer approach
  • >3 cells: Optimal efficiency path
- Resources:
  • Oxygen: Collect if path adds ≤5 steps AND not in danger
  • Breaks: Use if saves ≥8 steps OR critical escape
- Efficiency: Shortest safe path, minimize turns

Analyze: player_pos, exit_pos, visible_map (0=wall, 1=floor), germs (danger), oxygen (bonus), breaks_remaining (resource)
```

---

## 🐛 Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| Invalid JSON | Add "Output ONLY valid JSON. No explanations." |
| Slow response | Shorten prompt, reduce complexity |
| Ignores germs | Add numeric distance thresholds |
| Never uses breaks | Add specific break conditions with numbers |
| Path too long | Add "shortest path" priority |
| Collects oxygen unsafely | Add safety conditions for collection |

---

## 📈 Performance Targets

| Metric | Good | Great | Excellent |
|--------|------|-------|-----------|
| Response time | <500ms | <300ms | <200ms |
| Error rate | <10% | <5% | <2% |
| Avg path length | <30 steps | <20 steps | <15 steps |
| Maze completion | 60% | 80% | 95% |

---

## 🔥 Pro Tips

1. **Test incrementally**: Add one feature at a time
2. **Use concrete numbers**: "≤2" beats "very close"
3. **Monitor stats**: Check `response_time_ms` and `errors`
4. **A/B test**: Try two prompts, compare results
5. **Learn from logs**: Check `debug_dialogs/` on failures

---

## 🆘 Emergency Fallback

If your prompt fails completely:
```json
{
  "template": "Output JSON: {\"path\": [[x,y],...]}. Shortest path from player_pos to exit_pos. Avoid germs. JSON only.",
  "reset": true
}
```

---

## 📞 Support

- Check logs: Server console shows errors
- Debug files: `debug_dialogs/` folder
- Stats endpoint: `maze/stats/{session_id}`
- Guide: Read `MAZE_LAM_GUIDE.md` for details

---

**Remember**: No conversation memory = Every move is independent = Your prompt IS your strategy! 🎯
