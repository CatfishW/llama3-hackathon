# 2D Maze Game: Red Blood Cell Adventure

This is a 2D maze game where you play as a red blood cell navigating through the human body. Your goal is to collect as much oxygen as possible and reach the blood vessel (end) as fast as possible. Avoid germs that can eat you and end the game!

## Features
- Play as a red blood cell in a maze
- Collect oxygen for points
- Avoid germs (enemies)
- Reach the blood vessel to win
- Time and oxygen collected contribute to your final score
- Beautiful 2D graphics and art assets

## Requirements
- Python 3.x
- pygame

## How to Run
1. Install Python 3.x
2. Install pygame:
   ```powershell
   pip install pygame
   ```
3. Run the game:
   ```powershell
   python main.py
   ```

## Art Assets
All art assets are located in the `assets/` folder.

## Controls
- Arrow keys: Move the red blood cell

## Credits
- Game developed using pygame
- Art assets created for this project

## LAM Prompt Template

```yaml
name: "Shortest-Path Advisor"
description: "Guide the player via text hints toward the exit using A*-like reasoning"
placeholders:
  - PLAYER_POS
  - EXIT_POS
  - VISIBLE_MAP
instructions: |
  You are a maze-guide. Given the player’s location {{PLAYER_POS}} and the exit at {{EXIT_POS}},
  compute the next best move that reduces distance. Speak concisely (1–2 sentences), e.g. “Turn
  left and proceed three tiles.”
action_schema:
  type: "chat_hint"
  max_tokens: 50
  temperature: 0.2
```

## New Feature: Path Visualization

The game now visually displays the fastest path from the player to the exit, as computed by an A* algorithm. This can be used by LAM to guide the player for higher scores.
