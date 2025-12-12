# Project: OPTIX

## Technical Requirements Document - Generative UI Implementation

**DSDM Atern Methodology**

Version 1.0 | December 12, 2024

---

## 1. Overview

This Technical Requirements Document details the architecture, components, and implementation specifications for adding Generative UI capabilities to the OPTIX options trading platform. The implementation is based on research from Google's "Generative UI: LLMs are Effective UI Generators" paper and the "Generative Interfaces for Language Models" framework.

### 1.1 Vertical Slice Definition

| Attribute | Value |
|-----------|-------|
| Slice ID | VS-11 |
| Name | Generative UI Engine |
| Phase | Phase 2 (M5-8) |
| Priority | Should Have |
| Status | ⏳ Pending |

### 1.2 Core Concept

Generative UI enables the platform to dynamically generate custom, interactive interfaces from natural language queries. Rather than presenting static, predefined views, the LLM generates complete HTML/CSS/JS interfaces tailored to each user's specific needs—including visualizations, interactive components, and real-time data bindings.

### 1.3 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **LLM Provider** | Gemini 2.5 Pro / Claude Opus 4.5 | Strong UI code generation, large context |
| **Backend Framework** | FastAPI (existing) | Async support, tool orchestration |
| **Frontend Rendering** | React Native WebView / Web Components | Cross-platform, sandboxed execution |
| **Component Library** | D3.js, TradingView Lightweight Charts | Financial visualization standards |
| **State Management** | Finite State Machines (FSM) | Predictable UI state transitions |
| **Caching** | Redis (existing) | Generation caching, rate limiting |
| **Database** | PostgreSQL (existing) | Generation history, user preferences |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OPTIX Mobile App                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Chat Interface                                │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                    GenUI Renderer                            │   │   │
│  │  │  (WebView / Web Components with Sandbox)                     │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Gateway (FastAPI)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Auth Service │  │ GenUI Service│  │ Market Data  │  │  Brokerage   │    │
│  │     (✅)     │  │    (NEW)     │  │  Service(✅) │  │  Service(✅) │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GenUI Generation Engine                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Requirement Specification                         │  │
│  │           (Parse query → structured requirements)                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Structured Representation                          │  │
│  │         (FSM modeling, component graph, state transitions)            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│                                      ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                       UI Code Synthesis                               │  │
│  │              (Generate HTML/CSS/JS with data bindings)                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│    LLM Provider      │  │   Tool Services      │  │  Component Library   │
│  (Gemini/Claude/GPT) │  │ (Search, Images,     │  │  (Charts, Tables,    │
│                      │  │  Market Data)        │  │   Widgets)           │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

### 2.2 Component Architecture

```
genui-service/
├── api/
│   ├── router.py              # FastAPI routes
│   ├── schemas.py             # Pydantic models
│   └── middleware.py          # Rate limiting, auth
├── core/
│   ├── engine.py              # Main generation orchestrator
│   ├── requirement_parser.py  # Query → requirements
│   ├── fsm_builder.py         # FSM state modeling
│   ├── code_synthesizer.py    # UI code generation
│   └── post_processor.py      # Output sanitization
├── llm/
│   ├── providers.py           # LLM abstraction layer
│   ├── prompts/
│   │   ├── system.py          # System instructions
│   │   ├── planning.py        # Planning prompts
│   │   └── generation.py      # Code generation prompts
│   └── tools.py               # LLM tool definitions
├── components/
│   ├── registry.py            # Component registration
│   ├── options_chain.py       # Options chain component
│   ├── greeks_display.py      # Greeks visualization
│   ├── payoff_diagram.py      # P&L charts
│   ├── volatility_surface.py  # 3D IV surface
│   └── strategy_builder.py    # Strategy constructor
├── data/
│   ├── market_data_bridge.py  # Real-time data injection
│   ├── portfolio_bridge.py    # User portfolio data
│   └── cache_manager.py       # Generation caching
├── security/
│   ├── sanitizer.py           # Code sanitization
│   ├── sandbox.py             # Execution sandbox
│   └── validator.py           # Output validation
└── models/
    ├── generation.py          # SQLAlchemy models
    └── repository.py          # Data access layer
```

---

## 3. Core Components

### 3.1 Generation Engine

The generation engine implements a three-stage pipeline based on the "Generative Interfaces for Language Models" framework:

#### Stage 1: Requirement Specification

```python
class RequirementParser:
    """
    Transforms natural language queries into structured requirements.

    Input: "Show me AAPL options chain with highlighted high OI calls"
    Output: RequirementSpec with:
        - target_data: ["options_chain", "open_interest"]
        - symbol: "AAPL"
        - filters: {"oi_threshold": "high", "option_type": "calls"}
        - visualizations: ["table", "highlight"]
        - interactions: ["sort", "filter", "click_to_expand"]
    """

    async def parse(self, query: str, context: UserContext) -> RequirementSpec:
        # Use LLM to extract structured requirements
        # Include user context (expertise level, preferences)
        pass
```

#### Stage 2: Structured Representation (FSM)

Based on the research, individual UI components are modeled as Finite State Machines:

```
ℳ = (𝒮, ℰ, δ, s₀)

Where:
- 𝒮 = Set of atomic interface states
- ℰ = User-triggered events (click, hover, input)
- δ = State transition function
- s₀ = Initial state
```

