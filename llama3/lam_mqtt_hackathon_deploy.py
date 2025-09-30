# lam_mqtt_hackathon_deploy.py

import uuid
import json
import logging
import threading
import queue
import sys
import os
from abc import ABC, abstractmethod
import fire
import paho.mqtt.client as mqtt
from concurrent.futures import ThreadPoolExecutor
from llama import Dialog, Llama
from collections import deque
# Model interface and implementations
class ModelInterface(ABC):
    @abstractmethod
    def generate_response(self, dialog, max_gen_len, temperature, top_p):
        """Generate a response given a dialog history"""
        pass
    
    @abstractmethod
    def count_tokens(self, dialog):
        """Count tokens in the dialog"""
        pass
# Reuse your model classes
class LlamaModel(ModelInterface):
    def __init__(self, ckpt_dir, tokenizer_path, max_seq_len, max_batch_size):
        try:
            logging.info(f"[LlamaModel] Initializing with ckpt_dir={ckpt_dir}, tokenizer_path={tokenizer_path}")
            self.generator = Llama.build(
                ckpt_dir=ckpt_dir,
                tokenizer_path=tokenizer_path,
                max_seq_len=max_seq_len,
                max_batch_size=max_batch_size,
            )
            logging.info(f"[LlamaModel] Successfully initialized Llama model")
        except Exception as e:
            logging.error(f"[LlamaModel] Failed to initialize: {e}")
            raise RuntimeError(f"Failed to initialize Llama model: {e}")
    
    def generate_response(self, dialog, max_gen_len, temperature, top_p):
        try:
            logging.info(f"[LlamaModel] Generating response (pre-simplification)...")

            # 1. Validate & sanitize
            try:
                dialog = self.validate_and_sanitize_dialog(dialog)
            except Exception as validation_error:
                raise ValueError(f"Invalid dialog format: {validation_error}")

            # 2. Always simplify (compression of large maps)
            simplified_dialog = self._simplify_dialog(dialog)
            if simplified_dialog is not dialog:
                logging.info("[LlamaModel] Dialog simplified (map compressed)")

            # 3. Single generation attempt
            try:
                results = self.generator.chat_completion(
                    [simplified_dialog],
                    max_gen_len=max_gen_len,
                    temperature=temperature,
                    top_p=top_p,
                )
            except Exception as gen_err:
                # Persist simplified dialog for debugging then raise
                try:
                    debug_folder = "debug_dialogs"
                    os.makedirs(debug_folder, exist_ok=True)
                    debug_filename = os.path.join(debug_folder, f"debug_dialog_{uuid.uuid4()}.json")
                    with open(debug_filename, "w") as f:
                        json.dump(simplified_dialog, f, indent=2)
                    logging.error(f"[LlamaModel] Generation failed (saved {debug_filename}): {gen_err}")
                except Exception:
                    logging.error(f"[LlamaModel] Generation failed (also failed saving debug): {gen_err}")
                raise RuntimeError(f"chat_completion failed: {gen_err}")
            
            # Validate response structure
            if not results:
                raise RuntimeError("chat_completion returned empty results")
            
            if len(results) == 0:
                raise RuntimeError("chat_completion returned empty results list")
                
            result = results[0]
            if 'generation' not in result:
                raise RuntimeError(f"chat_completion result missing 'generation' key. Keys: {list(result.keys())}")
                
            generation = result['generation']
            if 'content' not in generation:
                raise RuntimeError(f"generation missing 'content' key. Keys: {list(generation.keys())}")
                
            content = generation['content']
            if not isinstance(content, str):
                raise RuntimeError(f"generation content is not a string: {type(content)}")
                
            return content
            
        except Exception as e:
            # Log the full exception for debugging
            logging.error(f"[LlamaModel] Exception in generate_response: {e}")
            logging.error(f"[LlamaModel] Dialog input: {dialog}")
            # propagate a meaningful exception up so caller can send to client
            raise RuntimeError(f"chat_completion failed: {e}")
    
    def count_tokens(self, dialog):
        """Count tokens in the dialog"""
        try:
            total_tokens = 0
            for message in dialog:
                if 'role' not in message or 'content' not in message:
                    logging.warning(f"[LlamaModel] Malformed message: {message}")
                    continue
                    
                role_token = self.generator.tokenizer.encode(message['role'], bos=False, eos=False)
                content_tokens = self.generator.tokenizer.encode(message['content'], bos=False, eos=False)
                total_tokens += len(role_token) + len(content_tokens)
            return total_tokens
        except Exception as e:
            logging.error(f"[LlamaModel] Error counting tokens: {e}")
            # Return a reasonable estimate to avoid breaking the session
            return sum(len(str(msg.get('content', ''))) for msg in dialog) // 4
    
    def validate_and_sanitize_dialog(self, dialog):
        """Validate and sanitize dialog to ensure it's compatible with Llama3"""
        if not isinstance(dialog, list):
            raise ValueError(f"Dialog must be a list, got {type(dialog)}")
        
        sanitized_dialog = []
        for i, message in enumerate(dialog):
            if not isinstance(message, dict):
                logging.warning(f"[LlamaModel] Skipping non-dict message at index {i}: {message}")
                continue
                
            if 'role' not in message or 'content' not in message:
                logging.warning(f"[LlamaModel] Skipping malformed message at index {i}: {message}")
                continue
            
            # Ensure role is valid
            valid_roles = ["system", "user", "assistant"]
            if message['role'] not in valid_roles:
                logging.warning(f"[LlamaModel] Invalid role '{message['role']}' at index {i}, skipping")
                continue
            
            # Ensure content is string and not empty
            content = str(message['content']).strip()
            if not content:
                logging.warning(f"[LlamaModel] Empty content at index {i}, skipping")
                continue
            
            sanitized_dialog.append({
                "role": message['role'],
                "content": content
            })
        
        if len(sanitized_dialog) == 0:
            raise ValueError("No valid messages found in dialog after sanitization")
        
        # Ensure first message is system message
        if sanitized_dialog[0]['role'] != 'system':
            logging.warning("[LlamaModel] No system message found, adding default")
            sanitized_dialog.insert(0, {
                "role": "system",
                "content": "You are a helpful assistant."
            })
        
        return sanitized_dialog

    def _simplify_dialog(self, dialog):
        """Produce a lighter-weight dialog by compressing large JSON maps in the last user message.

        Replaces 'visible_map' with a compressed structure 'visible_map_compressed'.
        """
        try:
            changed = False
            simplified = []
            for msg in dialog:
                if msg.get("role") != "user":
                    simplified.append(msg)
                    continue
                content = msg.get("content", "")
                data = None
                if isinstance(content, str) and len(content) < 300000:
                    try:
                        data = json.loads(content)
                    except Exception:
                        pass
                if isinstance(data, dict) and isinstance(data.get("visible_map"), list):
                    vm = data["visible_map"]
                    h = len(vm)
                    w = len(vm[0]) if h else 0
                    row_strings = ["".join(str(c) for c in row) for row in vm]

                    def rle(s):
                        out = []
                        last = None
                        count = 0
                        for ch in s:
                            if ch == last:
                                count += 1
                            else:
                                if last is not None:
                                    out.append(f"{last}{count}")
                                last = ch
                                count = 1
                        if last is not None:
                            out.append(f"{last}{count}")
                        r = "|".join(out)
                        return r if len(r) < len(s) else s

                    compressed_rows = [rle(rs) for rs in row_strings]
                    data["visible_map_compressed"] = {
                        "width": w,
                        "height": h,
                        "rows": compressed_rows,
                        "encoding": "char-run"
                    }
                    data.pop("visible_map", None)
                    simplified.append({
                        "role": "user",
                        "content": json.dumps(data, ensure_ascii=False)
                    })
                    changed = True
                else:
                    simplified.append(msg)
            return simplified if changed else dialog
        except Exception as e:
            logging.warning(f"[LlamaModel] _simplify_dialog error: {e}")
            return dialog

