"""
FastAPI API layer for the Generative UI Service.
"""

from .app import create_app, app
from .router import router

__all__ = [
    "create_app",
    "app",
    "router",
]
