# Maze Game Memory - Before & After Code Comparison

## Overview

This document shows the exact code changes made to enable LLM memory with a 3-message limit for the maze game.

---

## File 1: backend/app/services/llm_client.py

### SessionManager.__init__()

**BEFORE:**
```python
def __init__(self, llm_client: LLMClient, max_history_tokens: int = 10000):
    """
    Initialize session manager.
    
    Args:
        llm_client: LLM client instance
        max_history_tokens: Maximum tokens to keep in conversation history
    """
    self.llm_client = llm_client
    self.max_history_tokens = max_history_tokens
    self.sessions: Dict[str, Dict] = {}
    self.session_locks: Dict[str, threading.RLock] = {}
    self.global_lock = threading.RLock()
    
    logger.info("Session manager initialized")
```

**AFTER:**
```python
def __init__(self, llm_client: LLMClient, max_history_tokens: int = 10000, max_history_messages: Optional[int] = None):
    """
    Initialize session manager.
    
    Args:
        llm_client: LLM client instance
        max_history_tokens: Maximum tokens to keep in conversation history
        max_history_messages: Maximum number of messages to keep (excluding system prompt). If set, takes precedence over token-based trimming.
    """
    self.llm_client = llm_client
    self.max_history_tokens = max_history_tokens
    self.max_history_messages = max_history_messages
    self.sessions: Dict[str, Dict] = {}
    self.session_locks: Dict[str, threading.RLock] = {}
    self.global_lock = threading.RLock()
    
    if max_history_messages:
        logger.info(f"Session manager initialized with max_history_messages={max_history_messages}")
    else:
        logger.info("Session manager initialized")
```

**Changes:**
- ✅ Added `max_history_messages: Optional[int] = None` parameter
- ✅ Stored as instance variable
- ✅ Log includes the limit value if set

---

### SessionManager.process_message()

**BEFORE:**
```python
def process_message(
    self,
    session_id: str,
    system_prompt: str,
    user_message: str,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_tools: bool = True,
    use_history: bool = True
) -> str:
    """
    Process a user message and generate a response.
    
    Args:
        session_id: Session identifier
        system_prompt: System prompt
        user_message: User's message
        temperature: Sampling temperature
        top_p: Top-p sampling
        max_tokens: Maximum tokens
        use_tools: Whether to enable function calling tools
        use_history: Whether to maintain conversation history (disable for stateless calls like maze game)
        
    Returns:
        Generated response (may include function calls)
    """
    if use_history:
        # Get or create session with history
        session = self.get_or_create_session(session_id, system_prompt)
        session_lock = self.session_locks.get(session_id, threading.RLock())
        
        # Build the prompt first (with minimal locking)
        with session_lock:
            # Add user message to dialog
            session["dialog"].append({"role": "user", "content": user_message})
            session["message_count"] += 1
            
            # Simple trimming: keep only last N messages
            max_messages = 20
            if len(session["dialog"]) > max_messages:
                # Keep system message and last N-1 messages
                session["dialog"] = [session["dialog"][0]] + session["dialog"][-(max_messages-1):]
            
            # Prepare messages for API call
            messages = session["dialog"].copy()
    else:
        # Stateless mode: just system + user message (no history)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        session_lock = None
    
    # Now do inference WITHOUT holding session lock!
    try:
        # Use tools if requested (for maze game with function calling)
        tools = MAZE_GAME_TOOLS if use_tools else None
        
        response = self.llm_client.generate(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice="auto" if tools else None
        )
        
        # Add assistant response to history (only if using history)
        if use_history and session_lock:
            with session_lock:
                session["dialog"].append({"role": "assistant", "content": response})
        
        return response
            
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        logger.error(f"Session {session_id}: {error_msg}")
        raise
```

