"""
API endpoints for the Adaptive Intelligence Engine
"""
from .patterns import router as patterns_router
from .analysis import router as analysis_router
from .personalization import router as personalization_router
from .alerts import router as alerts_router

__all__ = [
    'patterns_router',
    'analysis_router',
    'personalization_router',
    'alerts_router',
]
