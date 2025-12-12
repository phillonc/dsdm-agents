"""
Configuration settings for the Flask Todo application.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent


class Config:
    """Base configuration class."""
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{BASE_DIR / "instance" / "todos.db"}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # WTForms
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Override with production secret key (must be set)
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """
    Get configuration based on environment.
    
    Args:
        env (str): Environment name ('development', 'testing', 'production')
        
    Returns:
        Config: Configuration class
    """
    env = env or os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