```python
class FSMBuilder:
    """
    Models UI components as finite state machines for predictable behavior.
    """

    def build_component_fsm(self, component_type: str, config: dict) -> ComponentFSM:
        """
        Example: OptionsChain component FSM

        States: {collapsed, expanded, filtering, sorting, loading}
        Events: {click_row, hover_strike, apply_filter, change_sort}
        Transitions:
            (collapsed, click_row) → expanded
            (expanded, click_row) → collapsed
            (any, apply_filter) → filtering → updated
        """
        pass

    def build_interaction_graph(self, components: List[ComponentFSM]) -> InteractionGraph:
        """
        Models high-level interaction flows as directed graph 𝒢 = (𝒱, 𝒯)
        where nodes are interface views and edges are transitions.
        """
        pass
```

#### Stage 3: UI Code Synthesis

```python
class CodeSynthesizer:
    """
    Generates executable HTML/CSS/JS from structured representation.
    Uses iterative refinement with generation-evaluation cycles.
    """

    async def synthesize(
        self,
        requirements: RequirementSpec,
        fsm: ComponentFSM,
        max_iterations: int = 5,
        target_score: float = 90.0
    ) -> GeneratedUI:
        """
        Iterative refinement process:
        1. Generate UI candidate
        2. Score using adaptive reward function
        3. If score < target and iterations < max, regenerate with feedback
        4. Return highest-scoring candidate
        """
        best_candidate = None
        best_score = 0.0

        for iteration in range(max_iterations):
            candidate = await self._generate_candidate(requirements, fsm, best_candidate)
            score = await self._evaluate_candidate(candidate, requirements)

            if score > best_score:
                best_candidate = candidate
                best_score = score

            if score >= target_score:
                break

        return best_candidate
```

### 3.2 LLM Integration

#### System Instructions Template

```python
GENUI_SYSTEM_PROMPT = """
You are a Generative UI engine for the OPTIX options trading platform.

## Objective
Generate interactive, data-driven user interfaces from natural language queries.
Output complete, self-contained HTML/CSS/JS that renders in a sandboxed WebView.

## Design System
- Primary Color: #2563EB (Blue)
- Background: #0F172A (Dark) / #FFFFFF (Light)
- Font: Inter, system-ui
- Border Radius: 8px
- Spacing: 4px base unit

## Available Components
{component_registry}

## Available Data APIs
{data_api_specs}

## Technical Requirements
1. All styles must be inline or in <style> tags
2. Use CSS Grid/Flexbox for layout
3. Include loading states for async data
4. Handle errors gracefully with user-friendly messages
5. Ensure touch-friendly interactions (min 44px targets)
6. Support dark/light mode via CSS variables

## Output Format
Return a single HTML document with embedded CSS and JavaScript.
Data placeholders use format: {{DATA:endpoint:params}}

## Examples
{few_shot_examples}
"""
```

#### Tool Definitions

```python
GENUI_TOOLS = [
    {
        "name": "get_options_chain",
        "description": "Fetch options chain for a symbol",
        "parameters": {
            "symbol": {"type": "string", "required": True},
            "expiration": {"type": "string", "required": False},
            "strike_range": {"type": "object", "required": False}
        }
    },
    {
        "name": "get_quote",
        "description": "Get real-time quote for a symbol",
        "parameters": {
            "symbol": {"type": "string", "required": True}
        }
    },
    {
        "name": "get_portfolio_positions",
        "description": "Get user's current portfolio positions",
        "parameters": {
            "group_by": {"type": "string", "enum": ["symbol", "strategy", "expiration"]}
        }
    },
    {
        "name": "get_greeks",
        "description": "Calculate Greeks for options positions",
        "parameters": {
            "positions": {"type": "array", "required": True}
        }
    },
    {
        "name": "generate_chart",
        "description": "Generate a chart visualization",
        "parameters": {
            "type": {"type": "string", "enum": ["line", "bar", "candlestick", "payoff", "surface"]},
            "data": {"type": "object", "required": True},
            "options": {"type": "object", "required": False}
        }
    },
    {
        "name": "search_web",
        "description": "Search for relevant information",
        "parameters": {
            "query": {"type": "string", "required": True}
        }
    }
]
```

### 3.3 Component Library

#### Pre-Built Component Registry

```python
class ComponentRegistry:
    """
    Registry of pre-built, optimized UI components for options trading.
    LLM can compose these components or generate custom variations.
    """

    components = {
        "OptionsChainTable": {
            "description": "Interactive options chain with calls/puts",
            "props": ["symbol", "expiration", "columns", "onStrikeSelect"],
            "template": "components/options_chain.html",
            "fsm_states": ["loading", "ready", "filtering", "expanded"]
        },
        "GreeksGauges": {
            "description": "Visual gauges for Delta, Gamma, Theta, Vega",
            "props": ["greeks", "ranges", "format"],
            "template": "components/greeks_gauges.html",
            "fsm_states": ["loading", "ready", "updating"]
        },
        "PayoffDiagram": {
            "description": "Strategy payoff P&L chart",
            "props": ["legs", "underlying_range", "current_price"],
            "template": "components/payoff_diagram.html",
            "fsm_states": ["loading", "ready", "hovering", "zooming"]
        },
        "VolatilitySurface": {
            "description": "3D implied volatility surface",
            "props": ["symbol", "expirations", "strikes"],
            "template": "components/vol_surface.html",
            "fsm_states": ["loading", "ready", "rotating", "zooming"]
        },
        "PositionCard": {
            "description": "Single position summary card",
            "props": ["position", "show_greeks", "show_pnl"],
            "template": "components/position_card.html",
            "fsm_states": ["collapsed", "expanded"]
        },
        "StrategyBuilder": {
            "description": "Drag-drop strategy leg builder",
            "props": ["symbol", "available_legs", "on_change"],
            "template": "components/strategy_builder.html",
            "fsm_states": ["idle", "dragging", "validating", "confirmed"]
        },
        "AlertConfigurator": {
            "description": "Price/condition alert setup",
            "props": ["symbol", "alert_types", "on_create"],
            "template": "components/alert_config.html",
            "fsm_states": ["idle", "configuring", "validating", "created"]
        },
        "EarningsCalendar": {
            "description": "Upcoming earnings with options IV",
            "props": ["symbols", "date_range", "show_iv"],
            "template": "components/earnings_calendar.html",
            "fsm_states": ["loading", "ready", "filtered"]
        }
    }
```

