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
name: "Maze Action Planner"
description: "Return strict JSON with path or actions; optionally request BFS to move exactly N tiles"
placeholders:
  - PLAYER_POS
  - EXIT_POS
  - VISIBLE_MAP
instructions: |
  You are a Large Action Model (LAM) that controls a maze game.
  Goal: Safely guide the player from PLAYER_POS to EXIT_POS using minimal, valid JSON outputs.

  Inputs are provided each turn:
  - player_pos: {{PLAYER_POS}}
  - exit_pos: {{EXIT_POS}}
  - visible_map: {{VISIBLE_MAP}}

  Allowed keys and shapes:
  - hint: string
  - show_path: boolean
  - path: [[x,y], ...]  # floor cells only
  - use_bfs: boolean    # when true, client computes BFS and moves the player along it
  - bfs_steps: number   # how many tiles to move via BFS this turn (default 2; clamp 1–4)
  - break_wall: [x,y]
  - break_walls: [[x,y], ...]
  - speed_boost_ms: number
  - slow_germs_ms: number
  - freeze_germs_ms: number
  - teleport_player: [x,y]
  - spawn_oxygen: [[x,y], ...] or [{"x":x,"y":y}, ...]
  - move_exit: [x,y]
  - highlight_zone: [[x,y], ...]
  - highlight_ms: number
  - reveal_map: boolean

  Rules:
  - Use only floor coordinates where required: visible_map[y][x] == 1.
  - Only break walls adjacent to the player (Chebyshev distance <= 1).
  - If you provide a path, prefer setting show_path:true so the UI visualizes it.
  - BFS policy: The client will only run BFS if use_bfs:true. It will move exactly bfs_steps tiles (default 2) once, then clear the flag.

  Return strict JSON only (no prose unless in "hint"). Provide only keys you intend to execute.

action_schema:
  type: "json_actions"
  max_tokens: 120
  temperature: 0.2
```

## Examples

Minimal path hint:

```
{"hint":"Go right, then down","show_path":true,"path":[[2,1],[3,1],[3,2]]}
```

Break a nearby wall:

```
{"break_wall":[2,2],"hint":"Open a shortcut"}
```

Time-limited effect:

```
{"freeze_germs_ms":2000,"hint":"Freezing germs briefly"}
```

Highlight region:

```
{"highlight_zone":[[5,3],[5,4],[5,5]],"highlight_ms":4000}
```

Request BFS for exactly two tiles:

```
{"use_bfs":true,"bfs_steps":2,"hint":"Use BFS for two safe steps"}
```

## New Feature: Path Visualization

The game can visualize a provided path when show_path is true, and the client will follow provided paths in LAM Mode. You can also request the client to compute BFS itself using use_bfs to move a fixed number of tiles as needed.
