"""
Main application entry point for the Adaptive Intelligence Engine
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .api import (
    patterns_router,
    analysis_router,
    personalization_router,
    alerts_router
)

# Create FastAPI application
app = FastAPI(
    title="OPTIX Adaptive Intelligence Engine",
    description="AI-powered pattern recognition and analysis system for options trading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(patterns_router)
app.include_router(analysis_router)
app.include_router(personalization_router)
app.include_router(alerts_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OPTIX Adaptive Intelligence Engine",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "patterns": "/api/v1/patterns",
            "analysis": "/api/v1/analysis",
            "personalization": "/api/v1/personalization",
            "alerts": "/api/v1/alerts",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/api/v1/capabilities")
async def get_capabilities():
    """Get system capabilities"""
    return {
        "pattern_recognition": {
            "chart_patterns": [
                "head_shoulders",
                "double_top",
                "double_bottom",
                "triangles",
                "flags",
                "wedges",
                "breakouts"
            ],
            "unusual_options_activity": [
                "unusual_volume",
                "sweeps",
                "golden_sweeps",
                "oi_changes"
            ],
            "volume_analysis": [
                "spikes",
                "divergence",
                "climax",
                "accumulation"
            ],
            "support_resistance": True
        },
        "ai_analysis": {
            "price_prediction": ["1D", "1W", "1M", "3M"],
            "volatility_forecasting": ["EWMA", "GARCH"],
            "sentiment_analysis": [
                "news",
                "options_flow",
                "market_breadth",
                "technical_indicators"
            ],
            "market_context": True
        },
        "personalization": {
            "pattern_learning": True,
            "custom_insights": True,
            "performance_tracking": True,
            "educational_content": True
        },
        "alerts": {
            "channels": ["in_app", "email", "sms", "push", "webhook"],
            "types": [
                "pattern_detected",
                "prediction_signal",
                "unusual_options",
                "volatility_change",
                "opportunity",
                "risk_warning"
            ],
            "customization": True
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI server"""
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    run_server(reload=True)
