# OwOGPT Quick Start

A modern, full-stack GPT chat app with MQTT/OpenAI/Ollama support and prompt template management.

## 1. Start Backend

```powershell
cd OwOGPT/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Reset database (first time or if schema changes)
python reset_db.py

# Start server
python run_server.py
```

Backend runs on http://localhost:8009

**Important**: Run `python reset_db.py` if you see database errors about NULL constraints.

## 2. Start Frontend

```bash
cd OwOGPT/frontend
npm install
npm run dev
```

Frontend runs on http://localhost:5174

## 3. Start LLM Service (MQTT mode)

For MQTT provider, run the llama.cpp deployment:

```bash
cd ../../
python llamacpp_mqtt_deploy.py --projects prompt_portal --mqtt_username TangClinic --mqtt_password Tang123
```

## Features

### Chat Sessions
- Create multiple chat sessions
- Switch between sessions
- Delete sessions via dropdown menu

### Prompt Templates
- Create/edit/delete templates via modal UI
- Switch templates dynamically from dropdown
- **Auto-reset**: Switching templates automatically deletes MQTT session and clears conversation history
- **Persistent preference**: Selected template is saved to localStorage and restored on reload
- Hot-update system prompts via MQTT with `reset=True`

### Providers
- **MQTT**: Uses `llamacpp_mqtt_deploy.py` with topics:
  - `prompt_portal/user_input`
  - `prompt_portal/assistant_response/{sessionId}/{clientId}/{requestId}`
  - `prompt_portal/template`
- **OpenAI**: Set `OPENAI_API_KEY` in `.env`
- **Ollama**: Run `ollama serve` locally

## Configuration

Edit `OwOGPT/backend/.env`:

```env
LLM_PROVIDER=mqtt
MQTT_BROKER_HOST=47.89.252.2
MQTT_USERNAME=TangClinic
MQTT_PASSWORD=Tang123
```

Switch provider: `LLM_PROVIDER=mqtt|openai|ollama`

## MQTT Topics

Aligned with `vllm_test_client.py` pattern:
- User input: `prompt_portal/user_input`
- Assistant response: `prompt_portal/assistant_response/{sessionId}/{clientId}/{requestId}`
- Template update: `prompt_portal/template`

## API Endpoints

- `POST /api/chat/sessions` - Create session
- `GET /api/chat/sessions` - List sessions
- `DELETE /api/chat/sessions/{id}` - Delete session
- `PATCH /api/chat/sessions/{id}` - Update session
- `POST /api/chat/messages` - Send message
- `GET /api/templates/` - List templates
- `POST /api/templates/` - Create template
- `PATCH /api/templates/{id}` - Update template
- `DELETE /api/templates/{id}` - Delete template

