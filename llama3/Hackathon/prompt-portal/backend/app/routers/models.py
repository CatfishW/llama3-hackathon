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
import httpx

from ..deps import get_current_user, get_db
from ..models_config import get_models_manager, ModelConfig
from ..models import User
from ..services.llm_client import detect_model_from_url

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
    model_config = {"protected_namespaces": ()}
    model_name: str = Field(..., description="Name of the model to select")


class ModelSelectionResponse(BaseModel):
    """Response after selecting a model"""
    success: bool
    selected_model: str
    message: str


class ModelCreateRequest(BaseModel):
    """Request to create/add a custom model"""
    model_config = {"protected_namespaces": ()}
    name: str = Field(..., description="Display name for the model")
    provider: str = Field(..., description="Provider (e.g., openai, anthropic)")
    model: Optional[str] = Field(None, description="Model identifier for API calls (optional, auto-detected from URL if empty)")
    apiBase: str = Field(..., description="API base URL")
    apiKey: str = Field(..., description="API key for authentication")
    description: Optional[str] = Field(None, description="Model description")
    features: Optional[List[str]] = Field(default_factory=list, description="Model features")
    maxTokens: Optional[int] = Field(None, description="Maximum tokens")
    supportsFunctions: Optional[bool] = Field(True, description="Supports function calling")
    supportsVision: Optional[bool] = Field(False, description="Supports vision/images")


class ModelUpdateRequest(BaseModel):
    """Request to update a model's configuration"""
    model_config = {"protected_namespaces": ()}
    apiBase: Optional[str] = Field(None, description="API base URL")
    apiKey: Optional[str] = Field(None, description="API key")
    description: Optional[str] = Field(None, description="Model description")
    features: Optional[List[str]] = Field(None, description="Model features")
    maxTokens: Optional[int] = Field(None, description="Maximum tokens")
    supportsFunctions: Optional[bool] = Field(None, description="Supports function calling")
    supportsVision: Optional[bool] = Field(None, description="Supports vision/images")


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
        
        selected_model_name = db_user.selected_model or "AGAII Cloud LLM"
        
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
    Get full configuration for a specific model including API keys.
    Users can see the full config of any model to edit it.
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


