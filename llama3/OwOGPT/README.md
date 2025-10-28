# OwOGPT

A modern, full-stack GPT chat experience with a beautiful UI and robust Python backend. Supports MQTT, OpenAI, and Ollama providers; prompt templates; sessions; messages; and SSE streaming.

## Backend (FastAPI)

- Path: `OwOGPT/backend`
- Run:
  - Windows PowerShell:
    ```powershell
    cd OwOGPT/backend
    python -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    pip install -r requirements.txt
    copy .env.example .env
    python run_server.py
    ```
- Health: `GET http://localhost:8009/api/health`
- MQTT topics (default):
  - `owogpt/user_input`
  - `owogpt/assistant_response`
  - `owogpt/template`
- Switch provider via `.env` → `LLM_PROVIDER=mqtt|openai|ollama`

## Frontend (React + Vite + Chakra)

- Path: `OwOGPT/frontend`
- Run:
  ```bash
  cd OwOGPT/frontend
  npm i
  npm run dev
  ```
- Dev server uses proxy to backend at `http://localhost:8009`.

## Features

- Session management, messages, prompt templates
- Provider abstraction (MQTT/OpenAI/Ollama)
- SSE endpoint `/api/chat/stream` for incremental UX
- Dark, minimal UI distinct from prompt-portal

## Notes

- To integrate with existing `prompt-portal` MQTT deployment, ensure topics and credentials match its broker.
- For Ollama, run `ollama serve` and set `OLLAMA_HOST` + `OLLAMA_MODEL` in `.env`.


