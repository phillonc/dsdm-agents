"""Configuration settings for GEX Visualizer."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application
    app_name: str = "GEX Visualizer"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Database
    database_url: str = "postgresql://gex_user:gex_pass@localhost:5432/gex_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 300  # 5 minutes
    
    # GEX Calculation Settings
    risk_free_rate: float = 0.05  # 5% annual risk-free rate
    trading_days_per_year: int = 252
    
    # Alert Thresholds
    gamma_flip_threshold_pct: float = 5.0  # Alert when within 5% of gamma flip
    pin_risk_days_to_expiry: int = 5  # Consider pin risk within 5 days
    high_gex_threshold: float = 1e9  # $1B GEX threshold
    
    # Data Storage
    historical_data_days: int = 365  # Keep 1 year of historical data
    
    # Market Data
    options_chain_api_url: Optional[str] = None
    options_chain_api_key: Optional[str] = None
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


settings = Settings()
