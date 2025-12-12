"""
Unit tests for Alert Service
"""
import pytest
from datetime import datetime, timedelta

from src.services.alert_service import AlertService
from src.models.alert_models import (
    Alert, AlertConfig, AlertType, AlertSeverity, AlertChannel, AlertStatus
)
from src.models.pattern_models import ChartPattern, PatternType, TrendDirection
from src.models.analysis_models import PredictionSignal, SignalType, SignalStrength


@pytest.fixture
def alert_service():
    """Create alert service"""
    return AlertService()


@pytest.fixture
def sample_alert_config():
    """Create sample alert configuration"""
    return AlertConfig(
        config_id="cfg_123",
        user_id="user_123",
        enabled=True,
        alert_type=AlertType.PATTERN_DETECTED,
        min_confidence=0.7,
        min_severity=AlertSeverity.MEDIUM,
        preferred_channels=[AlertChannel.IN_APP, AlertChannel.PUSH_NOTIFICATION],
        max_alerts_per_day=20,
        deduplication_window=3600
    )


@pytest.fixture
def sample_pattern():
    """Create sample chart pattern"""
    return ChartPattern(
        pattern_id="pat_123",
        symbol="AAPL",
        pattern_type=PatternType.HEAD_SHOULDERS,
        confidence=0.85,
        start_time=datetime.utcnow() - timedelta(days=10),
        end_time=datetime.utcnow(),
        trend_direction=TrendDirection.BEARISH,
        price_target=175.00,
        resistance_level=180.00,
        support_level=175.00,
        volume_confirmation=True
    )


@pytest.fixture
def sample_signal():
    """Create sample prediction signal"""
    return PredictionSignal(
        signal_id="sig_123",
        symbol="AAPL",
        signal_type=SignalType.BUY,
        signal_strength=SignalStrength.STRONG,
        confidence=0.82,
        current_price=178.50,
        predicted_price=185.00,
        time_horizon="1W",
        prediction_range={"min": 182.0, "max": 188.0, "std_dev": 2.5},
        model_name="RandomForest"
    )


@pytest.mark.asyncio
async def test_generate_pattern_alert(
    alert_service,
    sample_pattern,
    sample_alert_config
):
    """Test generating alert from pattern"""
    alert = await alert_service.generate_pattern_alert(
        user_id="user_123",
        pattern=sample_pattern,
        alert_config=sample_alert_config
    )
    
    assert alert is not None
    assert alert.user_id == "user_123"
    assert alert.alert_type == AlertType.PATTERN_DETECTED
    assert alert.symbol == "AAPL"
    assert alert.severity in AlertSeverity
    assert len(alert.channels) > 0


@pytest.mark.asyncio
async def test_generate_signal_alert(
    alert_service,
    sample_signal,
    sample_alert_config
):
    """Test generating alert from signal"""
    alert = await alert_service.generate_signal_alert(
        user_id="user_123",
        signal=sample_signal,
        alert_config=sample_alert_config
    )
    
    assert alert is not None
    assert alert.user_id == "user_123"
    assert alert.alert_type == AlertType.PREDICTION_SIGNAL
    assert alert.symbol == "AAPL"
    assert alert.actionable is True


@pytest.mark.asyncio
async def test_deliver_alert(alert_service):
    """Test alert delivery"""
    alert = Alert(
        alert_id="alert_123",
        user_id="user_123",
        alert_type=AlertType.CUSTOM,
        severity=AlertSeverity.MEDIUM,
        title="Test Alert",
        message="This is a test alert",
        channels=[AlertChannel.IN_APP],
        actionable=False,
        priority_score=0.7
    )
    
    logs = await alert_service.deliver_alert(alert)
    
    assert isinstance(logs, list)
    assert len(logs) > 0
    
    for log in logs:
        assert log.alert_id == "alert_123"
        assert log.channel == AlertChannel.IN_APP
        assert log.status in ["success", "failed"]


@pytest.mark.asyncio
async def test_alert_deduplication(
    alert_service,
    sample_pattern,
    sample_alert_config
):
    """Test alert deduplication"""
    # Generate first alert
    alert1 = await alert_service.generate_pattern_alert(
        user_id="user_123",
        pattern=sample_pattern,
        alert_config=sample_alert_config
    )
    
    assert alert1 is not None
    
    # Try to generate duplicate alert
    alert2 = await alert_service.generate_pattern_alert(
        user_id="user_123",
        pattern=sample_pattern,
        alert_config=sample_alert_config
    )
    
    assert alert2 is None  # Should be deduplicated


@pytest.mark.asyncio
async def test_confidence_filtering(
    alert_service,
    sample_signal
):
    """Test filtering by confidence threshold"""
    config = AlertConfig(
        config_id="cfg_123",
        user_id="user_123",
        enabled=True,
        alert_type=AlertType.PREDICTION_SIGNAL,
        min_confidence=0.9,  # Higher than signal confidence
        min_severity=AlertSeverity.LOW,
        preferred_channels=[AlertChannel.IN_APP]
    )
    
    alert = await alert_service.generate_signal_alert(
        user_id="user_123",
        signal=sample_signal,
        alert_config=config
    )
    
    assert alert is None  # Should be filtered out