**AFTER:**
```python
def process_message(
    self,
    session_id: str,
    system_prompt: str,
    user_message: str,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_tools: bool = True,
    use_history: bool = True,
    max_history_messages: Optional[int] = None  # NEW
) -> str:
    """
    Process a user message and generate a response.
    
    Args:
        session_id: Session identifier
        system_prompt: System prompt
        user_message: User's message
        temperature: Sampling temperature
        top_p: Top-p sampling
        max_tokens: Maximum tokens
        use_tools: Whether to enable function calling tools
        use_history: Whether to maintain conversation history (disable for stateless calls like maze game)
        max_history_messages: Maximum number of user/assistant message pairs to keep (excluding system prompt). 
                             If not specified, uses self.max_history_messages.
        
    Returns:
        Generated response (may include function calls)
    """
    # Determine effective max_history_messages
    effective_max_history_messages = max_history_messages if max_history_messages is not None else self.max_history_messages
    
    if use_history:
        # Get or create session with history
        session = self.get_or_create_session(session_id, system_prompt)
        session_lock = self.session_locks.get(session_id, threading.RLock())
        
        # Build the prompt first (with minimal locking)
        with session_lock:
            # Add user message to dialog
            session["dialog"].append({"role": "user", "content": user_message})
            session["message_count"] += 1
            
            # Trim history based on max_history_messages if set
            if effective_max_history_messages is not None:
                # Keep system message + last N user/assistant message pairs
                # Calculate how many non-system messages to keep
                non_system_messages = session["dialog"][1:]  # Skip system message
                
                # Keep only the last (max_history_messages * 2) non-system messages
                # because each pair is user + assistant response
                messages_to_keep = effective_max_history_messages * 2
                if len(non_system_messages) > messages_to_keep:
                    # Keep system message + recent messages
                    session["dialog"] = [session["dialog"][0]] + non_system_messages[-messages_to_keep:]
                    logger.debug(f"Trimmed dialog to {len(session['dialog'])} messages (max_history_messages={effective_max_history_messages})")
            else:
                # Simple trimming: keep only last N messages (old behavior)
                max_messages = 20
                if len(session["dialog"]) > max_messages:
                    # Keep system message and last N-1 messages
                    session["dialog"] = [session["dialog"][0]] + session["dialog"][-(max_messages-1):]
            
            # Prepare messages for API call
            messages = session["dialog"].copy()
    else:
        # Stateless mode: just system + user message (no history)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        session_lock = None
    
    # Now do inference WITHOUT holding session lock!
    try:
        # Use tools if requested (for maze game with function calling)
        tools = MAZE_GAME_TOOLS if use_tools else None
        
        response = self.llm_client.generate(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice="auto" if tools else None
        )
        
        # Add assistant response to history (only if using history)
        if use_history and session_lock:
            with session_lock:
                session["dialog"].append({"role": "assistant", "content": response})
        
        return response
            
    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        logger.error(f"Session {session_id}: {error_msg}")
        raise
```

**Changes:**
- ✅ Added `max_history_messages: Optional[int] = None` parameter
- ✅ Compute effective limit from parameter or instance variable
- ✅ If `effective_max_history_messages` is set, use message-pair counting instead of token counting
- ✅ Keep system message + last (N × 2) non-system messages
- ✅ Log when trimming happens

---

## File 2: backend/app/services/llm_service.py

### UnifiedLLMService.process_message()

**BEFORE:**
```python
def process_message(
    self,
    session_id: str,
    system_prompt: str,
    user_message: str,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_tools: bool = True,
    use_history: bool = True
) -> str:
    """
    Process a session-based message (SSE mode only).
    
    Args:
        session_id: Session identifier
        system_prompt: System prompt
        user_message: User's message
        temperature: Sampling temperature
        top_p: Top-p sampling
        max_tokens: Maximum tokens
        use_tools: Whether to enable function calling tools
        use_history: Whether to maintain conversation history (disable for stateless calls like maze game)
        
    Returns:
        Generated response
        
    Raises:
        RuntimeError: If called in MQTT mode or service unavailable
    """
    if not self.is_sse_mode():
        raise RuntimeError(...)
    
    session_manager = self.get_session_manager()
    if session_manager is None:
        raise RuntimeError(...)
    
    return session_manager.process_message(
        session_id=session_id,
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        use_tools=use_tools,
        use_history=use_history
    )
```

