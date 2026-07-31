"""
Configuration settings for brokerage service
"""

from pydantic_settings import BaseSettings
from typing import Optional


class BrokerageSettings(BaseSettings):
    """Brokerage service configuration"""
    
    # Schwab/TD Ameritrade
    schwab_client_id: str = ""
    schwab_client_secret: str = ""
    schwab_redirect_uri: str = "https://optix.app/oauth/callback/schwab"
    
    # Fidelity
    fidelity_client_id: str = ""
    fidelity_client_secret: str = ""
    fidelity_redirect_uri: str = "https://optix.app/oauth/callback/fidelity"
    
    # Plaid (for Robinhood)
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "production"  # sandbox, development, or production
    
    # Interactive Brokers
    ibkr_client_id: str = ""
    ibkr_client_secret: str = ""
    ibkr_redirect_uri: str = "https://optix.app/oauth/callback/ibkr"
    ibkr_use_gateway: bool = False  # Use local gateway vs web API
    
    # Webull
    webull_client_id: str = ""
    webull_client_secret: str = ""
    webull_redirect_uri: str = "https://optix.app/oauth/callback/webull"
    
    # Security
    token_encryption_key: str = ""  # 32-byte base64 encoded key
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # OAuth settings
    oauth_state_ttl_minutes: int = 10
    token_refresh_buffer_minutes: int = 5
    
    # Sync settings
    sync_interval_minutes: int = 15
    position_sync_timeout_seconds: int = 30
    
    # Database
    database_url: str = "postgresql://localhost/optix"
    
    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False


# Global settings instance
settings = BrokerageSettings()