class QwQModel(ModelInterface):
    def __init__(self, model_name, max_seq_len, quantization=None):
        """Placeholder for QwQ model - implement based on your needs"""
        raise NotImplementedError("QwQModel is not implemented yet. Use LlamaModel instead.")
    
    def generate_response(self, dialog, max_gen_len, temperature, top_p):
        raise NotImplementedError("QwQModel is not implemented yet.")
    
    def count_tokens(self, dialog):
        raise NotImplementedError("QwQModel is not implemented yet.")

# ─── Configuration ──────────────────────────────────────────────────────────────

# MQTT broker settings
MQTT_BROKER = "47.89.252.2"
MQTT_PORT   = 1883
STATE_TOPIC = "maze/state"
HINT_PREFIX = "maze/hint"
# New: topic to submit prompt templates (global or per-session)
TEMPLATE_TOPIC = "maze/template"

# ─── Session & Prompt Management ────────────────────────────────────────────────

class MazeSessionManager:
    def __init__(self, model, system_prompt, max_seq_len, max_breaks):
        self.model         = model
        self.system_prompt = system_prompt
        self.max_seq_len   = max_seq_len
        self.max_breaks    = max_breaks

        # Track per-session dialog history and breaks remaining
        self.dialogs       = {}  # session_id -> [messages...]
        self.breaks_left   = {}  # session_id -> int
        self.locks         = {}  # session_id -> threading.Lock
        self.global_lock   = threading.Lock()

    def get_or_create(self, session_id):
        with self.global_lock:
            if session_id not in self.dialogs:
                # Initialize dialog with system prompt
                self.dialogs[session_id] = [
                    {"role": "system", "content": self.system_prompt}
                ]
                self.breaks_left[session_id] = self.max_breaks
                self.locks[session_id] = threading.Lock()
                logging.info(f"[Session] Created new session '{session_id}' with {self.max_breaks} breaks")
        return self.dialogs[session_id], self.breaks_left[session_id], self.locks[session_id]

    def process_state(self, state):
        """
        Given a state dict from the game, produce guidance JSON.
        """
        session_id = state.get("sessionId", "default")
        dialog, breaks_remain, lock = self.get_or_create(session_id)

        # Build the user message describing the current state
        try:
            # Validate state data before creating user message
            required_state_fields = ["player_pos", "exit_pos", "visible_map"]
            for field in required_state_fields:
                if field not in state:
                    raise ValueError(f"Missing required state field: {field}")
            
            user_msg = {
                "role": "user",
                "content": json.dumps({
                    "player_pos":      state["player_pos"],
                    "exit_pos":        state["exit_pos"],
                    "visible_map":     state["visible_map"],
                    "breaks_remaining": breaks_remain
                }, ensure_ascii=False)  # Ensure proper JSON encoding
            }
            
            logging.debug(f"[Session {session_id}] Created user message with content length: {len(user_msg['content'])}")
            
        except Exception as e:
            logging.error(f"[Session {session_id}] Error creating user message: {e}")
            # Create a fallback message
            user_msg = {
                "role": "user", 
                "content": json.dumps({"error": "Invalid state data", "breaks_remaining": breaks_remain})
            }

        with lock:
            # Append to dialog
            dialog.append(user_msg)

            # Trim if too long
            # (simple drop oldest user/assistant after the system prompt)
            while self.model.count_tokens(dialog) > self.max_seq_len - 500 and len(dialog) > 2:
                dialog.pop(1)  # drop oldest user
                if len(dialog) > 1 and dialog[1]["role"] == "assistant":
                    dialog.pop(1)

            # Validate dialog structure after trimming
            if len(dialog) == 0:
                logging.error(f"[Session {session_id}] Dialog became empty after trimming!")
                # Reinitialize with system prompt
                dialog.append({"role": "system", "content": self.system_prompt})
                dialog.append(user_msg)
            elif dialog[0]["role"] != "system":
                logging.warning(f"[Session {session_id}] Dialog missing system message after trimming, reinserting")
                dialog.insert(0, {"role": "system", "content": self.system_prompt})
            
            logging.debug(f"[Session {session_id}] Final dialog length: {len(dialog)} messages")

            # Generate guidance
            try:
                logging.info(f"[Session {session_id}] Generating response with the dialogue content: {dialog}...")
                response_text = self.model.generate_response(
                    dialog,
                    max_gen_len=256,
                    temperature=0.6,
                    top_p=0.9
                )
            except Exception as e:
                logging.error(f"[Session {session_id}] Model generation error: {e}")
                # include small prompt excerpt for debugging
                sample = user_msg.get('content', '')
                if isinstance(sample, str) and len(sample) > 160:
                    sample = sample[:160] + '…'
                guidance = {"error": f"LLM error: {e}", "prompt": sample, "breaks_remaining": breaks_remain}
                return session_id, guidance

            # Append assistant response and parse into guidance JSON
            dialog.append({"role": "assistant", "content": response_text})

            guidance = self._robust_parse_guidance(response_text, state, breaks_remain, session_id)

            # Enforce break limits
            if "break_wall" in guidance:
                if breaks_remain > 0:
                    self.breaks_left[session_id] -= 1
                else:
                    guidance.pop("break_wall", None)

            guidance["breaks_remaining"] = self.breaks_left[session_id]

        return session_id, guidance

    # ─── Guidance Parsing Helpers ────────────────────────────────────────────
    def _robust_parse_guidance(self, response_text: str, state: dict, breaks_remain: int, session_id: str):
        raw = response_text.strip()
        # Strip fences
        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()
        if raw.startswith("```") and not raw.startswith("```json"):
            raw = raw[3:].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        # Attempt direct parse then extracted object
        for attempt in (raw,):
            try:
                obj = json.loads(attempt)
                if isinstance(obj, dict):
                    return self._finalize_guidance(obj, state, breaks_remain, session_id, source="direct")
            except Exception:
                pass

        extracted = self._extract_first_json_object(raw)
        if extracted:
            try:
                obj = json.loads(extracted)
                if isinstance(obj, dict):
                    return self._finalize_guidance(obj, state, breaks_remain, session_id, source="extracted")
            except Exception as e:
                logging.debug(f"[Session {session_id}] Extracted JSON parse fail: {e}")

        logging.warning(f"[Session {session_id}] Falling back to computed path (parse failed)")
        fallback = {"hint": raw[:160] + ("…" if len(raw) > 160 else "")}
        return self._finalize_guidance(fallback, state, breaks_remain, session_id, source="fallback")

    def _extract_first_json_object(self, text: str):
        """Extract the first top-level JSON object substring by balancing braces."""
        start = text.find('{')
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        return None

    def _finalize_guidance(self, guidance: dict, state: dict, breaks_remain: int, session_id: str, source: str):
        """Ensure mandatory fields (path) exist; compute if absent or invalid."""
        path = guidance.get("path")
        if not self._is_valid_path(path):
            try:
                computed_path, break_wall = self._compute_path_with_breaks(state, breaks_remain)
                guidance["path"] = computed_path
                # Only propose break if model didn't already and it's useful
                if break_wall and "break_wall" not in guidance and breaks_remain > 0:
                    guidance["break_wall"] = break_wall
                logging.info(f"[Session {session_id}] Path {'computed' if path is None else 'replaced'} via {source} (len={len(guidance['path'])})")
            except Exception as e:
                logging.error(f"[Session {session_id}] Failed to compute fallback path: {e}")
                guidance.setdefault("error", f"No valid path and fallback failed: {e}")
                guidance.setdefault("path", [])
        return guidance

    def _is_valid_path(self, path):
        if not isinstance(path, list) or not path:
            return False
        for p in path:
            if not (isinstance(p, list) or isinstance(p, tuple)):
                return False
            if len(p) != 2:
                return False
            if not all(isinstance(v, int) for v in p):
                return False
        return True

    def _compute_path_with_breaks(self, state: dict, breaks_remain: int):
        """BFS shortest path allowing up to breaks_remain wall breaks.

        Returns (path, suggested_break_wall). If a path exists without using a break,
        suggested_break_wall will be None. If no path exists but one break could help,
        we heuristically suggest a wall adjacent to the shortest frontier.
        """
        grid = state.get("visible_map") or []
        start = state.get("player_pos")
        goal = state.get("exit_pos")
        if not (isinstance(grid, list) and start and goal):
            raise ValueError("Invalid state for path computation")

        h = len(grid)
        w = len(grid[0]) if h else 0
        if h == 0 or w == 0:
            raise ValueError("Empty grid")

        sx, sy = start
        gx, gy = goal

        def in_bounds(x, y):
            return 0 <= y < h and 0 <= x < w

        # State: (x, y, breaks_used)
        q = deque([(sx, sy, 0)])
        parent = {(sx, sy, 0): None}
        visited = set([(sx, sy, 0)])
        dirs = [(1,0),(-1,0),(0,1),(0,-1)]
        goal_state = None

        while q:
            x, y, b = q.popleft()
            if (x, y) == (gx, gy):
                goal_state = (x, y, b)
                break
            for dx, dy in dirs:
                nx, ny = x+dx, y+dy
                if not in_bounds(nx, ny):
                    continue
                cell = grid[ny][nx]
                if cell == 1:  # floor
                    state_key = (nx, ny, b)
                    if state_key not in visited:
                        visited.add(state_key)
                        parent[state_key] = (x, y, b)
                        q.append(state_key)
                elif cell == 0 and b < breaks_remain:  # wall, we can break
                    state_key = (nx, ny, b+1)
                    if state_key not in visited:
                        visited.add(state_key)
                        parent[state_key] = (x, y, b)
                        q.append(state_key)

        if goal_state is None:
            # No path even with breaks: suggest a wall adjacent to start towards goal as heuristic
            suggestion = None
            if breaks_remain > 0:
                best_dist = float('inf')
                for dx, dy in dirs:
                    nx, ny = sx+dx, sy+dy
                    if in_bounds(nx, ny) and grid[ny][nx] == 0:
                        dist = abs(nx - gx) + abs(ny - gy)
                        if dist < best_dist:
                            best_dist = dist
                            suggestion = [nx, ny]
            return [], suggestion

        # Reconstruct path
        rev = []
        cur = goal_state
        while cur is not None:
            x, y, b = cur
            rev.append([x, y])
            cur = parent[cur]
        rev.reverse()

        # Determine if we used a break and which wall to suggest next (none if already used optimal)
        used_breaks = goal_state[2]
        suggestion = None
        if used_breaks == 0 and breaks_remain > 0:
            # We didn't need a break; maybe suggest none.
            suggestion = None
        return rev, suggestion

    def set_global_prompt(self, new_prompt: str, reset_existing: bool = False):
        """Update the global system prompt. Optionally reset all sessions to use it."""
        with self.global_lock:
            self.system_prompt = new_prompt
            if reset_existing:
                for sid in list(self.dialogs.keys()):
                    self.dialogs[sid] = [{"role": "system", "content": new_prompt}]
                    self.breaks_left[sid] = self.max_breaks
        logging.info("[Template] Global system prompt updated. reset_existing=%s", reset_existing)

    def set_session_prompt(self, session_id: str, new_prompt: str, reset: bool = True):
        """Update the system prompt for a specific session. Optionally reset its history."""
        with self.global_lock:
            if reset or session_id not in self.dialogs:
                self.dialogs[session_id] = [{"role": "system", "content": new_prompt}]
                self.breaks_left[session_id] = self.max_breaks
                if session_id not in self.locks:
                    self.locks[session_id] = threading.Lock()
            else:
                # Replace only the system message, retain history
                if self.dialogs[session_id]:
                    self.dialogs[session_id][0] = {"role": "system", "content": new_prompt}
                else:
                    self.dialogs[session_id] = [{"role": "system", "content": new_prompt}]
        logging.info("[Template] Session '%s' system prompt updated. reset=%s", session_id, reset)

