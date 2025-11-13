from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    SECRET_KEY: str = "change_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    DATABASE_URL: str = "sqlite:///./app.db"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # LLM Communication Mode: 'mqtt' or 'sse'
    LLM_COMM_MODE: str = "mqtt"
    
    # MQTT Configuration (used when LLM_COMM_MODE='mqtt')
    MQTT_BROKER_HOST: str = "47.89.252.2"
    MQTT_BROKER_PORT: int = 1883
    MQTT_CLIENT_ID: str = "prompt_portal_backend"
    MQTT_USERNAME: str = "TangClinic"
    MQTT_PASSWORD: str = "Tang123"
    MQTT_TOPIC_HINT: str = "maze/hint/+"
    MQTT_TOPIC_STATE: str = "maze/state"
    MQTT_TOPIC_USER_INPUT: str = "prompt_portal/user_input"
    MQTT_TOPIC_ASSISTANT_RESPONSE: str = "prompt_portal/assistant_response"
    MQTT_TOPIC_TEMPLATE: str = "maze/template"
    
    # SSE/Direct HTTP Configuration (used when LLM_COMM_MODE='sse')
    LLM_SERVER_URL: str = "http://localhost:8080"
    LLM_TIMEOUT: int = 300
    LLM_TEMPERATURE: float = 0.6
    LLM_TOP_P: float = 0.9
    LLM_MAX_TOKENS: int = 512
    LLM_SKIP_THINKING: bool = True
    LLM_MAX_HISTORY_TOKENS: int = 10000

    # Voice Chat - SST (Speech-to-Text) Configuration
    SST_BROKER_URL: str = "http://localhost:8082"
    SST_REQUEST_TIMEOUT: int = 300
    
    # Voice Chat - TTS (Text-to-Speech) Configuration
    TTS_BROKER_URL: str = "http://localhost:8081"
    TTS_REQUEST_TIMEOUT: int = 30

    # Vision configuration
    LLM_VISION_ENABLED: bool = True  # When True, attempt to send images to VLM
    LLM_VISION_MODE: str = "auto"    # e.g., "auto", "openai-compatible" (for chat.completions with images)

    class Config:
        env_file = ".env"

settings = Settings()
ALLOWED_ORIGINS: List[str] = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
'''
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
   apt-get update
'''