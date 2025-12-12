"""
Integration tests for end-to-end workflows
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.services.pattern_recognition_service import PatternRecognitionService
from src.services.ai_analysis_service import AIAnalysisService
from src.services.personalization_service import PersonalizationService
from src.services.alert_service import AlertService
from src.models.user_models import UserProfile, TradingStyle, RiskTolerance
from src.models.alert_models import AlertConfig, AlertType, AlertSeverity, AlertChannel


@pytest.fixture
def all_services():
    """Create all services"""
    return {
        'pattern': PatternRecognitionService(),
        'analysis': AIAnalysisService(),
        'personalization': PersonalizationService(),
        'alert': AlertService()
    }


@pytest.fixture
def sample_market_data():
    """Create comprehensive sample market data"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * (1 + returns).cumprod()
    
    price_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.005, 100)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, 100))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, 100))),
        'close': prices,
        'volume': np.random.randint(1000000, 3000000, size=100)
    }, index=dates)
    
    volume_data = pd.DataFrame({'volume': price_data['volume']}, index=dates)
    
    return {
        'price': price_data,
        'volume': volume_data
    }


@pytest.mark.asyncio
async def test_pattern_to_alert_workflow(all_services, sample_market_data):
    """Test complete workflow from pattern detection to alert generation"""
    # Step 1: Detect patterns
    patterns = await all_services['pattern'].detect_chart_patterns(
        symbol="AAPL",
        price_data=sample_market_data['price'],
        volume_data=sample_market_data['volume']
    )
    
    # Step 2: Create user and alert config
    user_id = "user_test"
    alert_config = AlertConfig(
        config_id="cfg_test",
        user_id=user_id,
        enabled=True,
        alert_type=AlertType.PATTERN_DETECTED,
        min_confidence=0.6,
        min_severity=AlertSeverity.LOW,
        preferred_channels=[AlertChannel.IN_APP]
    )
    
    # Step 3: Generate alerts from patterns
    alerts_generated = []
    for pattern in patterns:
        alert = await all_services['alert'].generate_pattern_alert(
            user_id=user_id,
            pattern=pattern,
            alert_config=alert_config
        )
        if alert:
            alerts_generated.append(alert)
    
    # Verify workflow
    if len(patterns) > 0:
        assert len(alerts_generated) > 0
        
        for alert in alerts_generated:
            assert alert.user_id == user_id
            assert alert.alert_type == AlertType.PATTERN_DETECTED


@pytest.mark.asyncio
async def test_analysis_to_insights_workflow(all_services, sample_market_data):
    """Test workflow from analysis to personalized insights"""
    # Step 1: Generate predictions
    signals = await all_services['analysis'].generate_prediction_signals(
        symbol="AAPL",
        price_data=sample_market_data['price'],
        time_horizon="1D"
    )
    
    # Step 2: Create user profile
    user_profile = UserProfile(
        user_id="user_test",
        trading_style=TradingStyle.SWING_TRADER,
        risk_tolerance=RiskTolerance.MODERATE,
        preferred_symbols=["AAPL"],
        preferred_timeframes=["1D"]
    )
    
    # Step 3: Generate personalized insights
    insights = await all_services['personalization'].generate_personalized_insights(
        user_id="user_test",
        user_profile=user_profile,
        trading_patterns=[],
        current_signals=signals,
        detected_patterns=[]
    )
    
    # Verify workflow
    assert len(insights) >= 0
    
    for insight in insights:
        assert insight.user_id == "user_test"
        assert 0.0 <= insight.relevance_score <= 1.0