# ─── Worker & MQTT Setup ────────────────────────────────────────────────────────

message_queue = queue.Queue()

def maze_message_processor(session_manager, mqtt_client):
    """Worker thread to process maze state messages and generate guidance"""
    while True:
        try:
            state = message_queue.get()
            logging.info(f"[Processor] Processing state for session: {state.get('sessionId', 'default')}")
            
            session_id, guidance = session_manager.process_state(state)
            topic = f"{HINT_PREFIX}/{session_id}"
            payload = json.dumps(guidance)
            
            # Publish the guidance
            result = mqtt_client.publish(topic, payload)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error(f"[Processor] Failed to publish to {topic}: {result.rc}")
            else:
                logging.info(f"[Publish] {topic} → {payload[:200]}...")
                
        except Exception as e:
            logging.error(f"[Processor] Error handling state: {e}")
            try:
                session_id = state.get('sessionId', 'default') if 'state' in locals() else 'unknown'
                error_payload = json.dumps({"error": str(e), "breaks_remaining": 0})
                mqtt_client.publish(f"{HINT_PREFIX}/{session_id}", error_payload)
                logging.info(f"[Processor] Published error to session {session_id}")
            except Exception as pub_error:
                logging.error(f"[Processor] Failed to publish error message: {pub_error}")
        finally:
            message_queue.task_done()


