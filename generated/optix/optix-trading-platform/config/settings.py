"""
OPTIX Trading Platform Configuration
Environment-based settings management
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "OPTIX Trading Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    
    # Security
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:19006",
        "https://optix.app"
    ]
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres_password@localhost:5433/optix"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Market Data
    MARKET_DATA_PROVIDER: str = "mock"  # mock, polygon, alphavantage
    POLYGON_API_KEY: Optional[str] = None
    ALPHAVANTAGE_API_KEY: Optional[str] = None
    
    # Brokerage Integrations
    SCHWAB_CLIENT_ID: Optional[str] = None
    SCHWAB_CLIENT_SECRET: Optional[str] = None
    TD_CLIENT_ID: Optional[str] = None
    TD_CLIENT_SECRET: Optional[str] = None
    FIDELITY_CLIENT_ID: Optional[str] = None
    FIDELITY_CLIENT_SECRET: Optional[str] = None
    
    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # Monitoring
    DATADOG_API_KEY: Optional[str] = None
    SENTRY_DSN: Optional[str] = None
    
    # Push Notifications
    FCM_SERVER_KEY: Optional[str] = None  # Firebase Cloud Messaging
    APNS_KEY_ID: Optional[str] = None  # Apple Push Notification Service
    APNS_TEAM_ID: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Feature Flags
    ENABLE_MFA: bool = True
    ENABLE_BROKERAGE_SYNC: bool = True
    ENABLE_ALERTS: bool = True
    ENABLE_WEBSOCKET: bool = True
    
    # Performance
    CACHE_TTL_QUOTES: int = 1  # seconds
    CACHE_TTL_OPTIONS_CHAIN: int = 5  # seconds
    CACHE_TTL_EXPIRATIONS: int = 3600  # 1 hour
    
    # Limits
    MAX_WATCHLISTS_PER_USER: int = 10
    MAX_SYMBOLS_PER_WATCHLIST: int = 50
    MAX_ALERTS_PER_USER: int = 50
    MAX_BROKERAGE_CONNECTIONS: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables from parent projects


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()
