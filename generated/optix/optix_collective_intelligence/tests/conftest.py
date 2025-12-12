"""
Pytest configuration and fixtures.
"""

import pytest


@pytest.fixture(autouse=True)
def reset_state():
    """Reset state before each test."""
    yield
    # Cleanup code here if needed
