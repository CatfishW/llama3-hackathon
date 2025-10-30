import uvicorn
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import ALLOWED_ORIGINS
from .database import Base, engine
from . import models
from .routers import auth, templates, leaderboard, mqtt_bridge, profile, friends, messages, settings, users, chatbot, announcements, driving
from .mqtt import start_mqtt, stop_mqtt
from .websocket import websocket_endpoint
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Prompt Portal (LAM Hackathon)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r".*",  # Allow any origin in dev; specific origins still honored
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static files for profile pictures
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(templates.router)
app.include_router(leaderboard.router)
app.include_router(driving.router)  # Driving game - separate from leaderboard
app.include_router(mqtt_bridge.router)
app.include_router(profile.router)
app.include_router(friends.router)
app.include_router(messages.router)
app.include_router(settings.router)
app.include_router(chatbot.router)
app.include_router(announcements.router)

# WebSocket endpoint
@app.websocket("/ws/{token}")
async def websocket_messages(websocket: WebSocket, token: str):
    await websocket_endpoint(websocket, token)

# Explicit catch-all OPTIONS handler to guarantee CORS preflight success
@app.options("/{full_path:path}")
async def options_preflight(full_path: str, request: Request):
    # Mirror the requesting origin when present (needed if credentials are allowed)
    origin = request.headers.get("origin", "*")
    acrh = request.headers.get("access-control-request-headers", "*")
    resp = Response(status_code=204)
    if origin != "*":
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
    else:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    resp.headers["Access-Control-Allow-Headers"] = acrh
    return resp

@app.on_event("startup")
def startup_event():
    start_mqtt()

@app.on_event("shutdown")
def shutdown_event():
    stop_mqtt()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
