"""
Configuration settings for OPTIX Backtester
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    api_title: str = "OPTIX Time Machine Backtester"
    api_version: str = "1.0.0"
    api_description: str = "Historical options backtesting and strategy optimization platform"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://optix:optix@localhost:5432/optix_backtester",
        description="Database connection URL"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching"
    )
    
    # Backtesting Configuration
    default_initial_capital: float = 100000.0
    default_commission_per_contract: float = 0.65
    default_slippage_percent: float = 0.1
    min_option_price: float = 0.05
    max_position_size: int = 100
    
    # Monte Carlo Configuration
    monte_carlo_iterations: int = 1000
    monte_carlo_confidence_levels: list[float] = [0.95, 0.99]
    
    # Walk-Forward Configuration
    walk_forward_train_ratio: float = 0.7
    walk_forward_test_periods: int = 5
    
    # Performance Configuration
    risk_free_rate: float = 0.04  # 4% annual
    trading_days_per_year: int = 252
    
    # Data Storage
    data_cache_dir: str = "./data/cache"
    results_dir: str = "./data/results"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    access_token_expire_minutes: int = 60
    
    # Performance Tuning
    max_workers: int = 4
    batch_size: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
