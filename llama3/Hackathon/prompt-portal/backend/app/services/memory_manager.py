"""
Advanced Memory Management System for LAM (Large Action Model) Maze Game

This module implements a hierarchical memory system designed to:
1. Minimize token usage while maximizing agent accuracy
2. Separate static knowledge from dynamic state
3. Compress historical data intelligently
4. Prioritize critical information

Memory Architecture:
┌────────────────────────────────────────────────┐
│  STATIC LAYER (cached, sent only once)         │
│  - System prompt / Persona                     │
│  - Available skills & action definitions       │
│  - Response format requirements                │
└────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│  EPISODIC LAYER (compressed summaries)         │
│  - Movement patterns (not individual moves)    │
│  - Key discoveries                             │
│  - Error history (collision patterns)          │
└────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│  WORKING LAYER (always current)                │
│  - Current position & surroundings             │
│  - Energy status                               │
│  - Immediate obstacles                         │
│  - Last action result                          │
└────────────────────────────────────────────────┘
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class MazeMemoryState:
    """Represents the agent's memory state for a maze session."""
    
    # Core identifiers
    session_id: str
    maze_size: int = 17
    
    # Position tracking
    current_position: Tuple[int, int] = (1, 1)
    exit_position: Tuple[int, int] = (15, 15)
    
    # Resource tracking
    energy: int = 150
    oxygen_collected: int = 0
    score: int = 0
    
    # Movement history - limited to recent critical moves
    recent_moves: deque = field(default_factory=lambda: deque(maxlen=5))
    
    # Pattern detection storage
    visited_positions: set = field(default_factory=set)
    collision_positions: set = field(default_factory=set)
    discovered_oxygen: set = field(default_factory=set)
    
    # Compressed history summaries
    movement_pattern: str = ""  # e.g., "Explored east wing, now heading south"
    exploration_coverage: float = 0.0
    
    # Last action result
    last_action: Optional[Dict] = None
    last_result: Optional[str] = None
    
    # Revealed map state - stored as compact string
    revealed_cells: set = field(default_factory=set)
    
    # Skill usage tracking
    skills_used: Dict[str, int] = field(default_factory=dict)
    
    # Message counter for context strategy
    message_count: int = 0
    
    # Hash of last sent minimap (for delta detection)
    last_minimap_hash: str = ""


