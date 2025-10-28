from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, ALLOWED_ORIGINS
from .database import init_db
from .mqtt_client import start as mqtt_start, stop as mqtt_stop
from .routers.chat import router as chat_router
from .routers.templates import router as templates_router
from .routers.stream import router as stream_router


app = FastAPI(title="OwOGPT API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    init_db()
    if settings.LLM_PROVIDER.lower() == "mqtt":
        mqtt_start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if settings.LLM_PROVIDER.lower() == "mqtt":
        mqtt_stop()


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


app.include_router(chat_router)
app.include_router(templates_router)
app.include_router(stream_router)


