# New Comprehensive Scoring System

## Overview

The new scoring system has been implemented to provide more accurate and fair evaluation based on comprehensive performance metrics. All historical scores are preserved as "deprecated scores" for reference.

## Key Changes

### 1. Time-Based Deduction
- **Continuous Penalty**: Score decreases by **1 point every 10 seconds** during gameplay
- This encourages faster completion while still allowing strategic play

### 2. Comprehensive Metrics Tracking

The system now tracks and evaluates:

#### Path Efficiency (PE)
- **Formula**: `optimal_steps / total_steps`
- **Good**: ≥ 0.85
- **Weight**: 1500 points maximum
- Rewards efficient pathfinding without excessive wandering

#### Backtrack Ratio (BR)
- **Formula**: `backtrack_count / total_steps`
- **Good**: ≤ 10%
- **Penalty**: Up to -1000 points
- Penalizes revisiting the same tiles unnecessarily

#### Collision Rate (CR)
- **Formula**: `collision_count / total_steps`
- **Good**: = 0 (no wall collisions)
- **Penalty**: Up to -1500 points
- Encourages careful navigation

#### Latency per Step (L)
- **Formula**: Average time between actions (milliseconds)
- **Good**: ≤ 400 ms
- **Bonus**: +1000 points for good latency
- **Penalty**: Up to -800 points for slow actions
- Measures decision-making speed

#### Oxygen Collection
- **Points**: 150 per oxygen collected
- Increased from 100 in the old system

#### Completion Bonuses
- **Base Completion**: 5000 points for winning
- **Success Rate Bonus**: 2000 points for completion
- **Speed Bonus**: Up to 1000 additional points for finishing under 60 seconds

#### Mode Multipliers
- **LAM Mode**: 1.5x multiplier (AI-controlled)
- **Manual Mode**: 1.0x multiplier (player-controlled)

#### Difficulty Scaling
- **Germ Factor**: 1.0 to 1.3x based on number of germs
- More germs = higher multiplier = higher potential score

## Database Schema Updates

### New Columns in `scores` Table:
- `new_score` (FLOAT, nullable): The new comprehensive score
- `total_steps` (INTEGER, nullable): Total steps taken
- `optimal_steps` (INTEGER, nullable): BFS shortest path length
- `backtrack_count` (INTEGER, nullable): Number of tile revisits
- `collision_count` (INTEGER, nullable): Number of wall collisions
- `dead_end_entries` (INTEGER, nullable): Reserved for future use
- `avg_latency_ms` (FLOAT, nullable): Average action latency

### Legacy Support:
- `score` (FLOAT): Preserved as "deprecated score" for historical comparison
- All existing scores remain viewable with NULL for new_score

## Leaderboard Display

### New Score (Primary)
- Displayed prominently in **green** with "NEW" badge
- Used for sorting and ranking
- Shows comprehensive performance

### Old Score (Deprecated)
- Displayed in **yellow** with reduced opacity
- Labeled as "(deprecated)"
- Preserved for historical comparison

### Metrics Display
- Shows steps taken and collision count
- Color-coded: green for good, red for poor performance

## Score Calculation Formula

```typescript
newScore = (
  // Base completion bonus
  5000 (if win) +
  2000 (success rate bonus) +
  
  // Path efficiency bonus
  (optimal_steps / total_steps) * 1500 +
  
  // Penalties
  - (backtrack_ratio * 5000) // up to -1000
  - (collision_rate * 6000)   // up to -1500
  - (latency penalty)          // up to -800
  - (elapsed_time / 10)        // -1 per 10 seconds
  
  // Bonuses
  + (oxygen_collected * 150) +
  + (speed_bonus) // up to 1000 for fast completion
  
) * mode_multiplier * germ_factor
```

## Migration Steps

### 1. Run Database Migration
```bash
cd backend
python add_new_score_column.py
```

This will:
- Add new_score and metrics columns to the scores table
- Preserve all existing data
- Set new_score to NULL for historical scores

### 2. Restart Backend
```bash
cd backend
python run_server.py
```

### 3. Test the System
1. Play a game in either manual or LAM mode
2. Complete or fail the game
3. Check that score submission succeeds
4. View the leaderboard to see both old and new scores

## Implementation Details

### Frontend Changes (`WebGame.tsx`)
- Added comprehensive metrics tracking in game state
- Track total steps, collisions, backtracks, and latencies
- Calculate both old and new scores on game over
- Submit both scores to the backend

### Backend Changes (`models.py`, `schemas.py`, `leaderboard.py`)
- Extended Score model with new fields
- Updated API schemas to include new_score
- Modified leaderboard sorting to prioritize new_score
- NULL new_score values sorted to the bottom

### Leaderboard Changes (`Leaderboard.tsx`)
- Display both score columns
- Visual distinction between new (green) and old (yellow) scores
- Show performance metrics when available
- Responsive design maintained

## Benefits

1. **More Fair Evaluation**: Rewards efficient play, not just completion
2. **Detailed Feedback**: Players can see exactly where they excelled or struggled
3. **Historical Preservation**: Old scores remain for comparison
4. **Scalable**: Easy to add more metrics in the future
5. **Time Pressure**: Continuous deduction adds urgency without being punishing

## Future Enhancements

Potential additions based on the metrics framework:

- **Dead-end Detection**: Track and penalize entering dead ends
- **Steps Variability (σ)**: Measure consistency across multiple runs
- **Format Compliance**: Track valid vs invalid actions
- **Recovery Time**: Measure steps to recover from errors
- **Robustness Testing**: Score stability under different conditions

## Troubleshooting

### "Column does not exist" error
Run the migration script: `python backend/add_new_score_column.py`

### Old scores showing NULL for new_score
This is expected. Only games played after the update will have new scores.

### Leaderboard sorting seems off
The system sorts by new_score first (NULLs last), then old score, then creation time.

## Questions?

For issues or suggestions about the scoring system, please check the project documentation or contact the development team.