**AFTER:**
```python
def process_message(
    self,
    session_id: str,
    system_prompt: str,
    user_message: str,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_tools: bool = True,
    use_history: bool = True,
    max_history_messages: Optional[int] = None  # NEW
) -> str:
    """
    Process a session-based message (SSE mode only).
    
    Args:
        session_id: Session identifier
        system_prompt: System prompt
        user_message: User's message
        temperature: Sampling temperature
        top_p: Top-p sampling
        max_tokens: Maximum tokens
        use_tools: Whether to enable function calling tools
        use_history: Whether to maintain conversation history (disable for stateless calls like maze game)
        max_history_messages: Maximum number of user/assistant message pairs to keep (excluding system prompt)
        
    Returns:
        Generated response
        
    Raises:
        RuntimeError: If called in MQTT mode or service unavailable
    """
    if not self.is_sse_mode():
        raise RuntimeError(...)
    
    session_manager = self.get_session_manager()
    if session_manager is None:
        raise RuntimeError(...)
    
    return session_manager.process_message(
        session_id=session_id,
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        use_tools=use_tools,
        use_history=use_history,
        max_history_messages=max_history_messages  # NEW
    )
```

**Changes:**
- ✅ Added `max_history_messages: Optional[int] = None` parameter
- ✅ Passed through to session_manager.process_message()

---

## File 3: backend/app/routers/mqtt_bridge.py

### /publish_state endpoint

**BEFORE:**
```python
logger.info(f"[SSE MODE] Calling LLM with session_id={session_id}, use_tools=False, use_history=False")

# Generate hint WITHOUT function calling and WITHOUT history
# - use_tools=False: llama.cpp doesn't support tools without --jinja flag
# - use_history=False: maze game publishes state every 3 seconds, history fills context quickly
# The template should contain instructions for JSON response format instead
hint_response = llm_service.process_message(
    session_id=session_id,
    system_prompt=system_prompt,
    user_message=user_message,
    use_tools=False,  # Disable OpenAI tools API - use prompt-based guidance instead
    use_history=False  # Disable history - maze game is stateless, state is in each request
)
```

**AFTER:**
```python
logger.info(f"[SSE MODE] Calling LLM with session_id={session_id}, use_tools=False, use_history=True, max_history_messages=3")

# Generate hint with LLM memory enabled
# - use_tools=False: llama.cpp doesn't support tools without --jinja flag
# - use_history=True: Enable conversation memory to provide contextual hints
# - max_history_messages=3: Limit to 3 message pairs to prevent context overflow
# The template should contain instructions for JSON response format instead
hint_response = llm_service.process_message(
    session_id=session_id,
    system_prompt=system_prompt,
    user_message=user_message,
    use_tools=False,  # Disable OpenAI tools API - use prompt-based guidance instead
    use_history=True,  # Enable history for contextual maze guidance
    max_history_messages=3  # Limit to 3 message pairs (6 total messages + system prompt)
)
```

**Changes:**
- ✅ Changed `use_history` from `False` to `True`
- ✅ Added `max_history_messages=3`
- ✅ Updated comments to explain the change
- ✅ Updated log message

### /request_hint endpoint

**Same changes as `/publish_state`:**
- ✅ Changed `use_history` from `False` to `True`
- ✅ Added `max_history_messages=3`
- ✅ Updated comments and logs

---

## Summary of Changes

| Component | Type | Changes |
|-----------|------|---------|
| **SessionManager.__init__()** | Modified | +1 parameter, +1 instance var, +2 log lines |
| **SessionManager.process_message()** | Modified | +1 parameter, +20 lines (trimming logic) |
| **SessionManager.process_message_stream()** | Modified | +1 parameter, +20 lines (trimming logic) |
| **UnifiedLLMService.process_message()** | Modified | +1 parameter, +1 line (pass-through) |
| **UnifiedLLMService.process_message_stream()** | Modified | +1 parameter, +1 line (pass-through) |
| **mqtt_bridge.py /publish_state** | Modified | Changed use_history + added parameter |
| **mqtt_bridge.py /request_hint** | Modified | Changed use_history + added parameter |
| **Documentation** | New | 3 new files (800+ lines) |

**Total Lines Added**: ~150 (code) + 800 (docs)  
**Total Lines Modified**: ~20 (in existing methods)  
**Files Changed**: 3 code files + 3 docs  
**Backward Compatibility**: ✅ 100%

---

**Implementation**: Complete ✅  
**Testing**: Ready  
**Deployment**: Ready to Go
