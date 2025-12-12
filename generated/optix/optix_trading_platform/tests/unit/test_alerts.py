"""Unit tests for alert system."""
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

from src.models import (
    OptionsTrade, OrderType, TradeType,
    FlowPattern, PatternType, SmartMoneySignal,
    MarketMakerPosition, PositionBias,
    UnusualActivityAlert, AlertType, AlertSeverity,
)
from src.alerts import AlertManager, AlertDispatcher


class TestAlertManager(unittest.TestCase):
    """Test AlertManager."""
    
    def setUp(self):
        """Set up test manager."""
        self.manager = AlertManager(alert_retention_hours=1)
    
    def create_trade(
        self,
        size: int = 100,
        premium: Decimal = Decimal('5.50'),
    ) -> OptionsTrade:
        """Create a test trade."""
        return OptionsTrade(
            trade_id=f"TRADE_{datetime.now().timestamp()}",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=OrderType.CALL,
            strike=Decimal('150.00'),
            expiration=datetime(2025, 1, 17),
            premium=premium,
            size=size,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.SWEEP,
            exchange="CBOE",
            execution_side="ask",
            is_aggressive=True,
            underlying_price=Decimal('148.00'),
        )
    
    def test_create_sweep_alert(self):
        """Test sweep alert creation."""
        trades = [self.create_trade(size=50) for _ in range(4)]
        
        alert = self.manager.create_sweep_alert(trades, confidence=0.85)
        
        self.assertEqual(alert.alert_type, AlertType.UNUSUAL_SWEEP)
        self.assertEqual(len(alert.related_trade_ids), 4)
        self.assertEqual(alert.total_contracts, 200)
        self.assertGreater(alert.confidence_score, 0.8)
    
    def test_create_block_alert(self):
        """Test block alert creation."""
        trade = self.create_trade(size=500, premium=Decimal('10.00'))
        
        alert = self.manager.create_block_alert(trade, confidence=0.9)
        
        self.assertEqual(alert.alert_type, AlertType.LARGE_BLOCK)
        self.assertEqual(alert.total_contracts, 500)
        self.assertGreater(alert.confidence_score, 0.8)
    
    def test_create_flow_pattern_alert(self):
        """Test flow pattern alert creation."""
        pattern = FlowPattern(
            pattern_id="PATTERN001",
            pattern_type=PatternType.AGGRESSIVE_CALL_BUYING,
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            detected_at=datetime.now(),
            total_premium=Decimal('500000'),
            total_contracts=1000,
            trade_count=5,
            signal=SmartMoneySignal.BULLISH,
            confidence_score=0.85,
        )
        
        alert = self.manager.create_flow_pattern_alert(pattern)
        
        self.assertEqual(alert.alert_type, AlertType.SMART_MONEY_FLOW)
        self.assertGreater(alert.confidence_score, 0.8)
    
    def test_create_gamma_squeeze_alert(self):
        """Test gamma squeeze alert creation."""
        position = MarketMakerPosition(
            symbol="AAPL",
            underlying_symbol="AAPL",
            calculated_at=datetime.now(),
            net_delta=Decimal('-1500'),
            net_gamma=Decimal('-1200'),
            net_vega=Decimal('200'),
            net_theta=Decimal('50'),
            position_bias=PositionBias.SHORT_GAMMA,
            hedge_pressure="buy",
            call_volume=5000,
            put_volume=3000,
            call_open_interest=100000,
            put_open_interest=80000,
            confidence=0.8,
        )
        
        alert = self.manager.create_gamma_squeeze_alert(position)
        
        self.assertEqual(alert.alert_type, AlertType.GAMMA_SQUEEZE)
        self.assertEqual(alert.severity, AlertSeverity.HIGH)
    
    def test_subscribe_to_alerts(self):
        """Test alert subscription."""
        callback_called = []
        
        def callback(alert: UnusualActivityAlert):
            callback_called.append(alert)
        
        self.manager.subscribe(callback)
        
        trades = [self.create_trade() for _ in range(4)]
        alert = self.manager.create_sweep_alert(trades, 0.85)
        
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0].alert_id, alert.alert_id)
    
    def test_get_active_alerts(self):
        """Test retrieving active alerts."""
        # Create multiple alerts
        for i in range(5):
            trades = [self.create_trade() for _ in range(4)]
            self.manager.create_sweep_alert(trades, 0.85)
        
        alerts = self.manager.get_active_alerts()
        
        self.assertEqual(len(alerts), 5)
        self.assertTrue(all(a.is_active for a in alerts))
    
    def test_filter_by_severity(self):
        """Test filtering by severity."""
        # Create high severity alert
        large_trades = [self.create_trade(size=500, premium=Decimal('20.00')) for _ in range(4)]
        self.manager.create_sweep_alert(large_trades, 0.95)
        
        # Create low severity alert
        small_trades = [self.create_trade(size=10, premium=Decimal('1.00')) for _ in range(4)]
        self.manager.create_sweep_alert(small_trades, 0.6)
        
        high_alerts = self.manager.get_active_alerts(min_severity=AlertSeverity.HIGH)
        
        self.assertGreater(len(high_alerts), 0)
        self.assertTrue(all(
            a.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]
            for a in high_alerts
        ))
    
    def test_acknowledge_alert(self):
        """Test alert acknowledgment."""
        trades = [self.create_trade() for _ in range(4)]
        alert = self.manager.create_sweep_alert(trades, 0.85)
        
        success = self.manager.acknowledge_alert(alert.alert_id, "test_user")
        
        self.assertTrue(success)
        
        alerts = self.manager.get_active_alerts()
        self.assertTrue(alerts[0].is_acknowledged)
    
    def test_deactivate_alert(self):
        """Test alert deactivation."""
        trades = [self.create_trade() for _ in range(4)]
        alert = self.manager.create_sweep_alert(trades, 0.85)
        
        success = self.manager.deactivate_alert(alert.alert_id)
        
        self.assertTrue(success)
        
        alerts = self.manager.get_active_alerts()
        self.assertEqual(len(alerts), 0)
    
    def test_statistics(self):
        """Test alert statistics."""
        for i in range(3):
            trades = [self.create_trade() for _ in range(4)]
            self.manager.create_sweep_alert(trades, 0.85)
        
        stats = self.manager.get_statistics()
        
        self.assertEqual(stats['total_created'], 3)
        self.assertEqual(stats['active'], 3)
        self.assertGreater(stats['by_type']['unusual_sweep'], 0)


