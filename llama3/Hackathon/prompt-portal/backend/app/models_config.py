"""
Multi-Model Configuration System

This module manages multiple LLM model configurations including
OpenAI-compatible endpoints with different providers.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import json
import os
from pathlib import Path
try:
    import httpx
except ImportError:
    httpx = None
import logging

logger = logging.getLogger(__name__)



class ModelConfig(BaseModel):
    """Configuration for a single LLM model"""
    name: str = Field(..., description="Display name of the model")
    provider: str = Field(..., description="Provider (openai, anthropic, etc.)")
    model: str = Field(..., description="Model identifier for API calls")
    apiBase: str = Field(..., description="API base URL")
    apiKey: str = Field(..., description="API key for authentication")
    description: Optional[str] = Field(None, description="Optional model description")
    features: Optional[List[str]] = Field(default_factory=list, description="Model features/capabilities")
    maxTokens: Optional[int] = Field(None, description="Maximum context/output tokens")
    supportsFunctions: Optional[bool] = Field(True, description="Supports function calling")
    supportsVision: Optional[bool] = Field(False, description="Supports vision/image inputs")
    autoDetect: Optional[bool] = Field(False, description="Whether to auto-detect model name from endpoint")



class ModelsConfigManager:
    """Manager for loading and accessing model configurations"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the models configuration manager.
        
        Args:
            config_path: Path to models.json. If None, uses default location.
        """
        if config_path is None:
            # Default to backend/app/models.json
            config_path = os.path.join(os.path.dirname(__file__), "models.json")
        
        self.config_path = config_path
        self.models: List[ModelConfig] = []
        self._load_models()
    
    def _load_models(self):
        """Load models from configuration file"""
        if not os.path.exists(self.config_path):
            # Create default configuration
            self._create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                models_data = data.get('models', [])
                self.models = [ModelConfig(**model) for model in models_data]
            
            # Perform auto-detection for marked models
            self.refresh_auto_detected_models()
        except Exception as e:
            print(f"Warning: Failed to load models config: {e}")
            self.models = self._get_default_models()
            self.refresh_auto_detected_models()
    
    def _create_default_config(self):
        """Create default models.json configuration"""
        default_config = {
            "version": "1.0.0",
            "models": [model.dict() for model in self._get_default_models()]
        }
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
    
    def _get_default_models(self) -> List[ModelConfig]:
        """Get default model configurations"""
        return [
            ModelConfig(
                name="AGAII Cloud MLLM (Vision)",
                provider="vllm",
                model="mllm",
                apiBase="https://game.agaii.org/mllm/v1",
                apiKey="not-needed",
                description="AGAII Cloud MLLM - Advanced multi-modal model, no API key required",
                features=["No API Key", "Vision Support", "Multi-modal", "Cloud Hosted"],
                maxTokens=8192,
                supportsFunctions=True,
                supportsVision=True,
                autoDetect=True
            ),
            ModelConfig(
                name="AGAII Cloud LLM",
                provider="vllm",
                model="Qwen/Qwen3-VL-8B-Instruct-FP8",
                apiBase="https://game.agaii.org/llm",
                apiKey="not-needed",
                description="AGAII Cloud VLM - Qwen3 Vision-Language model, no API key required",
                features=["No API Key", "Vision Support", "Function Calling", "Cloud Hosted"],
                maxTokens=8192,
                supportsFunctions=True,
                supportsVision=True,
                autoDetect=True
            ),
            ModelConfig(
                name="DeepSeek V3.2 (NVIDIA)",
                provider="openai",
                model="deepseek-ai/deepseek-v3.2",
                apiBase="https://integrate.api.nvidia.com/v1",
                apiKey="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",
                description="NVIDIA Integrate API - DeepSeek V3.2",
                features=["NVIDIA Integrate", "Cloud Hosted"],
                maxTokens=8192,
                supportsFunctions=True,
                supportsVision=False
            ),
            ModelConfig(
                name="GPT OSS 120B (NVIDIA)",
                provider="openai",
                model="openai/gpt-oss-120b",
                apiBase="https://integrate.api.nvidia.com/v1",
                apiKey="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",
                description="NVIDIA Integrate API - GPT OSS 120B",
                features=["NVIDIA Integrate", "Streaming"],
                maxTokens=4096,
                supportsFunctions=True,
                supportsVision=False
            ),
            ModelConfig(
                name="MiniMax M2 (NVIDIA)",
                provider="openai",
                model="minimaxai/minimax-m2",
                apiBase="https://integrate.api.nvidia.com/v1",
                apiKey="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",
                description="NVIDIA Integrate API - MiniMax M2",
                features=["NVIDIA Integrate", "Streaming"],
                maxTokens=8192,
                supportsFunctions=True,
                supportsVision=False
            ),
        ]
    
    def get_all_models(self) -> List[ModelConfig]:
        """Get all available models"""
        return self.models
    
    def get_model_by_name(self, name: str) -> Optional[ModelConfig]:
        """Get a specific model by name"""
        for model in self.models:
            if model.name == name:
                return model
        return None
    
    def get_model_names(self) -> List[str]:
        """Get list of all model names"""
        return [model.name for model in self.models]
    
    def add_model(self, model: ModelConfig):
        """Add a new model configuration"""
        self.models.append(model)
        self._save_config()
    
    def remove_model(self, name: str) -> bool:
        """Remove a model by name"""
        for i, model in enumerate(self.models):
            if model.name == name:
                self.models.pop(i)
                self._save_config()
                return True
        return False
    
    def _save_config(self):
        """Save current models to configuration file"""
        config = {
            "version": "1.0.0",
            "models": [model.dict() for model in self.models]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    def refresh_auto_detected_models(self):
        """Update model fields for models with autoDetect=True"""
        for model_cfg in self.models:
            if model_cfg.autoDetect:
                detected = self.discover_model_name(model_cfg.apiBase, model_cfg.apiKey)
                if detected and detected != model_cfg.model:
                    logger.info(f"Auto-detected model '{detected}' for '{model_cfg.name}' (was '{model_cfg.model}')")
                    model_cfg.model = detected
                    self._save_config()

    @staticmethod
    def discover_model_name(api_base: str, api_key: str = "not-needed") -> Optional[str]:
        """Query /v1/models to find the actual model ID"""
        if httpx is None:
            logger.warning("httpx not installed, cannot auto-detect model")
            return None
        try:
            url = api_base.rstrip('/')
            if not url.endswith('/v1'):
                url = f"{url}/v1"
            url = f"{url}/models"
            
            headers = {"accept": "application/json"}
            if api_key and api_key != "not-needed":
                headers["Authorization"] = f"Bearer {api_key}"
                
            # Use verify=False if needed for internal certs
            with httpx.Client(timeout=10, verify=False) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models_data = data.get('data', [])
                    if models_data:
                        # Return the first model ID found
                        return models_data[0].get('id')
        except Exception as e:
            logger.warning(f"Failed to discover model at {api_base}: {e}")
        return None


# Global instance
_models_manager: Optional[ModelsConfigManager] = None


def get_models_manager() -> ModelsConfigManager:
    """Get the global models configuration manager"""
    global _models_manager
    if _models_manager is None:
        _models_manager = ModelsConfigManager()
    return _models_manager


def reload_models_config():
    """Reload models configuration from file"""
    global _models_manager
    _models_manager = ModelsConfigManager()
