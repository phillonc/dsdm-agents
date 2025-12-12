"""Pytest configuration and shared fixtures."""
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database_url() -> str:
    """Mock database URL for testing."""
    return "postgresql+asyncpg://test:test@localhost:5432/test_gex_db"
