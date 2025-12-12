"""
FastAPI router for GenUI API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import json

from ..models.schemas import (
    GenerateUIRequest,
    GenerateUIResponse,
    RefineUIRequest,
    GenerationStatus,
    GenerationMetadata,
    GenerationSummary,
    GenerationHistoryResponse,
    GenerationDetailResponse,
    FavoriteRequest,
    FavoriteResponse,
    FeedbackRequest,
    FeedbackResponse,
    ComponentListResponse,
    UserPreferencesResponse,
    UpdatePreferencesRequest,
    StreamEvent,
    ErrorResponse,
)
from ..core.engine import GenUIEngine, get_genui_engine
from ..components.registry import ComponentRegistry, component_registry
from ..config import settings


router = APIRouter(prefix="/api/v1/genui", tags=["genui"])

# In-memory storage for demo (replace with database in production)
_generations = {}
_favorites = set()
_feedback = []
_user_preferences = {}


# ============================================================================
# Dependency Injection
# ============================================================================

def get_engine() -> GenUIEngine:
    """Get the GenUI engine instance."""
    return get_genui_engine()


def get_registry() -> ComponentRegistry:
    """Get the component registry instance."""
    return component_registry


def get_current_user_id() -> str:
    """Get current user ID (mock for demo)."""
    # In production, extract from JWT token
    return "user_demo_123"


# ============================================================================
# Generation Endpoints
# ============================================================================

@router.post("/generate", response_model=GenerateUIResponse)
async def generate_ui(
    request: GenerateUIRequest,
    background_tasks: BackgroundTasks,
    engine: GenUIEngine = Depends(get_engine),
    user_id: str = Depends(get_current_user_id),
):
    """
    Generate a custom UI from natural language query.

    Rate Limit: 20 requests/minute per user
    """
    try:
        # Generate UI
        result = await engine.generate(
            query=request.query,
            user_id=user_id,
            context=request.context,
            preferences=request.preferences,
        )

        # Store generation
        _generations[result.generation_id] = {
            "generation_id": result.generation_id,
            "user_id": user_id,
            "query": request.query,
            "status": result.status.value,
            "html": result.html,
            "metadata": result.metadata.model_dump() if result.metadata else {},
            "created_at": result.created_at.isoformat(),
            "generation_time_ms": result.generation_time_ms,
            "is_favorite": False,
        }

        return GenerateUIResponse(
            generation_id=result.generation_id,
            status=result.status,
            html=result.html,
            metadata=result.metadata,
            created_at=result.created_at,
            generation_time_ms=result.generation_time_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/stream")
async def generate_ui_stream(
    request: GenerateUIRequest,
    engine: GenUIEngine = Depends(get_engine),
    user_id: str = Depends(get_current_user_id),
):
    """
    Stream UI generation progress with Server-Sent Events.
    """
    async def event_generator():
        async for event in engine.generate_stream(
            query=request.query,
            user_id=user_id,
            context=request.context,
            preferences=request.preferences,
        ):
            # Store generation on complete
            if event.event == "complete" and event.generation_id:
                _generations[event.generation_id] = {
                    "generation_id": event.generation_id,
                    "user_id": user_id,
                    "query": request.query,
                    "status": "complete",
                    "html": event.html,
                    "metadata": event.metadata.model_dump() if event.metadata else {},
                    "created_at": datetime.utcnow().isoformat(),
                    "generation_time_ms": 0,
                    "is_favorite": False,
                }

            yield f"data: {event.model_dump_json()}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/refine", response_model=GenerateUIResponse)
async def refine_ui(
    request: RefineUIRequest,
    engine: GenUIEngine = Depends(get_engine),
    user_id: str = Depends(get_current_user_id),
):
    """
    Refine an existing generated UI with additional instructions.
    """
    # Get original generation
    original = _generations.get(request.generation_id)
    if not original:
        raise HTTPException(status_code=404, detail="Generation not found")

    if original["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to refine this generation")

    try:
        result = await engine.refine(
            generation_id=request.generation_id,
            original_html=original["html"],
            original_metadata=original["metadata"],
            refinement=request.refinement,
            user_id=user_id,
        )

        # Store new generation
        _generations[result.generation_id] = {
            "generation_id": result.generation_id,
            "user_id": user_id,
            "query": original["query"],
            "status": result.status.value,
            "html": result.html,
            "metadata": result.metadata.model_dump() if result.metadata else {},
            "created_at": result.created_at.isoformat(),
            "generation_time_ms": result.generation_time_ms,
            "is_favorite": False,
            "parent_generation_id": request.generation_id,
        }

        return GenerateUIResponse(
            generation_id=result.generation_id,
            status=result.status,
            html=result.html,
            metadata=result.metadata,
            created_at=result.created_at,
            generation_time_ms=result.generation_time_ms,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# History Endpoints
# ============================================================================

@router.get("/history", response_model=GenerationHistoryResponse)
async def get_generation_history(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    favorites_only: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get user's generation history.
    """
    # Filter generations for user
    user_generations = [
        g for g in _generations.values()
        if g["user_id"] == user_id
    ]

    # Apply filters
    if favorites_only:
        user_generations = [g for g in user_generations if g.get("is_favorite")]

    if search:
        search_lower = search.lower()
        user_generations = [
            g for g in user_generations
            if search_lower in g["query"].lower()
        ]

    # Sort by created_at descending
    user_generations.sort(key=lambda x: x["created_at"], reverse=True)

    # Paginate
    total = len(user_generations)
    items = user_generations[offset:offset + limit]

    return GenerationHistoryResponse(
        items=[
            GenerationSummary(
                generation_id=g["generation_id"],
                query=g["query"],
                status=GenerationStatus(g["status"]),
                is_favorite=g.get("is_favorite", False),
                thumbnail_url=None,
                created_at=datetime.fromisoformat(g["created_at"]),
            )
            for g in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/generations/{generation_id}", response_model=GenerationDetailResponse)
async def get_generation_detail(
    generation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Get detailed information about a specific generation.
    """
    generation = _generations.get(generation_id)
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this generation")

    return GenerationDetailResponse(
        generation_id=generation["generation_id"],
        query=generation["query"],
        status=GenerationStatus(generation["status"]),
        html=generation["html"],
        metadata=GenerationMetadata(**generation["metadata"]),
        is_favorite=generation.get("is_favorite", False),
        parent_generation_id=generation.get("parent_generation_id"),
        created_at=datetime.fromisoformat(generation["created_at"]),
        updated_at=datetime.fromisoformat(generation["created_at"]),
    )


@router.delete("/generations/{generation_id}", status_code=204)
async def delete_generation(
    generation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """
    Delete a generation from history.
    """
    generation = _generations.get(generation_id)
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this generation")

    del _generations[generation_id]
    return None


# ============================================================================
# Favorites Endpoints
# ============================================================================

@router.post("/generations/{generation_id}/favorite", response_model=FavoriteResponse)
async def toggle_favorite(
    generation_id: str,
    request: FavoriteRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Toggle favorite status for a generation.
    """
    generation = _generations.get(generation_id)
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if generation["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this generation")

    generation["is_favorite"] = request.is_favorite

    return FavoriteResponse(
        generation_id=generation_id,
        is_favorite=request.is_favorite,
    )


# ============================================================================
# Feedback Endpoints
# ============================================================================

@router.post("/generations/{generation_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    generation_id: str,
    request: FeedbackRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Submit feedback on a generation for model improvement.
    """
    generation = _generations.get(generation_id)
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    feedback_id = str(uuid.uuid4())
    feedback_entry = {
        "feedback_id": feedback_id,
        "generation_id": generation_id,
        "user_id": user_id,
        "rating": request.rating,
        "feedback_type": request.feedback_type.value,
        "feedback_text": request.feedback_text,
        "created_at": datetime.utcnow().isoformat(),
    }
    _feedback.append(feedback_entry)

    return FeedbackResponse(
        feedback_id=feedback_id,
        generation_id=generation_id,
        rating=request.rating,
        feedback_type=request.feedback_type,
        created_at=datetime.fromisoformat(feedback_entry["created_at"]),
    )


# ============================================================================
# Components Endpoints
# ============================================================================

@router.get("/components", response_model=ComponentListResponse)
async def list_components(
    registry: ComponentRegistry = Depends(get_registry),
):
    """
    List available pre-built components.
    """
    return ComponentListResponse(
        components=registry.list_components()
    )


@router.get("/components/{component_name}")
async def get_component(
    component_name: str,
    registry: ComponentRegistry = Depends(get_registry),
):
    """
    Get details about a specific component.
    """
    component = registry.get_component(component_name)
    if not component:
        raise HTTPException(status_code=404, detail=f"Component not found: {component_name}")

    return component


@router.get("/components/{component_name}/template")
async def get_component_template(
    component_name: str,
    registry: ComponentRegistry = Depends(get_registry),
):
    """
    Get the HTML template for a component.
    """
    template = registry.get_component_template(component_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {component_name}")

    return {"component_name": component_name, "template": template}


# ============================================================================
# Preferences Endpoints
# ============================================================================

@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
):
    """
    Get user's GenUI preferences.
    """
    prefs = _user_preferences.get(user_id, {})
    return UserPreferencesResponse(
        default_theme=prefs.get("default_theme", "dark"),
        preferred_chart_type=prefs.get("preferred_chart_type", "candlestick"),
        expertise_level=prefs.get("expertise_level", "intermediate"),
        favorite_components=prefs.get("favorite_components", []),
        custom_color_scheme=prefs.get("custom_color_scheme"),
        accessibility_settings=prefs.get("accessibility_settings"),
    )


@router.patch("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Update user's GenUI preferences.
    """
    if user_id not in _user_preferences:
        _user_preferences[user_id] = {}

    prefs = _user_preferences[user_id]

    if request.default_theme is not None:
        prefs["default_theme"] = request.default_theme.value
    if request.preferred_chart_type is not None:
        prefs["preferred_chart_type"] = request.preferred_chart_type.value
    if request.expertise_level is not None:
        prefs["expertise_level"] = request.expertise_level.value
    if request.favorite_components is not None:
        prefs["favorite_components"] = request.favorite_components
    if request.custom_color_scheme is not None:
        prefs["custom_color_scheme"] = request.custom_color_scheme
    if request.accessibility_settings is not None:
        prefs["accessibility_settings"] = request.accessibility_settings

    return await get_preferences(user_id)


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "genui",
        "version": settings.app_version,
        "generations_count": len(_generations),
    }