### 3.4 Post-Processing Pipeline

Based on Google's research, post-processors address common generation issues:

```python
class PostProcessor:
    """
    Pipeline of post-processors to sanitize and validate generated UI code.
    """

    processors = [
        SecuritySanitizer(),      # Remove dangerous JS patterns
        StyleNormalizer(),        # Ensure consistent styling
        AccessibilityChecker(),   # Add ARIA labels, roles
        DataBindingResolver(),    # Replace data placeholders
        ErrorBoundaryInjector(),  # Wrap components in error handling
        PerformanceOptimizer(),   # Minify, defer non-critical
        MobileResponsiveness(),   # Ensure responsive layout
    ]

    async def process(self, generated_html: str, context: GenerationContext) -> ProcessedUI:
        result = generated_html
        validation_errors = []

        for processor in self.processors:
            try:
                result = await processor.process(result, context)
            except ProcessingError as e:
                validation_errors.append(e)

        return ProcessedUI(
            html=result,
            is_valid=len(validation_errors) == 0,
            errors=validation_errors
        )
```

#### Security Sanitizer

```python
class SecuritySanitizer:
    """
    Ensures generated code is safe for sandboxed execution.
    """

    BLOCKED_PATTERNS = [
        r'eval\s*\(',
        r'Function\s*\(',
        r'document\.write',
        r'innerHTML\s*=',  # Use textContent or sanitized assignment
        r'window\.location',
        r'document\.cookie',
        r'localStorage\.',
        r'sessionStorage\.',
        r'fetch\s*\(',  # Must use bridged API
        r'XMLHttpRequest',
        r'<script\s+src=',  # No external scripts
        r'on\w+\s*=\s*["\']',  # No inline event handlers (use addEventListener)
    ]

    REQUIRED_CSP = {
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline'",  # Inline for generated code
        "style-src": "'self' 'unsafe-inline'",
        "img-src": "'self' data: https:",
        "connect-src": "'self'",  # Bridged API only
    }

    async def process(self, html: str, context: GenerationContext) -> str:
        # Check for blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, html, re.IGNORECASE):
                html = re.sub(pattern, '/* BLOCKED */', html, flags=re.IGNORECASE)

        # Inject CSP meta tag
        csp_content = "; ".join(f"{k} {v}" for k, v in self.REQUIRED_CSP.items())
        csp_tag = f'<meta http-equiv="Content-Security-Policy" content="{csp_content}">'
        html = html.replace('<head>', f'<head>\n{csp_tag}')

        return html
```

---

## 4. API Specifications

### 4.1 GenUI Service Endpoints

```python
# genui_service/api/router.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

router = APIRouter(prefix="/api/v1/genui", tags=["genui"])


class GenerationStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    POST_PROCESSING = "post_processing"
    COMPLETE = "complete"
    FAILED = "failed"


class GenerateUIRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    context: Optional[dict] = Field(default=None, description="Additional context (symbol, positions)")
    preferences: Optional[dict] = Field(default=None, description="User UI preferences")
    stream: bool = Field(default=True, description="Stream generation progress")


class GenerateUIResponse(BaseModel):
    generation_id: str
    status: GenerationStatus
    html: Optional[str] = None
    metadata: dict
    created_at: datetime
    generation_time_ms: int


class RefineUIRequest(BaseModel):
    generation_id: str
    refinement: str = Field(..., min_length=1, max_length=1000)


@router.post("/generate", response_model=GenerateUIResponse)
async def generate_ui(
    request: GenerateUIRequest,
    current_user: User = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    Generate a custom UI from natural language query.

    Rate Limit: 20 requests/minute per user
    """
    await rate_limiter.check("genui_generate", current_user.id, limit=20, window=60)

    generation = await genui_engine.generate(
        query=request.query,
        user=current_user,
        context=request.context,
        preferences=request.preferences
    )

    return GenerateUIResponse(
        generation_id=generation.id,
        status=generation.status,
        html=generation.html,
        metadata=generation.metadata,
        created_at=generation.created_at,
        generation_time_ms=generation.generation_time_ms
    )


@router.post("/generate/stream")
async def generate_ui_stream(
    request: GenerateUIRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream UI generation progress with Server-Sent Events.
    """
    async def event_generator():
        async for event in genui_engine.generate_stream(
            query=request.query,
            user=current_user,
            context=request.context
        ):
            yield f"data: {event.json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.post("/refine", response_model=GenerateUIResponse)
async def refine_ui(
    request: RefineUIRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Refine an existing generated UI with additional instructions.
    """
    generation = await genui_engine.refine(
        generation_id=request.generation_id,
        refinement=request.refinement,
        user=current_user
    )

    return GenerateUIResponse(
        generation_id=generation.id,
        status=generation.status,
        html=generation.html,
        metadata=generation.metadata,
        created_at=generation.created_at,
        generation_time_ms=generation.generation_time_ms
    )


@router.get("/history", response_model=List[GenerationSummary])
async def get_generation_history(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's generation history.
    """
    return await genui_repository.get_user_history(
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )


@router.post("/favorite/{generation_id}")
async def favorite_generation(
    generation_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Add generation to favorites.
    """
    await genui_repository.add_favorite(
        user_id=current_user.id,
        generation_id=generation_id
    )
    return {"status": "favorited"}


@router.get("/components")
async def list_available_components():
    """
    List available pre-built components.
    """
    return component_registry.list_components()
```