@router.post("/add", response_model=ModelOut)
async def add_custom_model(
    request: ModelCreateRequest,
    user = Depends(get_current_user)
):
    """
    Add a custom model configuration.
    Users can add their own models with custom API endpoints and keys.
    """
    try:
        models_manager = get_models_manager()
        
        # Check if model with same name already exists
        existing = models_manager.get_model_by_name(request.name)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.name}' already exists. Use update endpoint to modify it."
            )
        
        # Auto-detect model if not provided
        if not request.model:
            detected_model = detect_model_from_url(request.apiBase, request.apiKey)
            if detected_model:
                request.model = detected_model
                logger.info(f"Auto-detected model '{detected_model}' for custom model '{request.name}'")
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Could not auto-detect model from URL. Please specify model name manually."
                )

        # Set default maxTokens to 4096 if not specified
        max_tokens = request.maxTokens if request.maxTokens is not None else 4096

        # Create new model configuration
        new_model = ModelConfig(
            name=request.name,
            provider=request.provider,
            model=request.model,
            apiBase=request.apiBase,
            apiKey=request.apiKey,
            description=request.description,
            features=request.features or [],
            maxTokens=max_tokens,
            supportsFunctions=request.supportsFunctions,
            supportsVision=request.supportsVision
        )
        
        # Add to models manager
        models_manager.add_model(new_model)
        
        logger.info(f"User {user.email} added custom model: {request.name}")
        
        # Return model info (without API key)
        return ModelOut(
            name=new_model.name,
            provider=new_model.provider,
            model=new_model.model,
            description=new_model.description,
            features=new_model.features or [],
            maxTokens=new_model.maxTokens,
            supportsFunctions=new_model.supportsFunctions,
            supportsVision=new_model.supportsVision
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add custom model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add model: {str(e)}")


@router.put("/update/{model_name}", response_model=ModelOut)
async def update_model(
    model_name: str,
    request: ModelUpdateRequest,
    user = Depends(get_current_user)
):
    """
    Update a model's configuration (API URL, key, description, etc.).
    Users can update any model's settings.
    """
    try:
        models_manager = get_models_manager()
        
        # Get existing model
        model = models_manager.get_model_by_name(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        
        # Update fields if provided
        if request.apiBase is not None:
            model.apiBase = request.apiBase
        if request.apiKey is not None:
            model.apiKey = request.apiKey
        if request.description is not None:
            model.description = request.description
        if request.features is not None:
            model.features = request.features
        if request.maxTokens is not None:
            model.maxTokens = request.maxTokens
        if request.supportsFunctions is not None:
            model.supportsFunctions = request.supportsFunctions
        if request.supportsVision is not None:
            model.supportsVision = request.supportsVision
        
        # Save configuration
        models_manager._save_config()
        
        logger.info(f"User {user.email} updated model: {model_name}")
        
        # Return updated model info (without API key)
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
        logger.error(f"Failed to update model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update model: {str(e)}")


@router.delete("/delete/{model_name}")
async def delete_model(
    model_name: str,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a custom model configuration.
    Users can delete models they added.
    """
    try:
        models_manager = get_models_manager()
        
        # Check if model exists
        model = models_manager.get_model_by_name(model_name)
        if not model:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        
        # Remove the model
        success = models_manager.remove_model(model_name)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to remove model")
        
        # If any users had this as their selected model, reset to first available
        users_with_deleted_model = db.query(User).filter(User.selected_model == model_name).all()
        if users_with_deleted_model:
            remaining_models = models_manager.get_all_models()
            default_model = remaining_models[0].name if remaining_models else "AGAII Cloud LLM"
            
            for user_record in users_with_deleted_model:
                user_record.selected_model = default_model
            
            db.commit()
        
        logger.info(f"User {user.email} deleted model: {model_name}")
        
        return {
            "success": True,
            "message": f"Model '{model_name}' deleted successfully",
            "affected_users": len(users_with_deleted_model)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


class ModelTestRequest(BaseModel):
    """Request to test model connectivity"""
    model_config = {"protected_namespaces": ()}
    api_base: str = Field(..., description="API base URL to test")
    api_key: str = Field(..., description="API key for authentication")
    model: Optional[str] = Field(None, description="Model identifier to test (optional)")


class ModelTestResponse(BaseModel):
    """Response from model connectivity test"""
    success: bool
    message: str
    model_name: Optional[str] = None
    response_time_ms: Optional[int] = None


class ModelStatusOut(BaseModel):
    """Model with status information"""
    name: str
    provider: str
    model: str
    description: Optional[str] = None
    features: List[str] = []
    maxTokens: Optional[int] = None
    supportsFunctions: bool = True
    supportsVision: bool = False
    is_active: bool
    status_message: str
    response_time_ms: Optional[int] = None


@router.post("/test", response_model=ModelTestResponse)
async def test_model_connectivity(
    request: ModelTestRequest,
    user = Depends(get_current_user)
):
    """
    Test connectivity to an LLM API endpoint.
    
    This endpoint allows users to verify their API configuration
    before saving a model.
    """
    import time
    
    try:
        base_input = request.api_base.rstrip('/')
        base_candidates = []
        if base_input.endswith('/v1'):
            base_candidates = [base_input, base_input[:-3]]
        else:
            base_candidates = [base_input, f"{base_input}/v1"]

        model_urls = []
        seen_urls = set()
        for base in base_candidates:
            if not base:
                continue
            url = f"{base}/models"
            if url not in seen_urls:
                model_urls.append(url)
                seen_urls.add(url)

        headers = {"accept": "application/json"}
        if request.api_key and request.api_key not in ["not-needed", "none", ""]:
            headers["Authorization"] = f"Bearer {request.api_key}"

        start_time = time.time()
        data = None
        last_error: Optional[str] = None

        async with httpx.AsyncClient(timeout=10) as client:
            for models_url in model_urls:
                try:
                    response = await client.get(models_url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    break
                except httpx.TimeoutException:
                    last_error = "Connection timed out after 10 seconds"
                except httpx.HTTPStatusError as e:
                    last_error = f"HTTP error {e.response.status_code}: {e.response.text[:200]}"
                except Exception as e:
                    last_error = f"Connection failed: {str(e)}"

            if data is None and request.model:
                base_url = base_input if base_input.endswith('/v1') else f"{base_input}/v1"
                chat_url = f"{base_url}/chat/completions"
                payload = {
                    "model": request.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                    "temperature": 0
                }
                try:
                    response = await client.post(
                        chat_url,
                        headers={**headers, "content-type": "application/json"},
                        json=payload
                    )
                    response.raise_for_status()
                    response_time = int((time.time() - start_time) * 1000)
                    return ModelTestResponse(
                        success=True,
                        message="Successfully connected to LLM API",
                        model_name=request.model,
                        response_time_ms=response_time
                    )
                except httpx.TimeoutException:
                    last_error = "Connection timed out after 10 seconds"
                except httpx.HTTPStatusError as e:
                    last_error = f"HTTP error {e.response.status_code}: {e.response.text[:200]}"
                except Exception as e:
                    last_error = f"Connection failed: {str(e)}"

        if data is None:
            return ModelTestResponse(
                success=False,
                message=last_error or "Connection failed: No response from server"
            )

        response_time = int((time.time() - start_time) * 1000)

        model_name = None
        if isinstance(data, dict):
            if isinstance(data.get("data"), list) and data["data"]:
                model_name = data["data"][0].get("id")
            elif isinstance(data.get("models"), list) and data["models"]:
                model_name = data["models"][0].get("id") or data["models"][0].get("name")

        return ModelTestResponse(
            success=True,
            message="Successfully connected to LLM API",
            model_name=model_name,
            response_time_ms=response_time
        )
    except Exception as e:
        logger.error(f"Model connectivity test failed: {e}")
        return ModelTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.get("/status", response_model=List[ModelStatusOut])
async def get_models_status(
    user = Depends(get_current_user)
):
    """
    Get all available models with their current connectivity status.
    
    This endpoint checks each model's API endpoint and returns
    whether it's active or not.
    """
    import time
    import asyncio
    
    models_manager = get_models_manager()
    models = models_manager.get_all_models()
    
    async def check_model_status(model: ModelConfig) -> ModelStatusOut:
        """Check a single model's connectivity status"""
        try:
            # Normalize the URL
            base_url = model.apiBase.rstrip('/')
            if not base_url.endswith('/v1'):
                base_url = f"{base_url}/v1"
            models_url = f"{base_url}/models"
            
            headers = {"accept": "application/json"}
            if model.apiKey and model.apiKey not in ["not-needed", "none", ""]:
                headers["Authorization"] = f"Bearer {model.apiKey}"
            
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(models_url, headers=headers)
                response.raise_for_status()
            
            response_time = int((time.time() - start_time) * 1000)
            
            return ModelStatusOut(
                name=model.name,
                provider=model.provider,
                model=model.model,
                description=model.description,
                features=model.features or [],
                maxTokens=model.maxTokens,
                supportsFunctions=model.supportsFunctions,
                supportsVision=model.supportsVision,
                is_active=True,
                status_message="Active and responding",
                response_time_ms=response_time
            )
            
        except httpx.TimeoutException:
            return ModelStatusOut(
                name=model.name,
                provider=model.provider,
                model=model.model,
                description=model.description,
                features=model.features or [],
                maxTokens=model.maxTokens,
                supportsFunctions=model.supportsFunctions,
                supportsVision=model.supportsVision,
                is_active=False,
                status_message="Connection timed out"
            )
        except httpx.HTTPStatusError as e:
            return ModelStatusOut(
                name=model.name,
                provider=model.provider,
                model=model.model,
                description=model.description,
                features=model.features or [],
                maxTokens=model.maxTokens,
                supportsFunctions=model.supportsFunctions,
                supportsVision=model.supportsVision,
                is_active=False,
                status_message=f"HTTP {e.response.status_code}"
            )
        except Exception as e:
            return ModelStatusOut(
                name=model.name,
                provider=model.provider,
                model=model.model,
                description=model.description,
                features=model.features or [],
                maxTokens=model.maxTokens,
                supportsFunctions=model.supportsFunctions,
                supportsVision=model.supportsVision,
                is_active=False,
                status_message=f"Error: {str(e)[:50]}"
            )
    
    # Check all models concurrently
    results = await asyncio.gather(*[check_model_status(m) for m in models])
    return list(results)
