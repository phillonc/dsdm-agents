"""
Pytest configuration and shared fixtures
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.option import Option, OptionType, OptionPosition


@pytest.fixture
def sample_call_option():
    """Reusable call option fixture"""
    return Option(
        symbol="SAMPLE_C100",
        underlying_symbol="SAMPLE",
        option_type=OptionType.CALL,
        strike_price=Decimal('100'),
        expiration_date=datetime.utcnow() + timedelta(days=90),
        quantity=1,
        position=OptionPosition.LONG,
        premium=Decimal('5.00'),
        underlying_price=Decimal('100'),
        implied_volatility=Decimal('0.25')
    )


@pytest.fixture
def sample_put_option():
    """Reusable put option fixture"""
    return Option(
        symbol="SAMPLE_P100",
        underlying_symbol="SAMPLE",
        option_type=OptionType.PUT,
        strike_price=Decimal('100'),
        expiration_date=datetime.utcnow() + timedelta(days=90),
        quantity=1,
        position=OptionPosition.LONG,
        premium=Decimal('4.50'),
        underlying_price=Decimal('100'),
        implied_volatility=Decimal('0.25')
    )


@pytest.fixture
def common_option_params():
    """Common parameters for creating options"""
    return {
        'underlying_symbol': 'TEST',
        'underlying_price': Decimal('100'),
        'expiration_date': datetime.utcnow() + timedelta(days=90),
        'implied_volatility': Decimal('0.25'),
        'quantity': 1
    }


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
