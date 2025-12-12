"""
Pydantic schemas for the Generative UI Service API.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ============================================================================
# Enums
# ============================================================================

class GenerationStatus(str, Enum):
    """Status of a UI generation."""
    PENDING = "pending"
    PARSING = "parsing"
    PLANNING = "planning"
    GENERATING = "generating"
    POST_PROCESSING = "post_processing"
    EVALUATING = "evaluating"
    COMPLETE = "complete"
    FAILED = "failed"


class FeedbackType(str, Enum):
    """Types of feedback on generations."""
    QUALITY = "quality"
    ACCURACY = "accuracy"
    USEFULNESS = "usefulness"
    SPEED = "speed"


class ThemeMode(str, Enum):
    """UI theme modes."""
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


class ExpertiseLevel(str, Enum):
    """User expertise levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ChartType(str, Enum):
    """Preferred chart types."""
    CANDLESTICK = "candlestick"
    LINE = "line"
    BAR = "bar"


class ComponentState(str, Enum):
    """FSM states for UI components."""
    LOADING = "loading"
    READY = "ready"
    UPDATING = "updating"
    FILTERING = "filtering"
    EXPANDED = "expanded"
    COLLAPSED = "collapsed"
    HOVERING = "hovering"
    ZOOMING = "zooming"
    ROTATING = "rotating"
    DRAGGING = "dragging"
    VALIDATING = "validating"
    CONFIRMED = "confirmed"
    STREAMING = "streaming"
    PAUSED = "paused"
    ERROR = "error"


# ============================================================================
# Position & Context Models
# ============================================================================

class PositionContext(BaseModel):
    """User position for context."""
    symbol: str
    strike: Optional[float] = None
    expiration: Optional[str] = None
    option_type: Optional[str] = None  # "call" or "put"
    quantity: int = 0
    avg_cost: Optional[float] = None


class GenerationContext(BaseModel):
    """Additional context for UI generation."""
    symbol: Optional[str] = None
    current_price: Optional[float] = None
    positions: Optional[List[PositionContext]] = None
    watchlist: Optional[List[str]] = None
    market_status: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class UserPreferences(BaseModel):
    """User UI preferences for generation."""
    theme: ThemeMode = ThemeMode.DARK
    chart_type: ChartType = ChartType.CANDLESTICK
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    favorite_components: Optional[List[str]] = None
    custom_color_scheme: Optional[Dict[str, str]] = None
    accessibility_settings: Optional[Dict[str, bool]] = None


# ============================================================================
# Requirement Specification Models
# ============================================================================

class RequirementSpec(BaseModel):
    """Structured requirements parsed from natural language query."""
    intent: str = Field(..., description="Primary intent of the query")
    target_data: List[str] = Field(default_factory=list, description="Required data types")
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    visualizations: List[str] = Field(default_factory=list, description="Required visualization types")
    interactions: List[str] = Field(default_factory=list, description="Required interactions")
    time_range: Optional[str] = None
    expiration: Optional[str] = None
    educational: bool = False
    comparison: bool = False


# ============================================================================
# FSM (Finite State Machine) Models
# ============================================================================

class StateTransition(BaseModel):
    """A single state transition in the FSM."""
    from_state: ComponentState
    event: str
    to_state: ComponentState
    condition: Optional[str] = None


class ComponentFSM(BaseModel):
    """Finite State Machine for a UI component."""
    component_name: str
    states: List[ComponentState]
    events: List[str]
    transitions: List[StateTransition]
    initial_state: ComponentState = ComponentState.LOADING


class InteractionGraph(BaseModel):
    """Graph of component interactions."""
    nodes: List[str]  # View/component names
    edges: List[Dict[str, str]]  # {from, to, event}


# ============================================================================
# API Request/Response Models
# ============================================================================

class GenerateUIRequest(BaseModel):
    """Request to generate a new UI."""
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language query")
    context: Optional[GenerationContext] = None
    preferences: Optional[UserPreferences] = None
    stream: bool = Field(default=True, description="Enable streaming response")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v


