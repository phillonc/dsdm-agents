"""
Configuration settings for the Generative UI Service.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = "OPTIX GenUI Service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8004

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://optix:optix_secret@localhost:5433/optix_genui",
        description="PostgreSQL connection URL"
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/2"
    cache_ttl: int = 3600  # 1 hour

    # LLM Providers
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Default LLM settings
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-opus-4-5-20251101"
    max_tokens: int = 16000
    temperature: float = 0.7

    # Generation settings
    max_query_length: int = 2000
    max_refinement_length: int = 1000
    max_iterations: int = 5
    target_score: float = 90.0
    generation_timeout: int = 60  # seconds

    # Rate limiting
    rate_limit_generations: int = 20  # per minute
    rate_limit_window: int = 60  # seconds

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for token signing"
    )
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Component library
    component_templates_path: str = "components/templates"

    class Config:
        env_prefix = "GENUI_"
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