class MazeMemoryManager:
    """
    Manages memory for maze game agents with token-efficient strategies.
    
    Features:
    1. Hierarchical memory (static/episodic/working)
    2. Progressive compression of history
    3. Delta updates for unchanged state
    4. Smart priority-based context construction
    """
    
    def __init__(self, max_context_tokens: int = 2000):
        """
        Initialize memory manager.
        
        Args:
            max_context_tokens: Approximate target for user message tokens
        """
        self.max_context_tokens = max_context_tokens
        self.sessions: Dict[str, MazeMemoryState] = {}
        
        # Token estimates (approximate)
        self.TOKENS_PER_CHAR = 0.25
        
        logger.info("MazeMemoryManager initialized")
    
    def get_or_create_session(self, session_id: str, maze_size: int = 17) -> MazeMemoryState:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = MazeMemoryState(
                session_id=session_id,
                maze_size=maze_size
            )
            logger.info(f"Created memory state for session: {session_id}")
        return self.sessions[session_id]
    
    def update_state(
        self,
        session_id: str,
        position: Tuple[int, int],
        energy: int,
        oxygen: int,
        score: int,
        action: Optional[Dict] = None,
        result: Optional[str] = None,
        revealed_cells: Optional[set] = None,
        exit_position: Optional[Tuple[int, int]] = None
    ) -> None:
        """Update the session's memory state."""
        state = self.get_or_create_session(session_id)
        
        # Track movement
        if position != state.current_position:
            state.recent_moves.append({
                "from": state.current_position,
                "to": position,
                "action": action
            })
            state.visited_positions.add(position)
        
        # Track collisions from failed moves
        if result and "COLLISION" in result.upper():
            # Estimate collision position from direction
            if action and action.get("direction"):
                dx, dy = 0, 0
                d = action["direction"].lower()
                if d == "north": dy = -1
                elif d == "south": dy = 1
                elif d == "east": dx = 1
                elif d == "west": dx = -1
                collision_pos = (state.current_position[0] + dx, state.current_position[1] + dy)
                state.collision_positions.add(collision_pos)
        
        # Update core state
        state.current_position = position
        state.energy = energy
        state.oxygen_collected = oxygen
        state.score = score
        state.last_action = action
        state.last_result = result
        
        if exit_position:
            state.exit_position = exit_position
        
        if revealed_cells:
            state.revealed_cells.update(revealed_cells)
        
        # Update exploration coverage
        if state.maze_size > 0:
            total_cells = state.maze_size * state.maze_size
            state.exploration_coverage = len(state.visited_positions) / total_cells
        
        # Update movement pattern summary (compress history)
        state.movement_pattern = self._summarize_movement_pattern(state)
        
        state.message_count += 1
    
    def _summarize_movement_pattern(self, state: MazeMemoryState) -> str:
        """
        Create a compressed summary of recent movement patterns.
        Instead of listing every move, describe the overall pattern.
        """
        if len(state.recent_moves) < 2:
            return ""
        
        moves = list(state.recent_moves)
        
        # Detect dominant direction
        directions = {"north": 0, "south": 0, "east": 0, "west": 0}
        for move in moves:
            if move.get("action") and move["action"].get("direction"):
                d = move["action"]["direction"].lower()
                if d in directions:
                    directions[d] += 1
        
        # Find dominant direction
        max_dir = max(directions, key=directions.get)
        if directions[max_dir] >= len(moves) * 0.6:  # 60% same direction
            return f"Trending {max_dir}"
        
        # Detect oscillation (back and forth)
        if len(moves) >= 3:
            positions = [m["to"] for m in moves]
            unique = len(set(positions))
            if unique < len(positions) * 0.5:  # Less than half unique
                return "WARNING: Oscillating/stuck pattern"
        
        return ""
    
    def build_static_layer(self, system_prompt: str, available_skills: List[Dict]) -> str:
        """
        Build the static layer (sent only once or rarely).
        Contains persona, skills, and format requirements.
        """
        # Compress skills to essential info only
        skills_compact = []
        for skill in available_skills:
            skills_compact.append(f"- {skill.get('name', 'Unknown')}: {skill.get('description', '')[:60]}...")
        
        static = f"""{system_prompt}

[AVAILABLE SKILLS]
{chr(10).join(skills_compact)}

[RESPONSE FORMAT]
Output JSON: {{"action": "move"|"use_skill"|"wait", "direction": "north|south|east|west", "skill": "skill_id"}}"""
        
        return static
    
    def build_working_layer(
        self,
        session_id: str,
        minimap: str,
        surroundings: Dict[str, str],
        available_skills: List[Dict]
    ) -> str:
        """
        Build the working layer with current state.
        This is always sent and contains the most critical info.
        """
        state = self.get_or_create_session(session_id)
        
        # Calculate minimap hash for delta detection
        minimap_hash = hashlib.md5(minimap.encode()).hexdigest()[:8]
        map_changed = minimap_hash != state.last_minimap_hash
        state.last_minimap_hash = minimap_hash
        
        # Build compact surroundings
        surr_str = " | ".join([f"{k}:{v}" for k, v in surroundings.items()])
        
        # Energy status with urgency indicator
        energy_status = state.energy
        energy_urgency = ""
        if state.energy < 30:
            energy_urgency = " [CRITICAL]"
        elif state.energy < 60:
            energy_urgency = " [LOW]"
        
        # Build skill status (compact)
        skills_ready = []
        for skill in available_skills:
            if skill.get("ready", True):
                skills_ready.append(skill.get("id", "unknown"))
        
        working = f"""[STATE]
Pos: ({state.current_position[0]},{state.current_position[1]}) | Exit: ({state.exit_position[0]},{state.exit_position[1]})
Energy: {energy_status}/150{energy_urgency} | O2: {state.oxygen_collected} | Score: {state.score}
Near: {surr_str}
Skills: {', '.join(skills_ready) if skills_ready else 'None ready'}"""

        # Add minimap only if it changed or first message
        if map_changed or state.message_count <= 1:
            working += f"\n\n[MAP]\n{minimap}"
        else:
            working += "\n[MAP unchanged]"
        
        return working
    
    def build_episodic_layer(self, session_id: str) -> str:
        """
        Build the episodic layer with compressed history.
        This provides context without bloating the prompt.
        """
        state = self.get_or_create_session(session_id)
        
        parts = []
        
        # Movement pattern (if detected)
        if state.movement_pattern:
            parts.append(f"Pattern: {state.movement_pattern}")
        
        # Recent path (last 3-5 positions only)
        if state.recent_moves:
            recent_path = [f"({m['to'][0]},{m['to'][1]})" for m in list(state.recent_moves)[-3:]]
            parts.append(f"Recent: {' → '.join(recent_path)}")
        
        # Known collision points (compact list)
        if state.collision_positions:
            collisions = list(state.collision_positions)[-5:]  # Last 5 collisions
            coll_str = ", ".join([f"({c[0]},{c[1]})" for c in collisions])
            parts.append(f"Walls: {coll_str}")
        
        # Last result
        if state.last_result:
            # Truncate long results
            result = state.last_result[:100]
            if len(state.last_result) > 100:
                result += "..."
            parts.append(f"Last: {result}")
        
        # Exploration progress
        if state.exploration_coverage > 0:
            pct = int(state.exploration_coverage * 100)
            parts.append(f"Explored: {pct}%")
        
        if not parts:
            return ""
        
        return "[CONTEXT]\n" + " | ".join(parts)
    
    def build_optimized_prompt(
        self,
        session_id: str,
        system_prompt: str,
        minimap: str,
        surroundings: Dict[str, str],
        available_skills: List[Dict],
        is_first_message: bool = False
    ) -> Tuple[Optional[str], str]:
        """
        Build an optimized prompt with layered memory.
        
        Returns:
            Tuple of (system_prompt or None, user_message)
            System prompt is returned only on first message.
        """
        state = self.get_or_create_session(session_id)
        
        # Build layers
        working = self.build_working_layer(session_id, minimap, surroundings, available_skills)
        episodic = self.build_episodic_layer(session_id)
        
        # Combine user message
        user_parts = [working]
        if episodic:
            user_parts.append(episodic)
        
        user_message = "\n\n".join(user_parts)
        
        # Only send system prompt on first message
        if is_first_message or state.message_count <= 1:
            static = self.build_static_layer(system_prompt, available_skills)
            return (static, user_message)
        
        return (None, user_message)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) * self.TOKENS_PER_CHAR)
    
    def get_memory_stats(self, session_id: str) -> Dict[str, Any]:
        """Get memory usage statistics for a session."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        state = self.sessions[session_id]
        return {
            "session_id": session_id,
            "message_count": state.message_count,
            "positions_visited": len(state.visited_positions),
            "collisions_tracked": len(state.collision_positions),
            "cells_revealed": len(state.revealed_cells),
            "exploration_coverage": f"{state.exploration_coverage * 100:.1f}%",
            "movement_pattern": state.movement_pattern,
            "recent_moves": len(state.recent_moves)
        }
    
    def clear_session(self, session_id: str) -> None:
        """Clear a session's memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared memory for session: {session_id}")


# Global instance
_memory_manager: Optional[MazeMemoryManager] = None


def get_memory_manager() -> MazeMemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MazeMemoryManager()
    return _memory_manager
