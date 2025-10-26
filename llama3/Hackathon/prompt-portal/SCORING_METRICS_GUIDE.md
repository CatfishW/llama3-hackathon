# Scoring Metrics Quick Reference

## Score Components

| Component | Good Threshold | Weight | Description |
|-----------|---------------|--------|-------------|
| **Base Completion** | Win | 5000 pts | Base reward for completing the maze |
| **Success Rate Bonus** | 100% | 2000 pts | Additional completion bonus |
| **Path Efficiency** | ≥ 0.85 | Up to 1500 pts | Optimal path length / actual steps |
| **Backtrack Ratio** | ≤ 10% | -1000 pts max | Penalty for revisiting tiles |
| **Collision Rate** | = 0 | -1500 pts max | Penalty for hitting walls |
| **Avg Latency** | ≤ 400 ms | +1000 / -800 pts | Decision speed bonus/penalty |
| **Oxygen Collection** | More is better | 150 pts each | Resource gathering bonus |
| **Time Deduction** | Faster is better | -1 per 10 sec | Continuous time penalty |
| **Speed Bonus** | < 60 seconds | Up to 1000 pts | Fast completion reward |

## Multipliers

| Factor | Range | Description |
|--------|-------|-------------|
| **LAM Mode** | 1.5x | AI-controlled mode bonus |
| **Manual Mode** | 1.0x | Player-controlled baseline |
| **Germ Factor** | 1.0x - 1.3x | More germs = higher multiplier |

## Example Calculations

### Perfect Run (LAM Mode)
```
Base: 5000
Success: 2000
Path Efficiency (0.95): 1425
Oxygen (5 collected): 750
Latency Bonus: 1000
Speed Bonus (40 sec): 333
Time Deduction (40 sec): -4
Total before multipliers: 10,504
× LAM Mode (1.5): 15,756
× Germ Factor (1.2): 18,907 points
```

### Average Run (Manual Mode)
```
Base: 5000
Success: 2000
Path Efficiency (0.70): 1050
Backtrack Penalty (15%): -250
Oxygen (3 collected): 450
Speed Bonus (90 sec): 0
Time Deduction (90 sec): -9
Total before multipliers: 8,241
× Manual Mode (1.0): 8,241
× Germ Factor (1.1): 9,065 points
```

### Failed Run
```
Base: 0 (no win)
Success: 0
Oxygen (2 collected): 300
Collision Penalty: -600
Time Deduction (45 sec): -5
Total: -305 → 0 points (minimum)
```

## Tips to Maximize Score

### 🎯 Path Efficiency
- Plan your route before moving
- Use LAM hints in LAM mode
- Minimize backtracking

### ⚡ Speed
- Act quickly but carefully
- Time deduction is continuous (-1 per 10 sec)
- Finish under 60 seconds for speed bonus

### 🛡️ Avoid Penalties
- Don't hit walls (collision penalty)
- Don't revisit tiles (backtrack penalty)
- Keep action latency under 400ms

### 💰 Maximize Bonuses
- Collect all oxygen (+150 each)
- Play LAM mode for 1.5x multiplier
- More germs = higher difficulty = higher multiplier

## Metric Ranges

| Metric | Excellent | Good | Average | Poor |
|--------|-----------|------|---------|------|
| Path Efficiency | > 0.90 | 0.85-0.90 | 0.70-0.85 | < 0.70 |
| Backtrack Ratio | 0% | < 5% | 5-10% | > 10% |
| Collision Count | 0 | 1-2 | 3-5 | > 5 |
| Avg Latency | < 300ms | 300-400ms | 400-600ms | > 600ms |
| Completion Time | < 40s | 40-60s | 60-90s | > 90s |

## Score Interpretation

| Score Range | Rating | Description |
|-------------|--------|-------------|
| 15,000+ | 🏆 Exceptional | Near-perfect run with high efficiency |
| 10,000-15,000 | ⭐ Excellent | Very good performance, few mistakes |
| 7,000-10,000 | 👍 Good | Solid completion with room for improvement |
| 5,000-7,000 | ✅ Average | Completed but inefficiently |
| 2,000-5,000 | 📊 Below Average | Many penalties or very slow |
| 0-2,000 | 💀 Poor | Failed or very inefficient |

## Legacy vs New Scoring

### Old System (Deprecated)
- Simple: oxygen + win bonus + time bonus
- Limited feedback
- Less fair for difficult mazes

### New System
- Comprehensive: 10+ factors considered
- Detailed performance metrics
- Fairer across different difficulty levels
- Continuous time pressure
- Better competitive balance

## Migration Note

All historical scores are preserved as "Deprecated Score" in the leaderboard. New scores will be calculated using the comprehensive system and displayed as "New Score" with metrics.
