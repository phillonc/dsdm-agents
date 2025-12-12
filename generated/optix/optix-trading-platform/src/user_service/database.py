"""
Database configuration and session management
SQLAlchemy 2.0 async implementation with connection pooling
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import event, text
import structlog

from config.settings import settings

logger = structlog.get_logger()


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


class DatabaseManager:
    """
    Manages database connections and sessions with SQLAlchemy 2.0
    Implements connection pooling and health checks
    """
    
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize database engine and session factory"""
        if self._is_initialized:
            logger.warning("Database already initialized")
            return
        
        try:
            # Convert PostgreSQL URL to async format
            database_url = settings.DATABASE_URL
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
            
            # Create async engine with connection pooling
            self._engine = create_async_engine(
                database_url,
                echo=settings.DEBUG,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,   # Recycle connections after 1 hour
                poolclass=AsyncAdaptedQueuePool,
                connect_args={
                    "server_settings": {
                        "application_name": "optix_platform",
                        "jit": "off"  # Disable JIT for better predictability
                    },
                    "command_timeout": 60,
                    "timeout": 30,
                }
            )
            
            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )
            
            # Add event listeners
            self._setup_event_listeners()
            
            # Test connection
            await self.health_check()
            
            self._is_initialized = True
            logger.info("Database initialized successfully", url=database_url.split('@')[1])
            
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for monitoring"""
        
        @event.listens_for(self._engine.sync_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Event fired when connection is created"""
            logger.debug("Database connection established")
        
        @event.listens_for(self._engine.sync_engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Event fired when connection is checked out from pool"""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self._engine.sync_engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Event fired when connection is returned to pool"""
            logger.debug("Connection returned to pool")
    
    async def close(self) -> None:
        """Close database engine and cleanup connections"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connections closed")
            self._is_initialized = False
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.debug("Database health check passed")
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session as async context manager
        
        Usage:
            async with db_manager.get_session() as session:
                result = await session.execute(select(User))
        """
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def get_raw_session(self) -> AsyncSession:
        """
        Get raw database session (caller responsible for commit/rollback/close)
        Use get_session() context manager when possible
        """
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        return self._session_factory()
    
    @property
    def engine(self) -> AsyncEngine:
        """Get database engine"""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory"""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI routes
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions
    
    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with db_manager.get_session() as session:
        yield session


# Lifecycle management
async def init_db() -> None:
    """Initialize database on application startup"""
    await db_manager.initialize()


async def close_db() -> None:
    """Close database on application shutdown"""
    await db_manager.close()