### 4.2 WebSocket Real-Time Updates

```python
# genui_service/api/websocket.py

@router.websocket("/ws/genui/{generation_id}")
async def genui_websocket(
    websocket: WebSocket,
    generation_id: str,
    token: str = Query(...)
):
    """
    WebSocket connection for real-time data updates in generated UI.
    """
    # Validate token and get user
    user = await validate_ws_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    # Get generation config
    generation = await genui_repository.get(generation_id)
    if not generation or generation.user_id != user.id:
        await websocket.close(code=4004)
        return

    # Subscribe to data channels based on generation requirements
    channels = generation.metadata.get("data_subscriptions", [])

    try:
        async for message in data_bridge.subscribe(channels):
            await websocket.send_json({
                "type": "data_update",
                "channel": message.channel,
                "data": message.data
            })
    except WebSocketDisconnect:
        pass
```

---

## 5. Database Schema

### 5.1 New Tables

```sql
-- Generation history
CREATE TABLE genui_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    context JSONB,
    requirements JSONB,
    fsm_state JSONB,
    generated_html TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    generation_time_ms INTEGER,
    llm_provider VARCHAR(50),
    llm_model VARCHAR(100),
    token_count INTEGER,
    iteration_count INTEGER DEFAULT 1,
    final_score FLOAT,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_genui_generations_user_id ON genui_generations(user_id);
CREATE INDEX idx_genui_generations_created_at ON genui_generations(created_at DESC);
CREATE INDEX idx_genui_generations_favorite ON genui_generations(user_id, is_favorite) WHERE is_favorite = TRUE;

-- Component usage analytics
CREATE TABLE genui_component_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID NOT NULL REFERENCES genui_generations(id) ON DELETE CASCADE,
    component_name VARCHAR(100) NOT NULL,
    component_config JSONB,
    render_count INTEGER DEFAULT 1,
    interaction_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_genui_component_usage_generation ON genui_component_usage(generation_id);
CREATE INDEX idx_genui_component_usage_name ON genui_component_usage(component_name);

-- User preferences for generation
CREATE TABLE genui_user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    default_theme VARCHAR(20) DEFAULT 'system',
    preferred_chart_type VARCHAR(50) DEFAULT 'candlestick',
    expertise_level VARCHAR(20) DEFAULT 'intermediate',
    favorite_components TEXT[],
    custom_color_scheme JSONB,
    accessibility_settings JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Generation feedback for model improvement
CREATE TABLE genui_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID NOT NULL REFERENCES genui_generations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_type VARCHAR(50),  -- 'quality', 'accuracy', 'usefulness', 'speed'
    feedback_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_genui_feedback_generation ON genui_feedback(generation_id);
```

### 5.2 SQLAlchemy Models

```python
# genui_service/models/generation.py

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import uuid

from user_service.database import Base


class GenUIGeneration(Base):
    __tablename__ = "genui_generations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=True)
    requirements: Mapped[dict] = mapped_column(JSONB, nullable=True)
    fsm_state: Mapped[dict] = mapped_column(JSONB, nullable=True)
    generated_html: Mapped[str] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=True)
    iteration_count: Mapped[int] = mapped_column(Integer, default=1)
    final_score: Mapped[float] = mapped_column(Float, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="genui_generations")
    component_usage = relationship("GenUIComponentUsage", back_populates="generation", cascade="all, delete-orphan")
    feedback = relationship("GenUIFeedback", back_populates="generation", cascade="all, delete-orphan")


class GenUIComponentUsage(Base):
    __tablename__ = "genui_component_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("genui_generations.id"), nullable=False)
    component_name: Mapped[str] = mapped_column(String(100), nullable=False)
    component_config: Mapped[dict] = mapped_column(JSONB, nullable=True)
    render_count: Mapped[int] = mapped_column(Integer, default=1)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    generation = relationship("GenUIGeneration", back_populates="component_usage")


class GenUIUserPreferences(Base):
    __tablename__ = "genui_user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    default_theme: Mapped[str] = mapped_column(String(20), default="system")
    preferred_chart_type: Mapped[str] = mapped_column(String(50), default="candlestick")
    expertise_level: Mapped[str] = mapped_column(String(20), default="intermediate")
    favorite_components: Mapped[list] = mapped_column(ARRAY(Text), nullable=True)
    custom_color_scheme: Mapped[dict] = mapped_column(JSONB, nullable=True)
    accessibility_settings: Mapped[dict] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class GenUIFeedback(Base):
    __tablename__ = "genui_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("genui_generations.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=True)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    generation = relationship("GenUIGeneration", back_populates="feedback")
```

