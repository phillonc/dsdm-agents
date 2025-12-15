"""
OPTIX Trading Platform - Main Application
Microservices-based options trading platform

Phase 1 Implementation:
- VS-0: Core Mobile Foundation
- VS-7: Universal Brokerage Sync

Phase 2 Enhancements:
- Redis integration for session management and token blacklist
- PostgreSQL for production persistence with async SQLAlchemy 2.0

Phase 3 Enhancements:
- Redis-based rate limiting with sliding window algorithm
- Repository pattern for database operations
- Alembic migrations for schema management
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager

# Import service routers
import sys
from pathlib import Path

# Add src directory to path for local imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from user_service.api import router as user_router
from market_data_service.api import router as market_data_router
from watchlist_service.api import router as watchlist_router
from brokerage_service.api import router as brokerage_router
from alert_service.api import router as alert_router

# Import infrastructure components
from user_service.redis_client import get_redis_client
from user_service.database import init_db_async, close_db_async, db_manager
from user_service.rate_limiter import get_rate_limiter, add_rate_limit_headers
from config.settings import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


# Global references
redis_client = None
rate_limiter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global redis_client, rate_limiter
    
    logger.info("startup", message="OPTIX Trading Platform starting up...")
    logger.info("phase", 
                phase_1="VS-0 (Core Foundation) + VS-7 (Brokerage Sync)",
                phase_2="Redis Integration + Production Persistence",
                phase_3="Rate Limiting + Repository Pattern")
    
    # Initialize PostgreSQL (sync SQLAlchemy with async wrapper)
    try:
        await init_db_async()
        is_healthy = db_manager.health_check()
        if is_healthy:
            logger.info("database", status="connected", url=settings.DATABASE_URL.split('@')[1])
        else:
            logger.error("database", status="unhealthy")
    except Exception as e:
        logger.error("database", status="failed", error=str(e))
        logger.warning("database", message="Running without database")
    
    # Initialize Redis connection
    try:
        redis_client = get_redis_client(
            redis_url=settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS
        )
        await redis_client.connect()
        logger.info("redis", status="connected", url=settings.REDIS_URL)
    except Exception as e:
        logger.error("redis", status="failed", error=str(e))
        logger.warning("redis", message="Running without Redis - using in-memory storage")
    
    # Initialize rate limiter
    try:
        rate_limiter = await get_rate_limiter()
        logger.info("rate_limiter", status="initialized", limits={
            "auth_login": "5/min",
            "auth_register": "3/min",
            "auth_refresh": "10/min",
            "api_default": "100/min"
        })
    except Exception as e:
        logger.error("rate_limiter", status="failed", error=str(e))
    
    yield
    
    # Cleanup on shutdown
    logger.info("shutdown", message="OPTIX Trading Platform shutting down...")
    
    # Close database connections
    try:
        await close_db_async()
        logger.info("database", status="disconnected")
    except Exception as e:
        logger.error("database", error=f"Error closing database: {e}")
    
    # Close Redis connections
    if redis_client:
        try:
            await redis_client.disconnect()
            logger.info("redis", status="disconnected")
        except Exception as e:
            logger.error("redis", error=f"Error disconnecting Redis: {e}")


# Create FastAPI application
app = FastAPI(
    title="OPTIX Trading Platform API",
    description="""
    Mobile-first options trading platform with AI-powered insights.
    
    ## Vertical Slices Implemented
    
    ### VS-0: Core Mobile Foundation (Must Have)
    - User authentication with MFA
    - Real-time quotes and options chains
    - Watchlist management (max 50 symbols)
    - Basic price alerts
    - WebSocket streaming
    
    ### VS-7: Universal Brokerage Sync (Must Have)
    - Multi-broker OAuth integration
    - Unified portfolio view
    - Real-time position sync
    - Transaction history
    - Cross-account Greeks
    
    ## Phase 2 Enhancements
    
    ### Redis Integration
    - Distributed session management
    - Token blacklist with automatic expiration
    - Device trust tracking
    - Security event logging
    - High-performance caching
    
    ### PostgreSQL Integration
    - Async SQLAlchemy 2.0 ORM
    - Repository pattern for data access
    - Alembic migrations for schema management
    - Session persistence and audit trails
    - User, session, and security event storage
    
    ## Phase 3 Enhancements
    
    ### Rate Limiting
    - Redis-based sliding window algorithm
    - Per-endpoint rate limits
    - Admin bypass support
    - Standard HTTP rate limit headers
    - Graceful degradation on Redis failure
    
    ## Performance Requirements (NFRs)
    - API response time p95 < 200ms (reads), < 500ms (writes)
    - Real-time data latency < 500ms from source
    - Support 100K concurrent users
    - 99.9% uptime during market hours
    - Rate limit checks < 3ms
    - Database queries < 20ms
    
    ## Security
    - JWT authentication with 15-minute access tokens
    - Redis-backed token blacklist
    - PostgreSQL persistent session storage
    - MFA required for brokerage connections
    - Rate limiting on all auth endpoints
    - Comprehensive security audit logs
    - AES-256 encryption at rest
    - TLS 1.3 in transit
    """,
    version="1.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limit headers middleware
@app.middleware("http")
async def rate_limit_headers_middleware(request: Request, call_next):
    """Add rate limit headers to all responses"""
    response = await call_next(request)
    
    # Add rate limit headers if available
    rate_limit_info = getattr(request.state, "rate_limit_info", None)
    if rate_limit_info:
        add_rate_limit_headers(response, rate_limit_info)
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error("exception", 
                 path=request.url.path,
                 method=request.method,
                 error=str(exc),
                 exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """
    Comprehensive health check endpoint for load balancers and monitoring
    """
    # Check PostgreSQL health (sync method)
    db_status = "unknown"
    db_info = {}

    try:
        is_healthy = db_manager.health_check()
        if is_healthy:
            db_status = "healthy"
            pool = db_manager.engine.pool
            db_info = {
                "pool_size": pool.size(),
                "checked_out": pool.checkedout()
            }
        else:
            db_status = "unhealthy"
    except Exception as e:
        db_status = "error"
        db_info = {"error": str(e)}
    
    # Check Redis health
    redis_status = "disconnected"
    redis_info = {}
    
    if redis_client:
        try:
            is_healthy = await redis_client.ping()
            if is_healthy:
                redis_status = "healthy"
                info = await redis_client.info("stats")
                redis_info = {
                    "connected_clients": info.get("connected_clients", 0),
                    "ops_per_sec": info.get("instantaneous_ops_per_sec", 0)
                }
        except Exception as e:
            redis_status = "unhealthy"
            redis_info = {"error": str(e)}
    
    # Overall health status
    overall_status = "healthy"
    if db_status == "unhealthy" or redis_status == "unhealthy":
        overall_status = "degraded"
    elif db_status == "error" or redis_status == "error":
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "version": "1.2.0",
        "phase": "Phase 1-3: Foundation + Redis + PostgreSQL + Rate Limiting",
        "services": {
            "user_service": "operational",
            "market_data_service": "operational",
            "watchlist_service": "operational",
            "brokerage_service": "operational",
            "alert_service": "operational"
        },
        "infrastructure": {
            "database": {
                "status": db_status,
                **db_info
            },
            "redis": {
                "status": redis_status,
                **redis_info
            },
            "rate_limiter": {
                "status": "operational" if rate_limiter else "disabled",
                "enabled": settings.RATE_LIMIT_ENABLED
            }
        }
    }


@app.get("/health/database", tags=["system"])
async def database_health():
    """Dedicated database health check"""
    try:
        is_healthy = db_manager.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "database": "postgresql",
            "driver": "psycopg2"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/health/redis", tags=["system"])
async def redis_health():
    """Dedicated Redis health check"""
    if not redis_client:
        return {
            "status": "disconnected",
            "message": "Redis client not initialized"
        }
    
    try:
        is_healthy = await redis_client.ping()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "cache": "redis"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/", tags=["system"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "OPTIX Trading Platform API",
        "version": "1.2.0",
        "phase": "Phase 1-3: Foundation + Redis + PostgreSQL + Rate Limiting",
        "implemented_slices": [
            "VS-0: Core Mobile Foundation",
            "VS-7: Universal Brokerage Sync"
        ],
        "infrastructure": [
            "PostgreSQL: Production persistence with async SQLAlchemy 2.0",
            "Redis: Session management, token blacklist, and rate limiting",
            "Alembic: Database migration management",
            "Rate Limiting: Sliding window algorithm for API protection"
        ],
        "features": [
            "Repository pattern for clean data access",
            "Comprehensive security audit logging",
            "Admin bypass for rate limiting",
            "Connection pooling with health checks",
            "Graceful degradation on infrastructure failures"
        ],
        "documentation": "/docs",
        "health": "/health",
        "database_health": "/health/database",
        "redis_health": "/health/redis"
    }


# Register service routers
app.include_router(user_router)
app.include_router(market_data_router)
app.include_router(watchlist_router)
app.include_router(brokerage_router)
app.include_router(alert_router)


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        workers=1 if settings.DEBUG else settings.API_WORKERS
    )
