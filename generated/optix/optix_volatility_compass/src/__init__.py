"""
Volatility Compass - Comprehensive Implied Volatility Analytics
For OPTIX Trading Platform

Main exports:
- VolatilityCompassAPI: Primary interface for all functionality
- Models: Data structures for inputs and outputs
"""

from .api import VolatilityCompassAPI
from .models import (
    VolatilityMetrics,
    VolatilitySkew,
    VolatilityTermStructure,
    VolatilitySurface,
    VolatilityStrategy,
    VolatilityAlert,
    VolatilityCompassReport,
    WatchlistVolatilityAnalysis,
    VolatilityCondition,
    StrategyType
)

__version__ = "1.0.0"
__author__ = "OPTIX Development Team"

__all__ = [
    # Main API
    "VolatilityCompassAPI",
    
    # Data Models
    "VolatilityMetrics",
    "VolatilitySkew",
    "VolatilityTermStructure",
    "VolatilitySurface",
    "VolatilityStrategy",
    "VolatilityAlert",
    "VolatilityCompassReport",
    "WatchlistVolatilityAnalysis",
    
    # Enums
    "VolatilityCondition",
    "StrategyType",
    
    # Version
    "__version__",
]
