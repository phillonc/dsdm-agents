"""
FastAPI application factory for the Generative UI Service.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from .router import router as genui_router
from .websocket import websocket_endpoint
from ..config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")

    yield

    # Shutdown
    print("Shutting down GenUI Service")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
OPTIX Generative UI Service

AI-powered dynamic interface generation that creates custom, interactive
experiences from natural language queries.

## Features

- **Natural Language UI Generation**: Describe your desired interface and get interactive HTML/CSS/JS
- **Pre-built Component Library**: Optimized components for options trading
- **Real-time Data Integration**: Connect to live market data
- **Iterative Refinement**: Improve generated UIs with follow-up instructions

## Authentication

All endpoints require JWT Bearer token authentication.
```
Authorization: Bearer <access_token>
```

## Rate Limits

- Generation: 20 requests/minute per user
- Standard API: 100 requests/minute per user
        """,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request timing middleware
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        return response

    # Register routers
    app.include_router(genui_router)

    # Register WebSocket endpoint
    app.add_api_websocket_route(
        "/ws/genui/{generation_id}",
        websocket_endpoint,
    )

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "docs": "/docs" if settings.debug else "disabled",
        }

    # Global health check
    @app.get("/health")
    async def global_health():
        return {
            "status": "healthy",
            "service": "genui",
            "version": settings.app_version,
        }

    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": str(exc) if settings.debug else "An internal error occurred",
                "request_id": request.headers.get("X-Request-ID"),
            },
        )

    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "genui_service.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
