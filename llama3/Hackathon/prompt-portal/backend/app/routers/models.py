"""
Models API Router

Provides endpoints for managing and selecting LLM models.
Users can view available models and select their preferred model.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from ..deps import get_current_user, get_db
from ..models_config import get_models_manager, ModelConfig
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelOut(BaseModel):
    """Model information for frontend display"""
    name: str
    provider: str
    model: str
    description: Optional[str] = None
    features: List[str] = []
    maxTokens: Optional[int] = None
    supportsFunctions: bool = True
    supportsVision: bool = False


class ModelSelectionRequest(BaseModel):
    """Request to select a model"""
    model_name: str = Field(..., description="Name of the model to select")


class ModelSelectionResponse(BaseModel):
    """Response after selecting a model"""
    success: bool
    selected_model: str
    message: str


@router.get("/available", response_model=List[ModelOut])
async def get_available_models(
    user = Depends(get_current_user)
):
    """
    Get list of all available models.
    
    Returns:
        List of available models with their configurations
    """
    try:
        models_manager = get_models_manager()
        models = models_manager.get_all_models()
        
        # Convert to output format (without exposing API keys)
        return [
            ModelOut(
                name=model.name,
                provider=model.provider,
                model=model.model,
                description=model.description,
                features=model.features or [],
                maxTokens=model.maxTokens,
                supportsFunctions=model.supportsFunctions,
                supportsVision=model.supportsVision
            )
            for model in models
        ]
        
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve models")


@router.get("/selected", response_model=ModelOut)
async def get_selected_model(
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the currently selected model for the authenticated user.
    
    Returns:
        Currently selected model configuration
    """
    try:
        # Get user's selected model from database
        db_user = db.query(User).filter(User.id == user.id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        selected_model_name = db_user.selected_model or "TangLLM"
        
        # Get model configuration
        models_manager = get_models_manager()
        model = models_manager.get_model_by_name(selected_model_name)
        
        if not model:
            # Fall back to first available model
            models = models_manager.get_all_models()
            if not models:
                raise HTTPException(status_code=500, detail="No models available")
            model = models[0]
            # Update user's selection
            db_user.selected_model = model.name
            db.commit()
        
        return ModelOut(
            name=model.name,
            provider=model.provider,
            model=model.model,
            description=model.description,
            features=model.features or [],
            maxTokens=model.maxTokens,
            supportsFunctions=model.supportsFunctions,
            supportsVision=model.supportsVision
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get selected model: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve selected model")


@router.put("/select", response_model=ModelSelectionResponse)
async def select_model(
    request: ModelSelectionRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Select a model for the authenticated user.
    
    Args:
        request: Model selection request with model name
        
    Returns:
        Success status and selected model name
    """
    try:
        # Verify model exists
        models_manager = get_models_manager()
        model = models_manager.get_model_by_name(request.model_name)
        
        if not model:
            available_models = ", ".join(models_manager.get_model_names())
            raise HTTPException(
                status_code=404,
                detail=f"Model '{request.model_name}' not found. Available: {available_models}"
            )
        
        # Update user's selected model
        db_user = db.query(User).filter(User.id == user.id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_user.selected_model = request.model_name
        db.commit()
        
        logger.info(f"User {user.email} selected model: {request.model_name}")
        
        return ModelSelectionResponse(
            success=True,
            selected_model=request.model_name,
            message=f"Successfully selected {request.model_name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to select model: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to select model")


@router.get("/config/{model_name}")
async def get_model_config(
    model_name: str,
    user = Depends(get_current_user)
) -> ModelConfig:
    """
    Get full configuration for a specific model (admin/debugging).
    
    Note: API keys are included, so this should be protected.
    """
    try:
        models_manager = get_models_manager()
        model = models_manager.get_model_by_name(model_name)
        
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        
        return model
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model config: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve model configuration")
