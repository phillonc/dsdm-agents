"""
Unit tests for Personalization Service
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.services.personalization_service import PersonalizationService
from src.models.user_models import (
    UserProfile, TradingStyle, RiskTolerance, StrategyPreference,
    InsightType
)
from src.models.analysis_models import (
    PredictionSignal, SignalType, SignalStrength
)


@pytest.fixture
def personalization_service():
    """Create personalization service"""
    return PersonalizationService()


@pytest.fixture
def sample_user_profile():
    """Create sample user profile"""
    return UserProfile(
        user_id="user_123",
        trading_style=TradingStyle.SWING_TRADER,
        risk_tolerance=RiskTolerance.MODERATE,
        preferred_symbols=["AAPL", "MSFT", "GOOGL"],
        preferred_timeframes=["1D", "4H"],
        preferred_strategies=[StrategyPreference.MOMENTUM],
        experience_level="intermediate"
    )


@pytest.fixture
def sample_trade_history():
    """Create sample trade history"""
    num_trades = 50
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    strategies = ["momentum", "mean_reversion", "breakout"]
    
    trades = []
    for i in range(num_trades):
        entry_time = datetime.utcnow() - timedelta(days=np.random.randint(0, 90))
        exit_time = entry_time + timedelta(hours=np.random.randint(12, 72))
        
        profit = np.random.normal(0.02, 0.05)
        
        trades.append({
            'user_id': 'user_123',
            'symbol': np.random.choice(symbols),
            'strategy': np.random.choice(strategies),
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': 100.0,
            'exit_price': 100.0 * (1 + profit),
            'position_size': np.random.uniform(1000, 5000),
            'profit': profit * 100,
            'entry_conditions': ['rsi_oversold'],
            'exit_reason': 'take_profit',
            'account_size': 50000
        })
    
    return pd.DataFrame(trades)


@pytest.mark.asyncio
async def test_learn_trading_patterns(
    personalization_service,
    sample_user_profile,
    sample_trade_history
):
    """Test learning trading patterns"""
    patterns = await personalization_service.learn_trading_patterns(
        user_id="user_123",
        trade_history=sample_trade_history,
        user_profile=sample_user_profile
    )
    
    assert isinstance(patterns, list)
    
    for pattern in patterns:
        assert pattern.user_id == "user_123"
        assert 0.0 <= pattern.success_rate <= 1.0
        assert 0.0 <= pattern.confidence <= 1.0
        assert pattern.frequency >= personalization_service.min_sample_size


@pytest.mark.asyncio
async def test_generate_personalized_insights(
    personalization_service,
    sample_user_profile
):
    """Test generating personalized insights"""
    # Create sample signals
    signals = [
        PredictionSignal(
            signal_id="sig_1",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            signal_strength=SignalStrength.STRONG,
            confidence=0.85,
            current_price=178.50,
            predicted_price=185.00,
            time_horizon="1D",
            prediction_range={"min": 182.0, "max": 188.0, "std_dev": 2.5},
            model_name="RandomForest"
        )
    ]
    
    insights = await personalization_service.generate_personalized_insights(
        user_id="user_123",
        user_profile=sample_user_profile,
        trading_patterns=[],
        current_signals=signals,
        detected_patterns=[]
    )
    
    assert isinstance(insights, list)
    
    for insight in insights:
        assert insight.user_id == "user_123"
        assert insight.insight_type in InsightType
        assert 0.0 <= insight.relevance_score <= 1.0
        assert 0.0 <= insight.confidence <= 1.0


@pytest.mark.asyncio
async def test_calculate_relevance_score(
    personalization_service,
    sample_user_profile
):
    """Test relevance score calculation"""
    signal = PredictionSignal(
        signal_id="sig_1",
        symbol="AAPL",  # In preferred symbols
        signal_type=SignalType.BUY,
        signal_strength=SignalStrength.STRONG,
        confidence=0.85,
        current_price=178.50,
        predicted_price=185.00,
        time_horizon="1D",  # Matches preferred timeframe
        prediction_range={"min": 182.0, "max": 188.0, "std_dev": 2.5},
        model_name="RandomForest"
    )
    
    relevance = await personalization_service.calculate_relevance_score(
        user_profile=sample_user_profile,
        signal=signal
    )
    
    assert 0.0 <= relevance <= 1.0
    assert relevance > 0.5  # Should be relevant


@pytest.mark.asyncio
async def test_update_user_profile(
    personalization_service,
    sample_user_profile,
    sample_trade_history
):
    """Test updating user profile"""
    patterns = await personalization_service.learn_trading_patterns(
        user_id="user_123",
        trade_history=sample_trade_history,
        user_profile=sample_user_profile
    )
    
    updated_profile = await personalization_service.update_user_profile(
        user_id="user_123",
        user_profile=sample_user_profile,
        recent_trades=sample_trade_history,
        trading_patterns=patterns
    )
    
    assert updated_profile.user_id == "user_123"
    assert updated_profile.updated_at > sample_user_profile.updated_at
    assert len(updated_profile.preferred_symbols) > 0


def test_match_time_horizon(personalization_service):
    """Test time horizon matching"""
    # Day trader should match short timeframes
    match = personalization_service._match_time_horizon(
        "1H",
        TradingStyle.DAY_TRADER
    )
    assert match > 0.5
    
    # Position trader should match longer timeframes
    match = personalization_service._match_time_horizon(
        "1M",
        TradingStyle.POSITION_TRADER
    )
    assert match > 0.7


def test_match_risk_tolerance(personalization_service):
    """Test risk tolerance matching"""
    # Aggressive trader should match strong signals
    match = personalization_service._match_risk_tolerance(
        "very_strong",
        RiskTolerance.AGGRESSIVE
    )
    assert match > 0.8
    
    # Conservative trader prefers moderate signals
    match = personalization_service._match_risk_tolerance(
        "moderate",
        RiskTolerance.CONSERVATIVE
    )
    assert match > 0.8


@pytest.mark.asyncio
async def test_analyze_entry_patterns(
    personalization_service,
    sample_trade_history
):
    """Test entry pattern analysis"""
    patterns = await personalization_service._analyze_entry_patterns(
        user_id="user_123",
        trade_history=sample_trade_history
    )
    
    assert isinstance(patterns, list)
    
    for pattern in patterns:
        assert pattern.pattern_type.startswith("entry_")
        assert len(pattern.common_entry_conditions) > 0


@pytest.mark.asyncio
async def test_generate_opportunity_insights(
    personalization_service,
    sample_user_profile
):
    """Test opportunity insight generation"""
    signals = [
        PredictionSignal(
            signal_id="sig_1",
            symbol="AAPL",
            signal_type=SignalType.BUY,
            signal_strength=SignalStrength.STRONG,
            confidence=0.85,
            current_price=178.50,
            predicted_price=185.00,
            time_horizon="1D",
            prediction_range={"min": 182.0, "max": 188.0, "std_dev": 2.5},
            model_name="RandomForest"
        )
    ]
    
    insights = await personalization_service._generate_opportunity_insights(
        user_id="user_123",
        user_profile=sample_user_profile,
        current_signals=signals,
        detected_patterns=[]
    )
    
    assert isinstance(insights, list)
    
    for insight in insights:
        assert insight.insight_type == InsightType.OPPORTUNITY
        assert insight.actionable is True
        assert len(insight.action_items) > 0
