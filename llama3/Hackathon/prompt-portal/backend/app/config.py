from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    SECRET_KEY: str = "change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./app.db"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    MQTT_BROKER_HOST: str = "47.89.252.2"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str = "prompt_portal_backend"
    MQTT_USERNAME: str = "TangClinic"
    MQTT_PASSWORD: str = "Tang123"
    MQTT_TOPIC_HINT: str = "maze/hint/+"
    MQTT_TOPIC_STATE: str = "maze/state"
    MQTT_TOPIC_TEMPLATE: str = "maze/template"

    class Config:
        env_file = ".env"

settings = Settings()
ALLOWED_ORIGINS: List[str] = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