class RefineUIRequest(BaseModel):
    """Request to refine an existing generated UI."""
    generation_id: str = Field(..., description="ID of generation to refine")
    refinement: str = Field(..., min_length=1, max_length=1000, description="Refinement instructions")

    @field_validator('refinement')
    @classmethod
    def validate_refinement(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Refinement cannot be empty")
        return v


class QueryParsed(BaseModel):
    """Parsed query information in metadata."""
    intent: str
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None


class GenerationMetadata(BaseModel):
    """Metadata about a UI generation."""
    query_parsed: Optional[QueryParsed] = None
    components_used: List[str] = Field(default_factory=list)
    data_subscriptions: List[str] = Field(default_factory=list)
    evaluation_score: Optional[float] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    token_count: Optional[int] = None
    iteration_count: int = 1
    refinement_applied: Optional[str] = None
    changes_made: Optional[List[str]] = None


class GenerateUIResponse(BaseModel):
    """Response from UI generation."""
    generation_id: str
    status: GenerationStatus
    html: Optional[str] = None
    metadata: GenerationMetadata
    created_at: datetime
    generation_time_ms: int


class GenerationSummary(BaseModel):
    """Summary of a generation for history listing."""
    generation_id: str
    query: str
    status: GenerationStatus
    is_favorite: bool = False
    thumbnail_url: Optional[str] = None
    created_at: datetime


class GenerationHistoryResponse(BaseModel):
    """Response for generation history."""
    items: List[GenerationSummary]
    total: int
    limit: int
    offset: int


class GenerationDetailResponse(BaseModel):
    """Detailed response for a single generation."""
    generation_id: str
    query: str
    status: GenerationStatus
    html: Optional[str] = None
    metadata: GenerationMetadata
    is_favorite: bool = False
    parent_generation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FavoriteRequest(BaseModel):
    """Request to toggle favorite status."""
    is_favorite: bool


class FavoriteResponse(BaseModel):
    """Response from favorite toggle."""
    generation_id: str
    is_favorite: bool


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a generation."""
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback_type: FeedbackType
    feedback_text: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response from feedback submission."""
    feedback_id: str
    generation_id: str
    rating: int
    feedback_type: FeedbackType
    created_at: datetime


# ============================================================================
# Component Models
# ============================================================================

class ComponentInfo(BaseModel):
    """Information about a pre-built component."""
    name: str
    description: str
    props: List[str]
    preview_url: Optional[str] = None
    fsm_states: List[str]
    category: Optional[str] = None


class ComponentListResponse(BaseModel):
    """Response listing available components."""
    components: List[ComponentInfo]


# ============================================================================
# User Preferences Models
# ============================================================================

class UserPreferencesResponse(BaseModel):
    """Response with user's GenUI preferences."""
    default_theme: ThemeMode = ThemeMode.DARK
    preferred_chart_type: ChartType = ChartType.CANDLESTICK
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    favorite_components: List[str] = Field(default_factory=list)
    custom_color_scheme: Optional[Dict[str, str]] = None
    accessibility_settings: Optional[Dict[str, bool]] = None


class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences."""
    default_theme: Optional[ThemeMode] = None
    preferred_chart_type: Optional[ChartType] = None
    expertise_level: Optional[ExpertiseLevel] = None
    favorite_components: Optional[List[str]] = None
    custom_color_scheme: Optional[Dict[str, str]] = None
    accessibility_settings: Optional[Dict[str, bool]] = None


# ============================================================================
# Streaming Event Models
# ============================================================================

class StreamEvent(BaseModel):
    """Event in the generation stream."""
    event: str
    generation_id: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None
    html: Optional[str] = None
    metadata: Optional[GenerationMetadata] = None
    error: Optional[str] = None


# ============================================================================
# WebSocket Models
# ============================================================================

class WSConnectionResponse(BaseModel):
    """WebSocket connection response."""
    type: str = "connected"
    generation_id: str
    subscriptions: List[str]


class WSDataUpdate(BaseModel):
    """WebSocket data update message."""
    type: str = "data_update"
    channel: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSSubscribeCommand(BaseModel):
    """WebSocket subscribe command."""
    action: str = "subscribe"
    channel: str


class WSUnsubscribeCommand(BaseModel):
    """WebSocket unsubscribe command."""
    action: str = "unsubscribe"
    channel: str


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    error: str = "validation_error"
    message: str = "Request body validation failed"
    details: List[Dict[str, Any]]