def main(
    model_type: str = "llama",
    ckpt_dir: str = None,
    tokenizer_path: str = None,
    model_name: str = "Qwen/QwQ-32B",
    quantization: str = None,
    max_seq_len: int = 2048,
    max_batch_size: int = 4,
    max_breaks: int = 3,
    num_workers: int = 2,
    mqtt_username: str = None,
    mqtt_password: str = None
):
    """Deploy a hackathon‐style LAM that guides maze players via hints, paths, and wall‐breaks."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # 1) Initialize model
    if model_type.lower() == "llama":
        if not ckpt_dir or not tokenizer_path:
            raise ValueError("For llama model, --ckpt_dir and --tokenizer_path are required")
        
        # Validate paths exist
        if not os.path.exists(ckpt_dir):
            raise ValueError(f"Checkpoint directory does not exist: {ckpt_dir}")
        if not os.path.exists(tokenizer_path):
            raise ValueError(f"Tokenizer path does not exist: {tokenizer_path}")
            
        logging.info(f"Initializing Llama model with ckpt_dir={ckpt_dir}, tokenizer_path={tokenizer_path}")
        model = LlamaModel(ckpt_dir, tokenizer_path, max_seq_len, max_batch_size)
    elif model_type.lower() == "qwq":
        model = QwQModel(model_name, max_seq_len, quantization)
    else:
        raise ValueError(f"Unsupported model_type: {model_type}")

    logging.info("Model initialization completed successfully")
    
    # Test the model with a simple dialog to ensure it's working
    try:
        test_dialog = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello' in JSON format with a 'message' field."}
        ]
        logging.info("Testing model with a simple dialog...")
        test_response = model.generate_response(test_dialog, max_gen_len=50, temperature=0.1, top_p=0.9)
        logging.info(f"Model test successful. Response: {test_response[:100]}...")
    except Exception as e:
        logging.error(f"Model test failed: {e}")
        raise RuntimeError(f"Model test failed, cannot proceed: {e}")

    # 2) System prompt for maze guidance
    # SYSTEM_PROMPT = f"""
    # You are a Large Action Model (LAM) guiding players through a top-down maze game.
    # You receive the player's current position, the exit position, the visible map (0=wall,1=floor),
    # and how many wall‐breaks remain. **Always** compute and include:
    # - "path": a full list of [x,y] coords from the player to the exit
    # You may also include:
    # - "hint": a short text hint
    # - "break_wall": a single [x,y] coordinate where a wall should be broken (use sparingly)
    # Return **only** valid JSON.
    # """
    SYSTEM_PROMPT = ""

    # 3) Create session manager
    session_manager = MazeSessionManager(model, SYSTEM_PROMPT, max_seq_len, max_breaks)

    # 4) Start worker threads
    client_id = f"maze-hack-lam-{uuid.uuid4().hex[:8]}"
    mqtt_client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    if mqtt_username and mqtt_password:
        mqtt_client.username_pw_set(mqtt_username, mqtt_password)

    # Connect handlers
    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            logging.info(f"Connected to MQTT broker, subscribing to topics...")
            client.subscribe(STATE_TOPIC)
            client.subscribe(TEMPLATE_TOPIC)
            client.subscribe(f"{TEMPLATE_TOPIC}/+")  # Subscribe to session-specific templates
            logging.info(f"Subscribed to: {STATE_TOPIC}, {TEMPLATE_TOPIC}, {TEMPLATE_TOPIC}/+")
        else:
            logging.error(f"MQTT connect failed with code {reason_code}")

    def on_disconnect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            logging.warning(f"Unexpected MQTT disconnection: {reason_code}")

    def on_message(client, userdata, msg):
        try:
            logging.info(f"[DEBUG] Received MQTT message on topic '{msg.topic}': {msg.payload}")
            
            # Handle state updates
            if msg.topic == STATE_TOPIC:
                try:
                    state = json.loads(msg.payload.decode("utf-8"))
                    message_queue.put(state)
                    return
                except json.JSONDecodeError as e:
                    logging.error(f"[MQTT] Invalid JSON in state message: {e}")
                    return

            # Handle template submissions
            if msg.topic == TEMPLATE_TOPIC or msg.topic.startswith(f"{TEMPLATE_TOPIC}/"):
                try:
                    payload = json.loads(msg.payload.decode("utf-8")) if msg.payload else {}
                    new_prompt = payload.get("prompt_template") or payload.get("system_prompt") or payload.get("template")
                    if not new_prompt:
                        logging.warning("[Template] Missing 'template' in payload")
                        return
                    logging.info(f"[Template] Received new prompt: {new_prompt[:100]}...")
                    # optional overrides
                    mb = payload.get("max_breaks")
                    if isinstance(mb, int) and mb > 0:
                        session_manager.max_breaks = mb
                        logging.info("[Template] max_breaks updated globally to %d", mb)
                    reset = bool(payload.get("reset", True))
                    # session id can be in payload or encoded in topic suffix
                    sid = payload.get("session_id") or payload.get("sessionId")
                    if not sid and msg.topic.startswith(f"{TEMPLATE_TOPIC}/"):
                        sid = msg.topic.split("/", 2)[-1]
                    if sid:
                        session_manager.set_session_prompt(sid, new_prompt, reset=reset)
                        # Optionally acknowledge via hint channel
                        try:
                            client.publish(f"{HINT_PREFIX}/{sid}", json.dumps({"hint": "Template updated", "breaks_remaining": session_manager.breaks_left.get(sid, session_manager.max_breaks)}))
                        except Exception:
                            pass
                    else:
                        session_manager.set_global_prompt(new_prompt, reset_existing=reset)
                    return
                except json.JSONDecodeError as e:
                    logging.error(f"[MQTT] Invalid JSON in template message: {e}")
                    return

            logging.debug("[MQTT] Ignored topic %s", msg.topic)
        except Exception as e:
            logging.error(f"[MQTT] Unexpected error in on_message for topic {msg.topic}: {e}")
            logging.error(f"[MQTT] Message payload: {msg.payload}")

    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    # Launch workers
    pool = ThreadPoolExecutor(max_workers=num_workers)
    for _ in range(num_workers):
        pool.submit(maze_message_processor, session_manager, mqtt_client)

    # 5) Connect & loop
    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
    
    try:
        logging.info(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        logging.info("Starting MQTT loop...")
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully...")
    except Exception as e:
        logging.error(f"MQTT connection error: {e}")
        raise
    finally:
        logging.info("Cleaning up...")
        mqtt_client.disconnect()
        pool.shutdown(wait=True, timeout=10)


if __name__ == "__main__":
    fire.Fire(main)
    # Example usage:
    # torchrun --nproc_per_node 1 ./lam_mqtt_hackathon_deploy.py --model_type llama --ckpt_dir Llama3.1-8B-Instruct --tokenizer_path Llama3.1-8B-Instruct/tokenizer.model --max_batch_size 2 --mqtt_username TangClinic --mqtt_password Tang123
    # -
