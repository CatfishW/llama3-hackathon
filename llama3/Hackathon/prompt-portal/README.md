# Prompt Portal (Frontend Prompt Template Submission Website)

🌐 **Live at: [lammp.agaii.org](https://lammp.agaii.org)**

This repository contains a full-stack web application to manage and evaluate **prompt templates** for a LAM-powered Maze Game.
It supports **user registration/login (JWT)**, **prompt template CRUD**, **leaderboard**, and **real-time MQTT hint monitoring** with a **FastAPI** backend and a **React (Vite + TypeScript)** frontend.

> **Security Note**: All logging has been disabled in this application to protect user privacy and prevent data storage on the server.

> MQTT is brokered by the backend (paho-mqtt). Clients connect to a WebSocket to receive `maze/hint/{sessionId}` updates.
> The backend also provides an endpoint to publish game `maze/state` messages that include the selected **prompt template** content.

---

## Features

- User registration & login (JWT)
- Prompt template CRUD (title, description, content, versioning, active flag)
- Leaderboard submissions and ranking
- MQTT integration:
  - Backend subscribes to `MQTT_TOPIC_HINT` (default `maze/hint/+`) and forwards messages to clients via WebSocket `/api/mqtt/ws/hints/{sessionId}`
  - Backend publishes state to `MQTT_TOPIC_STATE` (default `maze/state`) with the selected prompt template embedded
- Test & Monitor page (frontend) to:
  - Select one of your templates
  - Enter a `sessionId`
  - Connect to live hints
  - Publish a dummy state to test end-to-end plumbing

All configuration is environment-driven for easy maintenance and extension.

---

## Tech Stack

**Backend (Python / FastAPI)**
- FastAPI, SQLAlchemy (SQLite default), paho-mqtt
- JWT auth (`python-jose`, `passlib`)
- WebSocket stream for per-session hints
- REST APIs for auth, templates, leaderboard, and MQTT bridge
- **LLM Integration**: Dual communication modes (MQTT / SSE)
  - Direct HTTP/SSE communication with llama.cpp server
  - OpenAI-compatible API client for LLM inference

**Frontend (React + Vite + TypeScript)**
- Axios for HTTP
- React Router for navigation
- Simple, clean UI with pages for Register/Login/Dashboard/Templates/Leaderboard/Test&Monitor

---

## Project Structure

```
prompt-portal/
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── deps.py
│       ├── mqtt.py
│       ├── utils/
│       │   └── security.py
│       └── routers/
│           ├── auth.py
│           ├── templates.py
│           ├── leaderboard.py
│           └── mqtt_bridge.py
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api.ts
        ├── auth/
        │   └── AuthContext.tsx
        ├── components/
        │   ├── Navbar.tsx
        │   └── TemplateForm.tsx
        └── pages/
            ├── Dashboard.tsx
            ├── Register.tsx
            ├── Login.tsx
            ├── Templates.tsx
            ├── NewTemplate.tsx
            ├── TemplateEdit.tsx
            ├── Leaderboard.tsx
            └── TestMQTT.tsx
```

---

## 🚀 Quick Start

### LLM Communication Modes

The framework supports two modes for communicating with LLM servers:

#### **MQTT Mode** (Traditional)
- Uses MQTT broker for pub/sub communication
- Ideal for distributed systems and multiple services
- Requires MQTT broker with public IP

#### **SSE Mode** (Simplified - **NEW!**)
- Direct HTTP/SSE communication with llama.cpp server
- **Perfect for 2-machine setups** (GPU server + web server)
- Works with reverse SSH tunneling for private networks
- Lower latency, easier debugging

**📚 See [SSE_QUICK_REFERENCE.md](./SSE_QUICK_REFERENCE.md) for quick setup**
**📘 See [TWO_MACHINE_SETUP.md](./TWO_MACHINE_SETUP.md) for complete 2-machine guide**

### Production Deployment with Custom Domain

**For deploying to lammp.agaii.org:**

```bash
# 1. Configure DNS A record pointing to your server IP
# 2. Run automated domain setup
chmod +x setup-domain.sh
./setup-domain.sh
```

See [DOMAIN_QUICK_GUIDE.md](./DOMAIN_QUICK_GUIDE.md) for quick instructions or [DOMAIN_SETUP.md](./DOMAIN_SETUP.md) for detailed documentation.

### Standard Deployment

For general server deployment without custom domain:

```bash
# Quick deployment (development mode)
chmod +x deploy.sh
./deploy.sh

# During deployment, choose:
# - MQTT mode: Traditional with broker
# - SSE mode: Direct connection (new!)

# Or production deployment with Nginx
chmod +x deploy-production.sh
./deploy-production.sh
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

---

## 💻 Local Development Setup

### 1) Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create .env from example and adjust
cp .env.example .env
# Edit .env to set SECRET_KEY and MQTT settings.
# If your broker supports only TCP (1883), keep defaults.
# If you host frontend at a different origin, update CORS_ORIGINS accordingly.

# Start the API
uvicorn app.main:app --reload --port 8000
```

The backend will:
- Create the SQLite DB `app.db` automatically
- Start the MQTT client and subscribe to `MQTT_TOPIC_HINT`
- Expose REST and WebSocket endpoints

**Key endpoints (base http://localhost:8000):**
- `POST /api/auth/register`
- `POST /api/auth/login`  → returns `{ access_token }`
- `GET /api/templates` (auth) list your templates
- `POST /api/templates` (auth) create a template
- `PATCH /api/templates/{id}` (auth) update
- `DELETE /api/templates/{id}` (auth) delete
- `GET /api/leaderboard?limit=20`
- `POST /api/leaderboard/submit` (auth) submit a score
- `POST /api/mqtt/publish_state` (auth) publish a state JSON **including your selected template** to the broker
- `GET /api/mqtt/last_hint?session_id=...`
- `WS /api/mqtt/ws/hints/{sessionId}` receive per-session hints in real time

> The `publish_state` endpoint enriches your payload with the selected prompt template:
> ```json
> {
>   "sessionId": "...",
>   "prompt_template": {
>     "title": "...",
>     "content": "...",
>     "version": 1,
>     "user_id": 123
>   },
>   "... other state fields ..."
> }
> ```

### 2) Frontend

```bash
cd frontend
npm install
# Configure API base and WS base via Vite env (optional). Defaults:
#   VITE_API_BASE=http://localhost:8000
#   VITE_WS_BASE=ws://localhost:8000
npm run dev
```

Open http://localhost:5173

- Register a new account
- Create a prompt template
- Go to **Test & Monitor**
  - Enter a `sessionId`
  - Connect to WS
  - Click **Publish Dummy State** to publish to MQTT via backend
  - If your LAM / game responds to `maze/state` by publishing to `maze/hint/{sessionId}`, you’ll see messages stream in

### Environment Notes

- **MQTT**: configured via backend `.env`. Default topics:
  - `MQTT_TOPIC_STATE=maze/state`
  - `MQTT_TOPIC_HINT=maze/hint/+` (subscribes to all sessionIds)
- If your MQTT broker requires TLS or auth, update the `mqtt.py` to set TLS and credentials.

---

## 🔧 Advanced Setup

### Two-Machine Deployment (GPU Server + Web Server)

If you have a GPU server without public IP and a separate web server:

1. **Machine A (GPU Server)**: Run llama.cpp + reverse SSH tunnel
2. **Machine B (Web Server)**: Run frontend + backend in SSE mode

**Quick Start:**
```bash
# Machine A (GPU server)
./start_llm_server.sh

# Machine B (web server)
./deploy.sh
# Choose SSE mode when prompted
```

**Complete Guide**: See [TWO_MACHINE_SETUP.md](./TWO_MACHINE_SETUP.md)

### Helper Scripts

- `maintain_tunnel.sh` - Auto-reconnecting SSH tunnel (Linux/Mac)
- `maintain_tunnel.bat` - Auto-reconnecting SSH tunnel (Windows)
- `start_llm_server.sh` - Quick start for LLM server + tunnel

## Extending the System

- Add fields to `PromptTemplate` (e.g., tags, language, model hints)
- Track richer analytics in `Score` (e.g., per-level metrics)
- Add an endpoint for games to fetch the **active prompt** for a user or session
- Add admin roles and moderation features
- Provide per-session state history persistence (e.g., store incoming hints and states)
- Scale LLM infrastructure with multiple GPU servers

---

## Suggested Prompt Template Guidelines

- Instruct the LAM to return **strict JSON** with keys like `hints`, `path`, `break_walls`.
- Encourage short, actionable hints and avoid verbose prose.
- Ensure structure is consistent for easy parsing by the game.

---

## 📚 Documentation

### Quick References
- **[DUAL_MODE_QUICK_REFERENCE.md](./DUAL_MODE_QUICK_REFERENCE.md)** - 📋 Quick reference card for both modes
- **[SSE_QUICK_REFERENCE.md](./SSE_QUICK_REFERENCE.md)** - ⚡ Command cheat sheet for SSE mode

### Setup Guides
- **[TWO_MACHINE_SETUP.md](./TWO_MACHINE_SETUP.md)** - 🖥️ Complete guide for 2-machine deployment
- **[SSE_MODE_DEPLOYMENT.md](./SSE_MODE_DEPLOYMENT.md)** - 🚀 Detailed SSE mode deployment guide
- **[DOMAIN_SETUP.md](./DOMAIN_SETUP.md)** - 🌐 Custom domain configuration guide
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - 📦 General deployment instructions

### Implementation Details
- **[COMPLETE_SSE_IMPLEMENTATION.md](./COMPLETE_SSE_IMPLEMENTATION.md)** - ✅ Complete implementation summary
- **[SSE_IMPLEMENTATION_SUMMARY.md](./SSE_IMPLEMENTATION_SUMMARY.md)** - 🔧 Technical overview of SSE changes
- **[SSE_CHATBOT_FIX.md](./SSE_CHATBOT_FIX.md)** - 💬 Chatbot dual-mode implementation
- **[MAZE_GAME_SSE_SUPPORT.md](./MAZE_GAME_SSE_SUPPORT.md)** - 🎮 Maze game dual-mode implementation
- **[MAZE_GAME_SSE_FIX.md](./MAZE_GAME_SSE_FIX.md)** - 🔧 Maze game JSON parsing fix
- **[STREAMING_MODE_GUIDE.md](./STREAMING_MODE_GUIDE.md)** - 📡 Real-time streaming implementation

### Feature-Specific Guides
- **[DEBUG_LOGGING_GUIDE.md](./docs/DEBUG_LOGGING_GUIDE.md)** - 🐛 Debugging and logging
- **[CUSTOM_SYSTEM_PROMPT_GUIDE.md](./docs/CUSTOM_SYSTEM_PROMPT_GUIDE.md)** - 📝 Custom prompts
- **[CONCURRENCY_FIX_GUIDE.md](./docs/CONCURRENCY_FIX_GUIDE.md)** - ⚙️ Concurrent processing

### Architecture & Design
- **[LAM_ARCHITECTURE_DIAGRAMS.md](./LAM_ARCHITECTURE_DIAGRAMS.md)** - 📊 System architecture diagrams
- **[MERMAID_DIAGRAMS_LAM_MAZE.md](./MERMAID_DIAGRAMS_LAM_MAZE.md)** - 🎨 Visual system diagrams

---

## License

For hackathon/demo use. Replace as needed.