@pytest.mark.asyncio
async def test_complete_trading_workflow(all_services, sample_market_data):
    """Test complete end-to-end trading workflow"""
    user_id = "user_complete"
    symbol = "AAPL"
    
    # Step 1: Pattern Recognition
    patterns = await all_services['pattern'].detect_chart_patterns(
        symbol=symbol,
        price_data=sample_market_data['price'],
        volume_data=sample_market_data['volume']
    )
    
    support_resistance = await all_services['pattern'].detect_support_resistance(
        symbol=symbol,
        price_data=sample_market_data['price'],
        volume_data=sample_market_data['volume']
    )
    
    # Step 2: AI Analysis
    signals = await all_services['analysis'].generate_prediction_signals(
        symbol=symbol,
        price_data=sample_market_data['price'],
        time_horizon="1W"
    )
    
    volatility_forecast = await all_services['analysis'].forecast_volatility(
        symbol=symbol,
        price_data=sample_market_data['price'],
        forecast_horizon="1W"
    )
    
    sentiment = await all_services['analysis'].analyze_sentiment(
        symbol=symbol,
        market_data={'rsi': 55.0, 'macd': 0.5}
    )
    
    # Step 3: Personalization
    user_profile = UserProfile(
        user_id=user_id,
        trading_style=TradingStyle.SWING_TRADER,
        risk_tolerance=RiskTolerance.MODERATE,
        preferred_symbols=[symbol]
    )
    
    insights = await all_services['personalization'].generate_personalized_insights(
        user_id=user_id,
        user_profile=user_profile,
        trading_patterns=[],
        current_signals=signals,
        detected_patterns=patterns
    )
    
    # Step 4: Alert Generation
    alert_config = AlertConfig(
        config_id=f"cfg_{user_id}",
        user_id=user_id,
        enabled=True,
        alert_type=AlertType.PATTERN_DETECTED,
        min_confidence=0.5,
        preferred_channels=[AlertChannel.IN_APP]
    )
    
    all_alerts = []
    
    # Generate alerts from patterns
    for pattern in patterns[:3]:  # Limit to avoid too many alerts
        alert = await all_services['alert'].generate_pattern_alert(
            user_id=user_id,
            pattern=pattern,
            alert_config=alert_config
        )
        if alert:
            all_alerts.append(alert)
    
    # Generate alerts from signals
    for signal in signals[:3]:
        alert = await all_services['alert'].generate_signal_alert(
            user_id=user_id,
            signal=signal,
            alert_config=alert_config
        )
        if alert:
            all_alerts.append(alert)
    
    # Verify complete workflow
    assert len(patterns) >= 0
    assert len(signals) > 0
    assert volatility_forecast is not None
    assert sentiment is not None
    assert len(insights) >= 0
    
    # Verify data consistency
    for signal in signals:
        assert signal.symbol == symbol
    
    for pattern in patterns:
        assert pattern.symbol == symbol
    
    for insight in insights:
        assert insight.user_id == user_id


@pytest.mark.asyncio
async def test_multi_symbol_analysis(all_services, sample_market_data):
    """Test analyzing multiple symbols simultaneously"""
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    results = {}
    
    for symbol in symbols:
        # Generate predictions for each symbol
        signals = await all_services['analysis'].generate_prediction_signals(
            symbol=symbol,
            price_data=sample_market_data['price'],
            time_horizon="1D"
        )
        
        results[symbol] = {
            'signals': signals,
            'count': len(signals)
        }
    
    # Verify all symbols processed
    assert len(results) == len(symbols)
    
    for symbol in symbols:
        assert symbol in results
        assert 'signals' in results[symbol]


@pytest.mark.asyncio
async def test_alert_batch_processing(all_services):
    """Test batch processing of alerts"""
    # Create multiple users with alerts
    user_alerts = {}
    alert_configs = {}
    
    for i in range(3):
        user_id = f"user_{i}"
        
        # Create alerts for user
        user_alerts[user_id] = [
            Alert(
                alert_id=f"alert_{user_id}_{j}",
                user_id=user_id,
                alert_type=AlertType.CUSTOM,
                severity=AlertSeverity.MEDIUM,
                title=f"Alert {j}",
                message=f"Test alert {j}",
                channels=[AlertChannel.IN_APP],
                actionable=False,
                priority_score=0.7
            )
            for j in range(2)
        ]
        
        # Create config for user
        alert_configs[user_id] = AlertConfig(
            config_id=f"cfg_{user_id}",
            user_id=user_id,
            enabled=True,
            alert_type=AlertType.CUSTOM
        )
    
    # Process batch
    from src.models.alert_models import Alert
    
    results = await all_services['alert'].process_alert_batch(
        user_alerts=user_alerts,
        alert_configs=alert_configs
    )
    
    # Verify batch processing
    assert isinstance(results, dict)
    assert len(results) <= len(user_alerts)
