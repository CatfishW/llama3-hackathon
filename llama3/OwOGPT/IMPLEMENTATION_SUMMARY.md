# OwOGPT Implementation Summary

## Overview
OwOGPT is a modern, full-stack chat application following the MQTT communication pattern from `prompt-portal` and compatible with `llamacpp_mqtt_deploy.py`.

## Key Features

### 1. MQTT Integration (Compatible with vllm_test_client.py pattern)
- **Topics**:
  - User input: `prompt_portal/user_input`
  - Assistant response: `prompt_portal/assistant_response/{sessionId}/{clientId}/{requestId}`
  - Template updates: `prompt_portal/template`
  
- **Message Flow**:
  1. Backend publishes user message with `replyTopic` field
  2. Subscribes to wildcard: `prompt_portal/assistant_response/#`
  3. Extracts `requestId` from topic path to resolve pending futures
  4. Compatible with `llamacpp_mqtt_deploy.py --projects prompt_portal`

### 2. Backend Features (FastAPI)

#### Chat Management
- `POST /api/chat/sessions` - Create new session
- `GET /api/chat/sessions` - List all sessions
- `PATCH /api/chat/sessions/{id}` - Update session (title, template, system_prompt)
- `DELETE /api/chat/sessions/{id}` - Delete session
- `GET /api/chat/sessions/{id}/messages` - Get message history
- `POST /api/chat/messages` - Send message and get response

#### Template Management
- `GET /api/templates/` - List templates
- `POST /api/templates/` - Create template
- `PATCH /api/templates/{id}` - Update template
- `DELETE /api/templates/{id}` - Delete template

#### Provider Abstraction
- **MQTT Provider**: Uses paho-mqtt with request/response correlation
- **OpenAI Provider**: Direct OpenAI API calls
- **Ollama Provider**: Local ollama HTTP API
- Configured via `LLM_PROVIDER` env var

### 3. Frontend Features (React + TypeScript + Chakra UI)

#### Session Management
- Create/delete sessions via sidebar
- Dropdown menu on each session for delete action
- Switch between sessions preserves message history

#### Template Management
- Template selector dropdown in header
- Edit icon opens management menu:
  - Create new template
  - Edit existing template
  - Delete template
- Modal for CRUD operations with title, description, system prompt fields
- Hot-update: Switching template updates current session and sends MQTT template message

#### Chat Interface
- Modern dark theme
- Message bubbles (user: blue, assistant: gray)
- Real-time message streaming
- Loading indicators

### 4. MQTT Message Format (Following vllm_test_client.py)

**User Input**:
```json
{
  "sessionId": "user-abc123",
  "message": "Hello",
  "requestId": "req-xyz789",
  "clientId": "owogpt_backend_a1b2c3d4",
  "replyTopic": "prompt_portal/assistant_response/user-abc123/owogpt_backend_a1b2c3d4/req-xyz789",
  "systemPrompt": "You are a helpful assistant",
  "temperature": 0.7,
  "topP": 0.9,
  "maxTokens": 512
}
```

**Assistant Response** (published to `replyTopic`):
```json
{
  "response": "Hello! How can I help you?",
  "requestId": "req-xyz789"
}
```

**Template Update**:
```json
{
  "sessionId": "user-abc123",
  "systemPrompt": "New system prompt",
  "template": {"content": "New system prompt"}
}
```

### 5. Database Schema (SQLite)

**prompt_templates**:
- id, user_id, title, description, content, is_active, version, created_at, updated_at

**chat_sessions**:
- id, session_key, user_id, title, template_id, system_prompt, temperature, top_p, max_tokens, message_count, created_at, updated_at, last_used_at

**chat_messages**:
- id, session_id, role, content, metadata_json, request_id, created_at

## Running the System

### 1. Backend
```powershell
cd OwOGPT/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_server.py
```

### 2. Frontend
```bash
cd OwOGPT/frontend
npm install
npm run dev
```

### 3. LLM Service (MQTT)
```bash
python llamacpp_mqtt_deploy.py \
  --projects prompt_portal \
  --mqtt_username TangClinic \
  --mqtt_password Tang123 \
  --server_url http://localhost:8080
```

## Configuration

**Backend** (`OwOGPT/backend/app/config.py`):
- MQTT topics: `prompt_portal/*` (aligned with llamacpp_mqtt_deploy.py)
- Broker: `47.89.252.2:1883`
- Auth: `TangClinic/Tang123`

**Frontend** (`OwOGPT/frontend/vite.config.ts`):
- Proxies `/api` to `http://localhost:8009`

## Differences from prompt-portal

1. **Simpler UI**: No social features, leaderboards, or maze game
2. **Focus on Templates**: Template CRUD is primary feature
3. **Session Management**: Direct session deletion from UI
4. **Dark Theme**: Different color scheme (more blue tones)
5. **Minimal**: No authentication (can be added later)

## MQTT Compatibility

✅ Compatible with `vllm_test_client.py`:
- Uses same topic structure
- Includes `replyTopic` in payload
- Subscribes with wildcard pattern
- Extracts request ID from topic

✅ Compatible with `llamacpp_mqtt_deploy.py`:
- Project name: `prompt_portal`
- Topic structure matches expected pattern
- Template updates work via MQTT

## Future Enhancements

- [ ] User authentication
- [ ] Streaming responses (SSE already implemented)
- [ ] Message regeneration
- [ ] Export chat history
- [ ] Multi-modal support (images)
- [ ] Conversation branching

