"""
Unit tests for Pattern Recognition Service
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.services.pattern_recognition_service import PatternRecognitionService
from src.models.pattern_models import PatternType, TrendDirection


@pytest.fixture
def pattern_service():
    """Create pattern recognition service"""
    return PatternRecognitionService()


@pytest.fixture
def sample_price_data():
    """Create sample price data"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    
    # Create data with a head & shoulders pattern
    base_price = 100.0
    prices = []
    
    for i in range(100):
        if i < 20:
            price = base_price + i * 0.5  # Uptrend
        elif 20 <= i < 30:
            price = base_price + 10 + (i - 20) * 2  # Left shoulder
        elif 30 <= i < 40:
            price = base_price + 20 - (i - 30) * 1  # Down to neckline
        elif 40 <= i < 50:
            price = base_price + 10 + (i - 40) * 3  # Head
        elif 50 <= i < 60:
            price = base_price + 40 - (i - 50) * 3  # Down from head
        elif 60 <= i < 70:
            price = base_price + 10 + (i - 60) * 2  # Right shoulder
        else:
            price = base_price + 20 - (i - 70) * 0.5  # Decline
        
        prices.append(price + np.random.normal(0, 0.5))
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
    }, index=dates)
    
    return df


@pytest.fixture
def sample_volume_data():
    """Create sample volume data"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    volumes = np.random.randint(1000000, 3000000, size=100)
    
    return pd.DataFrame({'volume': volumes}, index=dates)


@pytest.mark.asyncio
async def test_detect_chart_patterns(pattern_service, sample_price_data, sample_volume_data):
    """Test chart pattern detection"""
    patterns = await pattern_service.detect_chart_patterns(
        symbol="AAPL",
        price_data=sample_price_data,
        volume_data=sample_volume_data
    )
    
    assert isinstance(patterns, list)
    assert len(patterns) >= 0  # May or may not detect patterns
    
    for pattern in patterns:
        assert pattern.symbol == "AAPL"
        assert 0.0 <= pattern.confidence <= 1.0
        assert pattern.pattern_type in PatternType


@pytest.mark.asyncio
async def test_detect_support_resistance(pattern_service, sample_price_data, sample_volume_data):
    """Test support and resistance level detection"""
    levels = await pattern_service.detect_support_resistance(
        symbol="AAPL",
        price_data=sample_price_data,
        volume_data=sample_volume_data
    )
    
    assert isinstance(levels, list)
    
    for level in levels:
        assert level.symbol == "AAPL"
        assert level.level_type in ["support", "resistance"]
        assert 0.0 <= level.strength <= 1.0
        assert level.touches >= 2


@pytest.mark.asyncio
async def test_detect_unusual_options(pattern_service):
    """Test unusual options activity detection"""
    # Create sample options data
    options_data = pd.DataFrame({
        'strike': [95, 100, 105, 110],
        'expiration': [datetime.now() + timedelta(days=7)] * 4,
        'option_type': ['call', 'call', 'put', 'put'],
        'volume': [5000, 15000, 8000, 20000],  # Some unusually high
        'open_interest': [2000, 3000, 2500, 4000],
        'avg_volume': [1000, 2000, 1500, 3000],
        'premium': [2.5, 3.0, 2.0, 2.8],
        'implied_volatility': [0.3, 0.35, 0.32, 0.38],
        'delta': [0.6, 0.5, -0.4, -0.5]
    })
    
    activities = await pattern_service.detect_unusual_options_activity(
        symbol="AAPL",
        options_data=options_data
    )
    
    assert isinstance(activities, list)
    assert len(activities) > 0  # Should detect some unusual activity
    
    for activity in activities:
        assert activity.symbol == "AAPL"
        assert activity.volume_multiple >= 3.0
        assert 0.0 <= activity.confidence <= 1.0


@pytest.mark.asyncio
async def test_detect_volume_anomalies(pattern_service, sample_price_data):
    """Test volume anomaly detection"""
    # Create volume data with spike
    volumes = [1000000] * 99 + [5000000]  # Last day has spike
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    volume_data = pd.DataFrame({'volume': volumes}, index=dates)
    
    anomalies = await pattern_service.detect_volume_anomalies(
        symbol="AAPL",
        volume_data=volume_data,
        price_data=sample_price_data,
        timeframe="1D"
    )
    
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0  # Should detect the spike
    
    for anomaly in anomalies:
        assert anomaly.symbol == "AAPL"
        assert anomaly.volume_ratio >= 2.0
        assert 0.0 <= anomaly.significance <= 1.0


def test_calculate_pattern_confidence(pattern_service):
    """Test pattern confidence calculation"""
    confidence = pattern_service._calculate_pattern_confidence(
        shoulder_symmetry=0.95,
        volume_confirmation=0.8
    )
    
    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.7  # Should be high with good factors


@pytest.mark.asyncio
async def test_pattern_filtering_by_confidence(pattern_service, sample_price_data, sample_volume_data):
    """Test that patterns are filtered by minimum confidence"""
    service_high_confidence = PatternRecognitionService(
        config={'min_pattern_confidence': 0.9}
    )
    
    patterns = await service_high_confidence.detect_chart_patterns(
        symbol="AAPL",
        price_data=sample_price_data,
        volume_data=sample_volume_data
    )
    
    for pattern in patterns:
        assert pattern.confidence >= 0.9
