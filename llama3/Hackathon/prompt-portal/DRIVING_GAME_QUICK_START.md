# 🏁 Driving Game Scoring - Quick Start

## 🚀 5-Minute Setup

### 1. Run Migration (One-time)
```bash
cd Hackathon/prompt-portal/backend
python add_driving_game_columns.py
```

### 2. Start Testing
1. Go to **ChatBot** page
2. Select your prompt template
3. Check ✅ **"Driving Game Testing"**
4. Start conversation with Cap

### 3. Reach Consensus
Make sure your prompt outputs:
```
<EOS><PlayerOp:a><AgentOP:a>
```

### 4. Get Your Score! 🎉
- Modal popup shows your score
- Score automatically submitted to leaderboard
- View rankings in **Leaderboard → 🏁 Driving Game**

## 📊 Scoring Formula

```
Score = 1000 - (messages × 50) - seconds
Minimum: 100 points
```

**Pro Tip:** Fewer messages + faster consensus = Higher score! ⚡

## ✅ Required Output Format

Your prompt MUST make the agent output:
- `<EOS>` when consensus is reached
- `<PlayerOp:X>` where X is player's choice (a/b/c/d/custom)
- `<AgentOP:Y>` where Y is agent's choice (a/b/c/d)

**Example:**
```
Cap: "Okay, let's go with Power Boost!"
<EOS><PlayerOp:a><AgentOP:a>
```

## 🎯 Quick Test

1. Enable Driving Game mode
2. Say: "I choose Power Boost (option a)"
3. Wait for Cap's response with tags
4. Continue until both agree
5. See your score! 🏆

## 📈 View Leaderboard

**Leaderboard** → Select **"🏁 Driving Game"** → See rankings!

---

**That's it!** Start optimizing your prompts now! 🚀

