# Prompt Portal (Frontend Prompt Template Submission Website)

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

## Setup & Run

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

## Extending the System

- Add fields to `PromptTemplate` (e.g., tags, language, model hints)
- Track richer analytics in `Score` (e.g., per-level metrics)
- Add an endpoint for games to fetch the **active prompt** for a user or session
- Add admin roles and moderation features
- Provide per-session state history persistence (e.g., store incoming hints and states)

---

## Suggested Prompt Template Guidelines

- Instruct the LAM to return **strict JSON** with keys like `hints`, `path`, `break_walls`.
- Encourage short, actionable hints and avoid verbose prose.
- Ensure structure is consistent for easy parsing by the game.

---

## License

For hackathon/demo use. Replace as needed.