---

## 6. Evaluation Framework

Based on the "Generative Interfaces for Language Models" research, implement a three-dimensional evaluation framework:

### 6.1 Evaluation Dimensions

```python
class UIEvaluator:
    """
    Evaluates generated UIs across three dimensions:
    Functional, Interactive, and Emotional.
    """

    async def evaluate(self, generated_ui: GeneratedUI, requirements: RequirementSpec) -> EvaluationResult:
        functional_score = await self._evaluate_functional(generated_ui, requirements)
        interactive_score = await self._evaluate_interactive(generated_ui)
        emotional_score = await self._evaluate_emotional(generated_ui)

        overall_score = (
            functional_score * 0.4 +
            interactive_score * 0.35 +
            emotional_score * 0.25
        )

        return EvaluationResult(
            functional=functional_score,
            interactive=interactive_score,
            emotional=emotional_score,
            overall=overall_score
        )

    async def _evaluate_functional(self, ui: GeneratedUI, requirements: RequirementSpec) -> float:
        """
        Evaluate:
        - Query-Interface Consistency: Does the UI address the query?
        - Task Efficiency: Can the user complete their task efficiently?
        - Data Accuracy: Is the displayed data correct?
        """
        checks = [
            self._check_required_data_present(ui, requirements),
            self._check_components_appropriate(ui, requirements),
            self._check_data_bindings_valid(ui),
            self._check_no_placeholder_data(ui),
        ]
        return sum(checks) / len(checks) * 100

    async def _evaluate_interactive(self, ui: GeneratedUI) -> float:
        """
        Evaluate:
        - Usability: Are interactions intuitive?
        - Learnability: Can users figure out how to use it?
        - Information Clarity: Is information well-organized?
        """
        checks = [
            self._check_touch_targets_adequate(ui),
            self._check_loading_states_present(ui),
            self._check_error_handling_present(ui),
            self._check_visual_hierarchy_clear(ui),
            self._check_navigation_logical(ui),
        ]
        return sum(checks) / len(checks) * 100

    async def _evaluate_emotional(self, ui: GeneratedUI) -> float:
        """
        Evaluate:
        - Aesthetic Appeal: Does it look professional?
        - Style Consistency: Does it match OPTIX design system?
        - Interaction Satisfaction: Are animations smooth?
        """
        checks = [
            self._check_design_system_compliance(ui),
            self._check_color_scheme_appropriate(ui),
            self._check_typography_consistent(ui),
            self._check_spacing_balanced(ui),
        ]
        return sum(checks) / len(checks) * 100
```

### 6.2 PAGEN-Style Benchmark Dataset

Create a benchmark dataset of expert-crafted UIs for comparison:

```python
OPTIX_GENUI_BENCHMARK = [
    {
        "query": "Show AAPL options chain",
        "expert_ui": "benchmarks/options_chain_expert.html",
        "required_elements": ["calls_table", "puts_table", "greeks_columns", "strike_prices"],
        "evaluation_criteria": ["data_accuracy", "interaction_flow", "visual_clarity"]
    },
    {
        "query": "What's my portfolio risk?",
        "expert_ui": "benchmarks/portfolio_risk_expert.html",
        "required_elements": ["greek_aggregation", "position_breakdown", "risk_heatmap"],
        "evaluation_criteria": ["calculation_accuracy", "actionable_insights", "drill_down"]
    },
    {
        "query": "Explain iron condor strategy",
        "expert_ui": "benchmarks/iron_condor_edu_expert.html",
        "required_elements": ["payoff_diagram", "leg_explanation", "risk_reward", "example"],
        "evaluation_criteria": ["educational_value", "interactivity", "progression"]
    },
    # ... additional benchmark queries
]
```

---

## 7. Non-Functional Requirements

### 7.1 Performance Requirements

| NFR ID | Requirement | Target | Measurement |
|--------|-------------|--------|-------------|
| NFR-G01 | Initial generation time | < 30 seconds (p95) | Server metrics |
| NFR-G02 | Incremental refinement time | < 10 seconds (p95) | Server metrics |
| NFR-G03 | UI render time | < 500ms | Client metrics |
| NFR-G04 | Real-time data latency | < 500ms | WebSocket metrics |
| NFR-G05 | Concurrent generations | 1000+ users | Load testing |
| NFR-G06 | Cache hit rate | > 30% | Cache analytics |
| NFR-G07 | LLM token efficiency | < 10K tokens/generation | LLM metrics |

### 7.2 Reliability Requirements

| NFR ID | Requirement | Target | Measurement |
|--------|-------------|--------|-------------|
| NFR-G08 | Generation success rate | > 95% | Error monitoring |
| NFR-G09 | Post-processing success | > 99% | Pipeline metrics |
| NFR-G10 | Graceful degradation | 100% fallback coverage | Error handling |
| NFR-G11 | Retry success rate | > 80% on first retry | Retry metrics |

### 7.3 Security Requirements

| NFR ID | Requirement | Implementation |
|--------|-------------|----------------|
| NFR-G12 | Code sanitization | Block dangerous patterns (eval, innerHTML, etc.) |
| NFR-G13 | CSP enforcement | Strict Content-Security-Policy headers |
| NFR-G14 | Sandbox isolation | WebView with disabled dangerous APIs |
| NFR-G15 | Rate limiting | 20 generations/min per user |
| NFR-G16 | Input validation | Max 2000 char queries, sanitized |
| NFR-G17 | Output validation | HTML/CSS/JS linting before render |
| NFR-G18 | Audit logging | All generations logged with user context |

