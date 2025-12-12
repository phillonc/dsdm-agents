"""
Custom exceptions for the Collective Intelligence Network.
"""


class CollectiveIntelligenceError(Exception):
    """Base exception for all Collective Intelligence errors."""
    pass


class ValidationError(CollectiveIntelligenceError):
    """Raised when input validation fails."""
    pass


class NotFoundError(CollectiveIntelligenceError):
    """Raised when a requested resource is not found."""
    pass


class DuplicateError(CollectiveIntelligenceError):
    """Raised when attempting to create a duplicate resource."""
    pass


class PermissionError(CollectiveIntelligenceError):
    """Raised when a user lacks permission for an operation."""
    pass


class CopyTradingError(CollectiveIntelligenceError):
    """Raised when copy trading operations fail."""
    pass


class PerformanceCalculationError(CollectiveIntelligenceError):
    """Raised when performance metric calculation fails."""
    pass
