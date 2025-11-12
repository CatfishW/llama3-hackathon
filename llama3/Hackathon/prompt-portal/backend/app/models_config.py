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
        except Exception as e:
            print(f"Warning: Failed to load models config: {e}")
            self.models = self._get_default_models()
    
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
                name="TangLLM",
                provider="openai",
                model="Qwen-VL-32B",
                apiBase="http://173.61.35.162:25565/v1",
                apiKey="sk-local-abc",
                description="Local Qwen Vision-Language Model - 32B parameters with vision capabilities",
                features=["Fast Response", "Vision Support", "Function Calling", "Local Hosting"],
                maxTokens=32768,
                supportsFunctions=True,
                supportsVision=True
            ),
            ModelConfig(
                name="MiniMax M2",
                provider="openai",
                model="minimax/minimax-m2:free",
                apiBase="https://openrouter.ai/api/v1",
                apiKey="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",
                description="MiniMax M2 - Free tier via OpenRouter with strong performance",
                features=["Free Tier", "Fast Response", "Function Calling", "Cloud-based"],
                maxTokens=8192,
                supportsFunctions=True,
                supportsVision=False
            ),
            ModelConfig(
                name="Qwen3 Coder",
                provider="openai",
                model="qwen/qwen3-coder:free",
                apiBase="https://openrouter.ai/api/v1",
                apiKey="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",
                description="Qwen3 Coder - Specialized for code generation and understanding (Free)",
                features=["Code Generation", "Free Tier", "Fast Response", "Function Calling"],
                maxTokens=8192,
                supportsFunctions=True,
                supportsVision=False
            ),
            ModelConfig(
                name="Kat Coder Pro",
                provider="openai",
                model="kwaipilot/kat-coder-pro:free",
                apiBase="https://openrouter.ai/api/v1",
                apiKey="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",
                description="Kat Coder Pro - Advanced coding assistant by Kuaishou (Free)",
                features=["Advanced Coding", "Free Tier", "Fast Response", "Function Calling"],
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
