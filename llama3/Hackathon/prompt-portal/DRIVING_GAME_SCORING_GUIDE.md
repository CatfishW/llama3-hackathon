# Driving Game Scoring System - User Guide

## Overview

The **Driving Game Scoring System** allows users to test their prompt templates specifically designed for the "Cap" agent in physics learning scenarios. The system automatically detects when consensus is reached between the player and the agent, calculates a score, and submits it to the leaderboard.

## How It Works

### 1. Enable Driving Game Mode

In the **ChatBot** page (Chat Studio):

1. Select a prompt template from "My Prompt Template" dropdown
2. Enable "Driving Game Testing" checkbox
3. The mode will show as "🏁 Active" with a message counter

**Note:** You must have a template selected to enable Driving Game mode.

### 2. Interact with Cap

Start a conversation testing your prompt template:
- Send messages as you would in the actual driving game
- The system tracks:
  - Number of messages exchanged
  - Time elapsed since activation
  - Player and Agent option choices

### 3. Consensus Detection

The system automatically detects consensus when Cap's response contains:
- `<EOS>` tag (End of Session)
- `<PlayerOp:...>` tag (Player's chosen option)
- `<AgentOP:...>` tag (Agent's chosen option)

When both options match, consensus is reached!

### 4. Score Calculation

Your score is calculated using this formula:

```
Base Score: 1000 points
- Message Penalty: 50 points per message
- Time Penalty: 1 point per second
= Final Score (minimum 100)
```

**Higher scores mean:**
- Fewer messages needed to reach consensus
- Faster consensus achievement
- More efficient prompt template

### 5. Score Submission

When consensus is reached:
1. A modal popup appears showing:
   - Your final score
   - Number of messages
   - Your choice and Cap's choice
   - Confirmation that score was submitted
2. Choose to:
   - **🔄 Try Again** - Reset the session and try to improve your score
   - **Continue** - Close the modal and keep the conversation

### 6. Leaderboard

Visit the **Leaderboard** page to see rankings:

1. Select **🏁 Driving Game** mode in the filter
2. View all submitted scores sorted by highest score
3. See detailed metrics:
   - Messages count
   - Time taken
   - Consensus status

## Example Prompt Template

Here's a reference prompt template for the Driving Game agent:

```
You are Cap, a goofy, reckless, silly peer agent in a physics learning game.
You act like a funny but supportive classmate. You never reveal the "right answer."
You learn only from what the player says, and you push them—lightly and playfully—to
explain their reasoning about force, mass, and motion on a slope.

GOAL: Choose a different option than the player, argue playfully for your option,
and ask the player why they chose theirs. Keep questioning until both of you
explicitly align on the same option.

When consensus is reached, end with <EOS>; otherwise continue with <Cont>.

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE):
End every reply with all three tags in this order:
<Cont or EOS><PlayerOp:...><AgentOP:...>

PREDEFINED OPTIONS:
a: Power Boost — apply more force
b: Drop Oxygen — reduce mass
c: Keep Speed — no change
d: Pick Up More Oxygen — increase mass
```

## Tips for High Scores

1. **Clear Instructions**: Your prompt should clearly instruct the agent on how to detect player options
2. **Efficient Dialogue**: Design prompts that guide toward consensus without excessive back-and-forth
3. **Option Mapping**: Make sure your prompt can correctly identify player choices and map them to options
4. **Consensus Logic**: Clearly define when the agent should output `<EOS>` vs `<Cont>`

## Technical Details

### Backend Changes

- New database columns for Driving Game metrics:
  - `driving_game_consensus_reached` (boolean)
  - `driving_game_message_count` (integer)
  - `driving_game_duration_seconds` (float)
  - `driving_game_player_option` (string)
  - `driving_game_agent_option` (string)

- New mode type: `driving_game` for leaderboard filtering

### Frontend Features

- Driving Game mode toggle in Chat Studio
- Real-time message counting
- Automatic consensus detection via regex
- Animated modal popup for score display
- Leaderboard filtering by Driving Game mode

## Database Migration

To enable the new fields, run:

```bash
cd Hackathon/prompt-portal/backend
python add_driving_game_columns.py
```

## Troubleshooting

**Q: The checkbox is disabled**
A: Make sure you've selected a prompt template first

**Q: Consensus not detected**
A: Ensure your agent outputs the required tags in the exact format:
- `<EOS>` (not `<eos>` or `< EOS >`)
- `<PlayerOp:option>` and `<AgentOP:option>` with matching values

**Q: Score not showing on leaderboard**
A: Check that:
1. Database migration was run
2. Mode is set to "driving_game" when submitting
3. Template ID is valid

**Q: Modal doesn't appear**
A: Check browser console for errors. Ensure consensus tags are properly formatted in agent response.

## API Endpoints

### Submit Score
```
POST /api/leaderboard/submit
{
  "template_id": number,
  "session_id": string,
  "mode": "driving_game",
  "new_score": number,
  "driving_game_consensus_reached": true,
  "driving_game_message_count": number,
  "driving_game_duration_seconds": number,
  "driving_game_player_option": string,
  "driving_game_agent_option": string
}
```

### Get Leaderboard
```
GET /api/leaderboard?mode=driving_game&limit=50&skip=0
```

## Future Enhancements

Potential improvements:
- Multiple physics scenarios (not just hill climb)
- Different scoring algorithms per scenario
- Score breakdown visualization
- Template comparison analytics
- Export detailed session logs

---

**Happy Testing!** 🎮🏁

