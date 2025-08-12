import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import ALLOWED_ORIGINS
from .database import Base, engine
from . import models
from .routers import auth, templates, leaderboard, mqtt_bridge, profile, friends, messages, settings, users
from .mqtt import start_mqtt, stop_mqtt
from .websocket import websocket_endpoint
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Prompt Portal (LAM Hackathon)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for profile pictures
uploads_dir = "uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(templates.router)
app.include_router(leaderboard.router)
app.include_router(mqtt_bridge.router)
app.include_router(profile.router)
app.include_router(friends.router)
app.include_router(messages.router)
app.include_router(settings.router)

# WebSocket endpoint
@app.websocket("/ws/{token}")
async def websocket_messages(websocket: WebSocket, token: str):
    await websocket_endpoint(websocket, token)

@app.on_event("startup")
def startup_event():
    start_mqtt()

@app.on_event("shutdown")
def shutdown_event():
    stop_mqtt()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
