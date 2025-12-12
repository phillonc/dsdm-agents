"""Unit tests for data models."""
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models import (
    OptionsTrade, TradeType, OrderType,
    FlowPattern, PatternType, SmartMoneySignal,
    MarketMakerPosition, PositionBias,
    UnusualActivityAlert, AlertSeverity, AlertType,
)


class TestOptionsTrade(unittest.TestCase):
    """Test OptionsTrade model."""
    
    def setUp(self):
        """Set up test data."""
        self.trade = OptionsTrade(
            trade_id="TEST001",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=OrderType.CALL,
            strike=Decimal('150.00'),
            expiration=datetime(2025, 1, 17),
            premium=Decimal('5.50'),
            size=100,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.REGULAR,
            exchange="CBOE",
            execution_side="ask",
            is_aggressive=True,
            underlying_price=Decimal('148.00'),
        )
    
    def test_notional_value(self):
        """Test notional value calculation."""
        expected = Decimal('5.50') * Decimal('100') * Decimal('100')
        self.assertEqual(self.trade.notional_value, expected)
    
    def test_is_itm_call(self):
        """Test ITM check for call."""
        self.assertFalse(self.trade.is_itm)  # 148 < 150
        
        self.trade.underlying_price = Decimal('151.00')
        self.assertTrue(self.trade.is_itm)
    
    def test_is_itm_put(self):
        """Test ITM check for put."""
        self.trade.order_type = OrderType.PUT
        self.trade.underlying_price = Decimal('148.00')
        self.assertTrue(self.trade.is_itm)  # 148 < 150
        
        self.trade.underlying_price = Decimal('151.00')
        self.assertFalse(self.trade.is_itm)
    
    def test_moneyness_call(self):
        """Test moneyness calculation for call."""
        self.trade.underlying_price = Decimal('150.00')
        moneyness = self.trade.moneyness
        self.assertIsNotNone(moneyness)
        self.assertAlmostEqual(float(moneyness), 1.0, places=2)
    
    def test_days_to_expiration(self):
        """Test days to expiration."""
        ref_time = datetime(2025, 1, 10)
        dte = self.trade.days_to_expiration(ref_time)
        self.assertEqual(dte, 7)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        trade_dict = self.trade.to_dict()
        self.assertEqual(trade_dict['trade_id'], "TEST001")
        self.assertEqual(trade_dict['underlying_symbol'], "AAPL")
        self.assertEqual(trade_dict['order_type'], "call")


class TestFlowPattern(unittest.TestCase):
    """Test FlowPattern model."""
    
    def setUp(self):
        """Set up test data."""
        self.pattern = FlowPattern(
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
            call_premium=Decimal('500000'),
            put_premium=Decimal('0'),
        )
    
    def test_net_sentiment(self):
        """Test net sentiment calculation."""
        self.assertEqual(self.pattern.net_sentiment, "bullish")
        
        self.pattern.put_premium = Decimal('600000')
        self.assertEqual(self.pattern.net_sentiment, "bearish")
        
        self.pattern.call_premium = Decimal('300000')
        self.pattern.put_premium = Decimal('300000')
        self.assertEqual(self.pattern.net_sentiment, "neutral")
    
    def test_is_significant(self):
        """Test significance check."""
        self.assertTrue(self.pattern.is_significant)
        
        self.pattern.confidence_score = 0.5
        self.assertFalse(self.pattern.is_significant)
        
        self.pattern.confidence_score = 0.85
        self.pattern.total_premium = Decimal('50000')
        self.assertFalse(self.pattern.is_significant)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        pattern_dict = self.pattern.to_dict()
        self.assertEqual(pattern_dict['pattern_type'], 'aggressive_call_buying')
        self.assertEqual(pattern_dict['signal'], 'bullish')


class TestMarketMakerPosition(unittest.TestCase):
    """Test MarketMakerPosition model."""
    
    def setUp(self):
        """Set up test data."""
        self.position = MarketMakerPosition(
            symbol="AAPL",
            underlying_symbol="AAPL",
            calculated_at=datetime.now(),
            net_delta=Decimal('-1500'),
            net_gamma=Decimal('-800'),
            net_vega=Decimal('200'),
            net_theta=Decimal('50'),
            position_bias=PositionBias.SHORT_GAMMA,
            hedge_pressure="buy",
            call_volume=5000,
            put_volume=3000,
            call_open_interest=100000,
            put_open_interest=80000,
        )
    
    def test_put_call_ratios(self):
        """Test put/call ratio calculations."""
        volume_ratio = self.position.put_call_volume_ratio
        self.assertIsNotNone(volume_ratio)
        self.assertAlmostEqual(float(volume_ratio), 0.6, places=2)
        
        oi_ratio = self.position.put_call_oi_ratio
        self.assertIsNotNone(oi_ratio)
        self.assertAlmostEqual(float(oi_ratio), 0.8, places=2)
    
    def test_gamma_squeeze_risk(self):
        """Test gamma squeeze risk detection."""
        self.assertTrue(self.position.is_gamma_squeeze_risk)
        
        self.position.position_bias = PositionBias.LONG_GAMMA
        self.assertFalse(self.position.is_gamma_squeeze_risk)
        
        self.position.position_bias = PositionBias.SHORT_GAMMA
        self.position.net_gamma = Decimal('-500')
        self.assertFalse(self.position.is_gamma_squeeze_risk)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        pos_dict = self.position.to_dict()
        self.assertEqual(pos_dict['position_bias'], 'short_gamma')
        self.assertTrue(pos_dict['is_gamma_squeeze_risk'])


class TestUnusualActivityAlert(unittest.TestCase):
    """Test UnusualActivityAlert model."""
    
    def setUp(self):
        """Set up test data."""
        self.alert = UnusualActivityAlert(
            alert_id="ALERT001",
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
    
    def test_age_seconds(self):
        """Test alert age calculation."""
        age = self.alert.age_seconds
        self.assertGreaterEqual(age, 0)
        self.assertLess(age, 1)  # Just created
    
    def test_priority_score(self):
        """Test priority score calculation."""
        score = self.alert.priority_score
        self.assertGreater(score, 75)  # High severity + high confidence + large premium
    
    def test_acknowledge(self):
        """Test alert acknowledgment."""
        self.assertFalse(self.alert.is_acknowledged)
        
        self.alert.acknowledge("test_user")
        
        self.assertTrue(self.alert.is_acknowledged)
        self.assertEqual(self.alert.acknowledged_by, "test_user")
        self.assertIsNotNone(self.alert.acknowledged_at)
    
    def test_deactivate(self):
        """Test alert deactivation."""
        self.assertTrue(self.alert.is_active)
        
        self.alert.deactivate()
        
        self.assertFalse(self.alert.is_active)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        alert_dict = self.alert.to_dict()
        self.assertEqual(alert_dict['alert_type'], 'unusual_sweep')
        self.assertEqual(alert_dict['severity'], 'high')


if __name__ == '__main__':
    unittest.main()