class TestAlertDispatcher(unittest.TestCase):
    """Test AlertDispatcher."""
    
    def setUp(self):
        """Set up test dispatcher."""
        self.dispatcher = AlertDispatcher()
    
    def create_alert(self) -> UnusualActivityAlert:
        """Create a test alert."""
        return UnusualActivityAlert(
            alert_id="TEST_ALERT",
            alert_type=AlertType.UNUSUAL_SWEEP,
            severity=AlertSeverity.HIGH,
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            created_at=datetime.now(),
            title="Test Alert",
            description="Test description",
            total_premium=Decimal('1000000'),
            total_contracts=500,
            confidence_score=0.9,
        )
    
    def test_dispatch_to_console(self):
        """Test console dispatch."""
        alert = self.create_alert()
        
        results = self.dispatcher.dispatch(alert, channels=['console'])
        
        self.assertTrue(results['console'])
    
    def test_add_webhook_handler(self):
        """Test adding webhook handler."""
        self.dispatcher.add_webhook_handler("https://example.com/webhook")
        
        alert = self.create_alert()
        results = self.dispatcher.dispatch(alert, channels=['webhook'])
        
        self.assertTrue(results['webhook'])
    
    def test_add_custom_handler(self):
        """Test adding custom handler."""
        handler_called = []
        
        def custom_handler(alert):
            handler_called.append(alert)
        
        self.dispatcher.add_custom_handler("custom", custom_handler)
        
        alert = self.create_alert()
        results = self.dispatcher.dispatch(alert, channels=['custom'])
        
        self.assertTrue(results['custom'])
        self.assertEqual(len(handler_called), 1)
    
    def test_dispatch_log(self):
        """Test dispatch logging."""
        alert = self.create_alert()
        
        self.dispatcher.dispatch(alert, channels=['console'])
        
        log = self.dispatcher.get_dispatch_log(limit=10)
        
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]['alert_id'], "TEST_ALERT")


class TestAlertSeverityCalculation(unittest.TestCase):
    """Test alert severity calculation."""
    
    def setUp(self):
        """Set up test manager."""
        self.manager = AlertManager()
    
    def test_critical_severity(self):
        """Test critical severity for very large trade."""
        severity = self.manager._calculate_severity(
            premium=Decimal('10000000'),  # $10M
            confidence=0.95,
            trade_count=10,
        )
        
        self.assertEqual(severity, AlertSeverity.CRITICAL)
    
    def test_high_severity(self):
        """Test high severity."""
        severity = self.manager._calculate_severity(
            premium=Decimal('1000000'),  # $1M
            confidence=0.85,
            trade_count=5,
        )
        
        self.assertIn(severity, [AlertSeverity.HIGH, AlertSeverity.CRITICAL])
    
    def test_low_severity(self):
        """Test low severity."""
        severity = self.manager._calculate_severity(
            premium=Decimal('50000'),
            confidence=0.6,
            trade_count=2,
        )
        
        self.assertIn(severity, [AlertSeverity.LOW, AlertSeverity.MEDIUM, AlertSeverity.INFO])


if __name__ == '__main__':
    unittest.main()
