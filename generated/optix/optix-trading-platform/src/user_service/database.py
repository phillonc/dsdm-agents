"""
Database configuration and session management
SQLAlchemy 2.0 synchronous implementation with connection pooling
"""
from typing import Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
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
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None
        self._is_initialized = False

    def initialize(self) -> None:
        """Initialize database engine and session factory"""
        if self._is_initialized:
            logger.warning("Database already initialized")
            return

        try:
            # Ensure we're using psycopg2 sync driver
            database_url = settings.DATABASE_URL
            if "asyncpg" in database_url:
                database_url = database_url.replace("+asyncpg", "+psycopg2")
            elif database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            elif database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)

            # Create sync engine with connection pooling
            self._engine = create_engine(
                database_url,
                echo=settings.DEBUG,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                pool_recycle=3600,
                poolclass=QueuePool,
            )

            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False
            )

            # Test connection
            self.health_check()

            self._is_initialized = True
            logger.info("Database initialized successfully", url=database_url.split('@')[1] if '@' in database_url else database_url)

        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise

    def close(self) -> None:
        """Close database engine and cleanup connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")
            self._is_initialized = False

    def health_check(self) -> bool:
        """Check database health"""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.debug("Database health check passed")
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get database session as context manager

        Usage:
            with db_manager.get_session() as session:
                result = session.execute(select(User))
        """
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_raw_session(self) -> Session:
        """
        Get raw database session (caller responsible for commit/rollback/close)
        Use get_session() context manager when possible
        """
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return self._session_factory()

    @property
    def engine(self) -> Engine:
        """Get database engine"""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Get session factory"""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI routes
def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions

    Usage:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db_session)):
            result = db.execute(select(User))
            return result.scalars().all()
    """
    if not db_manager._is_initialized:
        raise RuntimeError("Database not initialized. Call initialize() first.")

    session = db_manager._session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Lifecycle management (sync versions for compatibility)
def init_db() -> None:
    """Initialize database on application startup"""
    db_manager.initialize()


def close_db() -> None:
    """Close database on application shutdown"""
    db_manager.close()


# Async wrappers for FastAPI lifespan events
async def init_db_async() -> None:
    """Async wrapper for init_db"""
    init_db()


async def close_db_async() -> None:
    """Async wrapper for close_db"""
    close_db()
