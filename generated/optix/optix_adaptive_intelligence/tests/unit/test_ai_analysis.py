"""
Unit tests for AI Analysis Service
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from src.services.ai_analysis_service import AIAnalysisService
from src.models.analysis_models import (
    SignalType, VolatilityRegime, SentimentScore, MarketRegime
)


@pytest.fixture
def analysis_service():
    """Create AI analysis service"""
    return AIAnalysisService()


@pytest.fixture
def sample_price_data():
    """Create sample price data"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * (1 + returns).cumprod()
    
    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.005, 100)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, 100))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, 100))),
        'close': prices,
        'volume': np.random.randint(1000000, 3000000, size=100)
    }, index=dates)
    
    return df


@pytest.mark.asyncio
async def test_generate_prediction_signals(analysis_service, sample_price_data):
    """Test price prediction signal generation"""
    signals = await analysis_service.generate_prediction_signals(
        symbol="AAPL",
        price_data=sample_price_data,
        time_horizon="1D"
    )
    
    assert isinstance(signals, list)
    
    for signal in signals:
        assert signal.symbol == "AAPL"
        assert signal.signal_type in SignalType
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.current_price > 0
        assert signal.predicted_price > 0
        assert 'min' in signal.prediction_range
        assert 'max' in signal.prediction_range


@pytest.mark.asyncio
async def test_forecast_volatility(analysis_service, sample_price_data):
    """Test volatility forecasting"""
    forecast = await analysis_service.forecast_volatility(
        symbol="AAPL",
        price_data=sample_price_data,
        forecast_horizon="1W"
    )
    
    assert forecast.symbol == "AAPL"
    assert forecast.current_volatility >= 0
    assert forecast.forecasted_volatility >= 0
    assert forecast.volatility_regime in VolatilityRegime
    assert 0.0 <= forecast.regime_change_probability <= 1.0
    assert 0.0 <= forecast.historical_percentile <= 100.0
    assert forecast.ewma_forecast is not None
    assert forecast.garch_forecast is not None


@pytest.mark.asyncio
async def test_analyze_sentiment(analysis_service):
    """Test sentiment analysis"""
    market_data = {
        'rsi': 60.0,
        'macd': 0.5,
        'breadth': {
            'advance_decline_ratio': 1.5,
            'new_highs_lows': 100
        }
    }
    
    sentiment = await analysis_service.analyze_sentiment(
        symbol="AAPL",
        market_data=market_data
    )
    
    assert sentiment.symbol == "AAPL"
    assert sentiment.overall_sentiment in SentimentScore
    assert -1.0 <= sentiment.sentiment_score <= 1.0
    assert 0.0 <= sentiment.confidence <= 1.0
    assert isinstance(sentiment.key_drivers, list)


@pytest.mark.asyncio
async def test_analyze_market_context(analysis_service, sample_price_data):
    """Test market context analysis"""
    market_data = {
        'spy_correlation': 0.75,
        'beta': 1.2,
        'sector_performance': {'technology': 0.05},
        'ad_ratio': 1.5,
        'nh_nl': 100,
        'vix': 18.5
    }
    
    context = await analysis_service.analyze_market_context(
        symbol="AAPL",
        price_data=sample_price_data,
        market_data=market_data
    )
    
    assert context.symbol == "AAPL"
    assert context.market_regime in MarketRegime
    assert 0.0 <= context.regime_confidence <= 1.0
    assert 0.0 <= context.trend_strength <= 1.0
    assert -1.0 <= context.correlation_to_spy <= 1.0


@pytest.mark.asyncio
async def test_feature_preparation(analysis_service, sample_price_data):
    """Test feature preparation for ML models"""
    features = await analysis_service._prepare_features(
        sample_price_data,
        None
    )
    
    assert isinstance(features, pd.DataFrame)
    assert len(features) > 0
    assert 'returns' in features.columns
    assert 'volatility_20' in features.columns
    assert 'rsi' in features.columns


def test_classify_signal(analysis_service):
    """Test signal classification"""
    # Test strong buy signal
    signal_type, strength, confidence = analysis_service._classify_signal(0.06, 2.0)
    assert signal_type == SignalType.STRONG_BUY
    
    # Test sell signal
    signal_type, strength, confidence = analysis_service._classify_signal(-0.03, 2.0)
    assert signal_type == SignalType.SELL
    
    # Test hold signal
    signal_type, strength, confidence = analysis_service._classify_signal(0.01, 2.0)
    assert signal_type == SignalType.HOLD


def test_classify_volatility_regime(analysis_service):
    """Test volatility regime classification"""
    returns = pd.Series(np.random.normal(0, 0.02, 100))
    
    regime, prob = analysis_service._classify_volatility_regime(
        current_vol=0.20,
        forecasted_vol=0.35,
        returns=returns
    )
    
    assert regime in VolatilityRegime
    assert 0.0 <= prob <= 1.0


def test_classify_sentiment(analysis_service):
    """Test sentiment classification"""
    # Very bullish
    sentiment = analysis_service._classify_sentiment(0.7)
    assert sentiment == SentimentScore.VERY_BULLISH
    
    # Bearish
    sentiment = analysis_service._classify_sentiment(-0.3)
    assert sentiment == SentimentScore.BEARISH
    
    # Neutral
    sentiment = analysis_service._classify_sentiment(0.1)
    assert sentiment == SentimentScore.NEUTRAL