### 7.4 Accessibility Requirements

| NFR ID | Requirement | Implementation |
|--------|-------------|----------------|
| NFR-G19 | WCAG 2.1 AA | Automated and manual accessibility testing |
| NFR-G20 | Screen reader support | ARIA labels on all interactive elements |
| NFR-G21 | Keyboard navigation | Full keyboard support, visible focus |
| NFR-G22 | Color contrast | Minimum 4.5:1 for text, 3:1 for UI |
| NFR-G23 | Motion sensitivity | Reduced motion option, no auto-play |

---

## 8. Implementation Plan

### 8.1 Phase 1: Foundation (Weeks 1-4)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 8.1.1 | Set up GenUI service structure | Service scaffold |
| 8.1.2 | Implement LLM abstraction layer | Provider interface |
| 8.1.3 | Create system prompts | Prompt templates |
| 8.1.4 | Build requirement parser | Parser module |
| 8.1.5 | Implement basic code synthesizer | Generation pipeline |
| 8.1.6 | Create security sanitizer | Sanitization module |
| 8.1.7 | Set up database schema | Alembic migration |
| 8.1.8 | Build basic API endpoints | FastAPI routes |

### 8.2 Phase 2: Component Library (Weeks 5-8)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 8.2.1 | Build OptionsChainTable component | Component + tests |
| 8.2.2 | Build GreeksGauges component | Component + tests |
| 8.2.3 | Build PayoffDiagram component | Component + tests |
| 8.2.4 | Build PositionCard component | Component + tests |
| 8.2.5 | Implement component registry | Registry service |
| 8.2.6 | Create FSM builder | State machine module |
| 8.2.7 | Build data bridge for market data | Data injection |
| 8.2.8 | Implement streaming generation | SSE endpoint |

### 8.3 Phase 3: Advanced Features (Weeks 9-12)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 8.3.1 | Build VolatilitySurface component | 3D visualization |
| 8.3.2 | Build StrategyBuilder component | Drag-drop builder |
| 8.3.3 | Implement iterative refinement | Generation-evaluation cycles |
| 8.3.4 | Build evaluation framework | Scoring system |
| 8.3.5 | Create benchmark dataset | PAGEN-style tests |
| 8.3.6 | Implement generation history | History API |
| 8.3.7 | Build favorites system | User preferences |
| 8.3.8 | Implement feedback collection | Feedback API |

### 8.4 Phase 4: Mobile Integration (Weeks 13-16)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 8.4.1 | Build React Native WebView renderer | Mobile renderer |
| 8.4.2 | Implement native bridge for data | Data communication |
| 8.4.3 | Create chat interface integration | UI integration |
| 8.4.4 | Build offline caching | Generation cache |
| 8.4.5 | Implement push updates | WebSocket client |
| 8.4.6 | Performance optimization | Mobile optimization |
| 8.4.7 | Accessibility audit | A11y compliance |
| 8.4.8 | End-to-end testing | Integration tests |

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/test_genui_engine.py

import pytest
from genui_service.core.engine import GenUIEngine
from genui_service.core.requirement_parser import RequirementParser


class TestRequirementParser:
    @pytest.fixture
    def parser(self):
        return RequirementParser()

    async def test_parse_simple_query(self, parser):
        query = "Show me AAPL options"
        result = await parser.parse(query, context=None)

        assert result.symbol == "AAPL"
        assert "options_chain" in result.target_data

    async def test_parse_complex_query(self, parser):
        query = "Compare covered call vs cash-secured put for NVDA earnings"
        result = await parser.parse(query, context=None)

        assert result.symbol == "NVDA"
        assert "strategy_comparison" in result.visualizations
        assert result.context.get("event") == "earnings"


class TestCodeSynthesizer:
    async def test_generates_valid_html(self, synthesizer, mock_llm):
        requirements = RequirementSpec(
            target_data=["quote"],
            symbol="SPY",
            visualizations=["card"]
        )

        result = await synthesizer.synthesize(requirements)

        assert result.html.startswith("<!DOCTYPE html>")
        assert "<body>" in result.html
        assert "SPY" in result.html


class TestSecuritySanitizer:
    def test_blocks_eval(self, sanitizer):
        html = '<script>eval("alert(1)")</script>'
        result = sanitizer.process(html)

        assert "eval" not in result
        assert "/* BLOCKED */" in result

    def test_blocks_inline_handlers(self, sanitizer):
        html = '<button onclick="doSomething()">Click</button>'
        result = sanitizer.process(html)

        assert 'onclick=' not in result
```

### 9.2 Integration Tests

```python
# tests/test_genui_api.py

import pytest
from httpx import AsyncClient