@pytest.mark.asyncio
async def test_severity_filtering(
    alert_service,
    sample_signal,
    sample_alert_config
):
    """Test filtering by minimum severity"""
    # Create low confidence signal
    low_signal = PredictionSignal(
        signal_id="sig_low",
        symbol="AAPL",
        signal_type=SignalType.HOLD,
        signal_strength=SignalStrength.WEAK,
        confidence=0.71,
        current_price=178.50,
        predicted_price=179.00,
        time_horizon="1D",
        prediction_range={"min": 178.0, "max": 180.0, "std_dev": 1.0},
        model_name="RandomForest"
    )
    
    config = AlertConfig(
        config_id="cfg_123",
        user_id="user_123",
        enabled=True,
        alert_type=AlertType.PREDICTION_SIGNAL,
        min_confidence=0.7,
        min_severity=AlertSeverity.HIGH,  # High threshold
        preferred_channels=[AlertChannel.IN_APP]
    )
    
    alert = await alert_service.generate_signal_alert(
        user_id="user_123",
        signal=low_signal,
        alert_config=config
    )
    
    # May or may not pass depending on severity calculation
    if alert is not None:
        assert alert.severity == AlertSeverity.HIGH or alert.severity == AlertSeverity.CRITICAL


def test_calculate_pattern_severity(alert_service, sample_pattern):
    """Test pattern severity calculation"""
    severity = alert_service._calculate_pattern_severity(sample_pattern)
    
    assert severity in AlertSeverity
    # High confidence should result in higher severity
    assert severity in [AlertSeverity.MEDIUM, AlertSeverity.HIGH]


def test_calculate_signal_severity(alert_service, sample_signal):
    """Test signal severity calculation"""
    severity = alert_service._calculate_signal_severity(sample_signal)
    
    assert severity in AlertSeverity
    # Strong signal should result in medium or high severity
    assert severity in [AlertSeverity.MEDIUM, AlertSeverity.HIGH]


def test_create_pattern_alert_message(alert_service, sample_pattern):
    """Test pattern alert message creation"""
    title, message = alert_service._create_pattern_alert_message(sample_pattern)
    
    assert isinstance(title, str)
    assert isinstance(message, str)
    assert "AAPL" in title
    assert "Head Shoulders" in title
    assert "confidence" in message.lower()


def test_create_signal_alert_message(alert_service, sample_signal):
    """Test signal alert message creation"""
    title, message = alert_service._create_signal_alert_message(sample_signal)
    
    assert isinstance(title, str)
    assert isinstance(message, str)
    assert "AAPL" in title
    assert "Buy" in title
    assert "confidence" in message.lower()


@pytest.mark.asyncio
async def test_quiet_hours(alert_service):
    """Test quiet hours functionality"""
    config = AlertConfig(
        config_id="cfg_123",
        user_id="user_123",
        enabled=True,
        alert_type=AlertType.CUSTOM,
        quiet_hours={'start_hour': 22, 'end_hour': 8}
    )
    
    is_quiet = alert_service._is_quiet_hours(config)
    
    assert isinstance(is_quiet, bool)


def test_filter_and_prioritize_alerts(alert_service):
    """Test alert filtering and prioritization"""
    alerts = [
        Alert(
            alert_id=f"alert_{i}",
            user_id="user_123",
            alert_type=AlertType.CUSTOM,
            severity=AlertSeverity.HIGH if i % 2 == 0 else AlertSeverity.LOW,
            title=f"Alert {i}",
            message=f"Message {i}",
            channels=[AlertChannel.IN_APP],
            actionable=False,
            priority_score=0.5 + (i * 0.1)
        )
        for i in range(10)
    ]
    
    config = AlertConfig(
        config_id="cfg_123",
        user_id="user_123",
        enabled=True,
        alert_type=AlertType.CUSTOM
    )
    
    filtered = alert_service._filter_and_prioritize_alerts(alerts, config)
    
    assert isinstance(filtered, list)
    assert len(filtered) <= len(alerts)
    
    # Check that alerts are sorted by priority
    if len(filtered) > 1:
        for i in range(len(filtered) - 1):
            severity_level_current = alert_service._severity_level(filtered[i].severity)
            severity_level_next = alert_service._severity_level(filtered[i + 1].severity)
            assert severity_level_current >= severity_level_next


def test_evaluate_condition(alert_service):
    """Test condition evaluation"""
    assert alert_service._evaluate_condition(10.0, '>', 5.0) is True
    assert alert_service._evaluate_condition(10.0, '<', 5.0) is False
    assert alert_service._evaluate_condition(10.0, '==', 10.0) is True
    assert alert_service._evaluate_condition(10.0, '>=', 10.0) is True
    assert alert_service._evaluate_condition(10.0, '<=', 15.0) is True
    assert alert_service._evaluate_condition(10.0, '!=', 5.0) is True
