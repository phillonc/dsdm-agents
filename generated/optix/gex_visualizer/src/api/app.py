"""FastAPI application factory."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.api.routers import gex_router, alerts_router, historical_router
from src.services import StorageService
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Args:
        app: FastAPI application
        
    Yields:
        None
    """
    # Startup
    storage = StorageService()
    await storage.init_db()
    app.state.storage = storage
    
    yield
    
    # Shutdown
    # Cleanup if needed


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="GEX Visualizer for OPTIX Trading Platform - Gamma Exposure Analytics",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(
        gex_router,
        prefix=f"{settings.api_prefix}/gex",
        tags=["GEX Calculations"]
    )
    
    app.include_router(
        alerts_router,
        prefix=f"{settings.api_prefix}/alerts",
        tags=["Alerts"]
    )
    
    app.include_router(
        historical_router,
        prefix=f"{settings.api_prefix}/historical",
        tags=["Historical Data"]
    )
    
    # Prometheus metrics endpoint
    if settings.enable_metrics:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
    
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version
        }
    
    @app.get("/")
    async def root() -> dict:
        """Root endpoint."""
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/api/docs"
        }
    
    return app