class TestGenUIAPI:
    @pytest.fixture
    async def client(self, app):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    async def test_generate_ui_success(self, client, auth_headers):
        response = await client.post(
            "/api/v1/genui/generate",
            json={"query": "Show me AAPL quote"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["generating", "complete"]
        assert "generation_id" in data

    async def test_generate_ui_rate_limited(self, client, auth_headers):
        # Make 21 requests quickly
        for i in range(21):
            response = await client.post(
                "/api/v1/genui/generate",
                json={"query": f"Query {i}"},
                headers=auth_headers
            )

        assert response.status_code == 429  # Rate limited

    async def test_refine_ui(self, client, auth_headers, existing_generation):
        response = await client.post(
            "/api/v1/genui/refine",
            json={
                "generation_id": existing_generation.id,
                "refinement": "Add the puts side too"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
```

### 9.3 Benchmark Tests

```python
# tests/test_genui_benchmark.py

import pytest
from genui_service.evaluation import UIEvaluator
from genui_service.benchmarks import OPTIX_GENUI_BENCHMARK


class TestGenUIBenchmark:
    @pytest.fixture
    def evaluator(self):
        return UIEvaluator()

    @pytest.mark.parametrize("benchmark", OPTIX_GENUI_BENCHMARK)
    async def test_benchmark_query(self, genui_engine, evaluator, benchmark):
        """
        Test that generated UI meets minimum quality threshold for benchmark queries.
        """
        generated = await genui_engine.generate(query=benchmark["query"])
        evaluation = await evaluator.evaluate(generated, benchmark["required_elements"])

        # Minimum acceptable scores
        assert evaluation.functional >= 70.0, f"Functional score too low: {evaluation.functional}"
        assert evaluation.interactive >= 60.0, f"Interactive score too low: {evaluation.interactive}"
        assert evaluation.overall >= 65.0, f"Overall score too low: {evaluation.overall}"
```

---

## 10. Monitoring & Observability

### 10.1 Metrics

```python
# genui_service/monitoring.py

from prometheus_client import Counter, Histogram, Gauge

# Generation metrics
GENERATION_REQUESTS = Counter(
    "genui_generation_requests_total",
    "Total generation requests",
    ["status", "llm_provider"]
)

GENERATION_DURATION = Histogram(
    "genui_generation_duration_seconds",
    "Generation duration in seconds",
    buckets=[1, 5, 10, 20, 30, 45, 60, 90, 120]
)

GENERATION_TOKENS = Histogram(
    "genui_generation_tokens",
    "Tokens used per generation",
    buckets=[1000, 2000, 5000, 10000, 20000, 50000]
)

GENERATION_ITERATIONS = Histogram(
    "genui_generation_iterations",
    "Refinement iterations per generation",
    buckets=[1, 2, 3, 4, 5]
)

GENERATION_SCORE = Histogram(
    "genui_generation_score",
    "Final evaluation score",
    buckets=[50, 60, 70, 80, 90, 95, 100]
)

# Active generations
ACTIVE_GENERATIONS = Gauge(
    "genui_active_generations",
    "Currently active generations"
)

# Cache metrics
CACHE_HITS = Counter(
    "genui_cache_hits_total",
    "Cache hits for similar queries"
)

CACHE_MISSES = Counter(
    "genui_cache_misses_total",
    "Cache misses"
)

# Component usage
COMPONENT_USAGE = Counter(
    "genui_component_usage_total",
    "Component usage in generations",
    ["component_name"]
)
```

### 10.2 Logging

```python
# Structured logging for generation events

logger.info(
    "genui_generation_started",
    generation_id=generation.id,
    user_id=user.id,
    query_length=len(query),
    has_context=context is not None
)

logger.info(
    "genui_generation_complete",
    generation_id=generation.id,
    duration_ms=generation_time_ms,
    llm_provider=llm_provider,
    token_count=token_count,
    iteration_count=iteration_count,
    final_score=final_score,
    component_count=len(components_used)
)

logger.warning(
    "genui_generation_failed",
    generation_id=generation.id,
    error_type=type(e).__name__,
    error_message=str(e),
    retry_count=retry_count
)
```

---

## 11. Dependencies

### 11.1 Python Packages

```
# requirements-genui.txt

# LLM Providers
anthropic>=0.39.0
google-generativeai>=0.8.0
openai>=1.50.0

# HTML/Code Processing
beautifulsoup4>=4.12.0
lxml>=5.0.0
html5lib>=1.1
cssutils>=2.9.0

# Security
bleach>=6.1.0
defusedxml>=0.7.1

# Validation
jsonschema>=4.21.0
pydantic>=2.5.0

# Caching
redis>=5.0.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

### 11.2 Frontend Dependencies

```json
// package.json additions
{
  "dependencies": {
    "@anthropic-ai/sdk": "^0.30.0",
    "d3": "^7.8.5",
    "lightweight-charts": "^4.1.0",
    "react-native-webview": "^13.6.0",
    "dompurify": "^3.0.8"
  }
}
```

---

## 12. Appendix

### 12.1 Example Generated UI

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';">
  <title>AAPL Options Chain</title>
  <style>
    :root {
      --primary: #2563EB;
      --bg-dark: #0F172A;
      --bg-light: #1E293B;
      --text: #F1F5F9;
      --green: #22C55E;
      --red: #EF4444;
    }

    body {
      font-family: Inter, system-ui, sans-serif;
      background: var(--bg-dark);
      color: var(--text);
      margin: 0;
      padding: 16px;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .symbol {
      font-size: 24px;
      font-weight: 700;
    }

    .price {
      font-size: 20px;
      color: var(--green);
    }

    .expiration-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      overflow-x: auto;
    }

    .tab {
      padding: 8px 16px;
      background: var(--bg-light);
      border-radius: 8px;
      cursor: pointer;
      white-space: nowrap;
    }

    .tab.active {
      background: var(--primary);
    }

    .chain-table {
      width: 100%;
      border-collapse: collapse;
    }

    .chain-table th,
    .chain-table td {
      padding: 12px 8px;
      text-align: right;
    }

    .chain-table th {
      background: var(--bg-light);
      position: sticky;
      top: 0;
    }

    .strike {
      text-align: center;
      font-weight: 600;
      background: var(--bg-light);
    }

    .itm {
      background: rgba(34, 197, 94, 0.1);
    }

    .high-oi {
      background: rgba(37, 99, 235, 0.2);
    }

    .greeks {
      font-size: 12px;
      color: #94A3B8;
    }

    @media (prefers-color-scheme: light) {
      :root {
        --bg-dark: #FFFFFF;
        --bg-light: #F1F5F9;
        --text: #0F172A;
      }
    }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <span class="symbol">AAPL</span>
      <span class="price" id="current-price">${{DATA:quote:AAPL.price}}</span>
    </div>
    <div class="greeks">
      Last updated: <span id="timestamp">{{DATA:quote:AAPL.timestamp}}</span>
    </div>
  </div>

  <div class="expiration-tabs" id="expirations">
    <!-- Populated dynamically -->
  </div>

  <table class="chain-table">
    <thead>
      <tr>
        <th>Bid</th>
        <th>Ask</th>
        <th>Last</th>
        <th>Vol</th>
        <th>OI</th>
        <th>Δ</th>
        <th class="strike">Strike</th>
        <th>Δ</th>
        <th>OI</th>
        <th>Vol</th>
        <th>Last</th>
        <th>Ask</th>
        <th>Bid</th>
      </tr>
    </thead>
    <tbody id="chain-body">
      <!-- Populated dynamically -->
    </tbody>
  </table>

  <script>
    // Data bridge communication
    const dataBridge = window.OPTIXDataBridge || {
      subscribe: () => {},
      request: async () => ({})
    };

    // State
    let currentExpiration = null;
    let chainData = null;

    // Initialize
    async function init() {
      const expirations = await dataBridge.request('options_expirations', { symbol: 'AAPL' });
      renderExpirations(expirations);

      if (expirations.length > 0) {
        selectExpiration(expirations[0]);
      }

      // Subscribe to real-time updates
      dataBridge.subscribe('quote:AAPL', updatePrice);
      dataBridge.subscribe('options_chain:AAPL', updateChain);
    }

    function renderExpirations(expirations) {
      const container = document.getElementById('expirations');
      container.innerHTML = expirations.map((exp, i) =>
        `<div class="tab ${i === 0 ? 'active' : ''}" data-exp="${exp}">${formatDate(exp)}</div>`
      ).join('');

      container.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => selectExpiration(tab.dataset.exp));
      });
    }

    async function selectExpiration(exp) {
      currentExpiration = exp;
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelector(`[data-exp="${exp}"]`)?.classList.add('active');

      chainData = await dataBridge.request('options_chain', {
        symbol: 'AAPL',
        expiration: exp
      });
      renderChain(chainData);
    }

    function renderChain(data) {
      const tbody = document.getElementById('chain-body');
      const currentPrice = parseFloat(document.getElementById('current-price').textContent.replace('$', ''));
      const maxOI = Math.max(...data.map(d => Math.max(d.call.openInterest, d.put.openInterest)));

      tbody.innerHTML = data.map(row => {
        const isITM = row.strike < currentPrice;
        const isHighOI = row.call.openInterest > maxOI * 0.7 || row.put.openInterest > maxOI * 0.7;

        return `
          <tr class="${isITM ? 'itm' : ''} ${isHighOI ? 'high-oi' : ''}">
            <td>${row.call.bid.toFixed(2)}</td>
            <td>${row.call.ask.toFixed(2)}</td>
            <td>${row.call.last.toFixed(2)}</td>
            <td>${formatNumber(row.call.volume)}</td>
            <td>${formatNumber(row.call.openInterest)}</td>
            <td class="greeks">${row.call.delta.toFixed(2)}</td>
            <td class="strike">${row.strike}</td>
            <td class="greeks">${row.put.delta.toFixed(2)}</td>
            <td>${formatNumber(row.put.openInterest)}</td>
            <td>${formatNumber(row.put.volume)}</td>
            <td>${row.put.last.toFixed(2)}</td>
            <td>${row.put.ask.toFixed(2)}</td>
            <td>${row.put.bid.toFixed(2)}</td>
          </tr>
        `;
      }).join('');
    }

    function updatePrice(data) {
      document.getElementById('current-price').textContent = `$${data.price.toFixed(2)}`;
      document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleTimeString();
    }

    function updateChain(data) {
      if (data.expiration === currentExpiration) {
        renderChain(data.chain);
      }
    }

    function formatDate(dateStr) {
      return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    function formatNumber(num) {
      if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
      if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
      return num.toString();
    }

    init();
  </script>
</body>
</html>
```

### 12.2 References

- [Generative UI: LLMs are Effective UI Generators](https://generativeui.github.io/) - Google Research
- [Google Research Blog: Generative UI](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)
- [Generative Interfaces for Language Models](https://arxiv.org/html/2508.19227v2) - arXiv
- [The GenUI Study](https://arxiv.org/abs/2501.13145) - arXiv
- [Generative AI in Multimodal User Interfaces](https://arxiv.org/html/2411.10234v1) - arXiv

---

*End of Document*

*Last Updated: December 12, 2024*
*Version: 1.0*
*Author: DSDM Agents System*
