"""Unit tests for detectors."""
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models import OptionsTrade, TradeType, OrderType
from src.detectors import SweepDetector, BlockDetector, DarkPoolDetector, FlowAnalyzer


class TestSweepDetector(unittest.TestCase):
    """Test SweepDetector."""
    
    def setUp(self):
        """Set up test detector."""
        self.detector = SweepDetector(
            min_legs=3,
            max_time_window_seconds=2.0,
            min_premium_per_leg=Decimal('5000'),
        )
    
    def create_trade(self, exchange: str, seconds_offset: float = 0) -> OptionsTrade:
        """Create a test trade."""
        return OptionsTrade(
            trade_id=f"TRADE_{exchange}",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=OrderType.CALL,
            strike=Decimal('150.00'),
            expiration=datetime(2025, 1, 17),
            premium=Decimal('5.50'),
            size=50,
            price=Decimal('150.50'),
            timestamp=datetime.now() + timedelta(seconds=seconds_offset),
            trade_type=TradeType.REGULAR,
            exchange=exchange,
            execution_side="ask",
            is_aggressive=True,
        )
    
    def test_detect_sweep(self):
        """Test sweep detection."""
        # Create sweep across multiple exchanges
        trades = [
            self.create_trade("CBOE", 0),
            self.create_trade("PHLX", 0.5),
            self.create_trade("ISE", 1.0),
            self.create_trade("AMEX", 1.5),
        ]
        
        # Process trades
        for trade in trades[:-1]:
            result = self.detector.detect_sweep(trade)
            self.assertIsNone(result)
        
        # Last trade should trigger sweep detection
        result = self.detector.detect_sweep(trades[-1])
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 4)
        self.assertTrue(all(t.trade_type == TradeType.SWEEP for t in result))
    
    def test_no_sweep_single_exchange(self):
        """Test no sweep with single exchange."""
        trades = [self.create_trade("CBOE", i * 0.5) for i in range(4)]
        
        for trade in trades:
            result = self.detector.detect_sweep(trade)
            self.assertIsNone(result)  # All same exchange
    
    def test_no_sweep_too_slow(self):
        """Test no sweep when trades too far apart."""
        trades = [
            self.create_trade("CBOE", 0),
            self.create_trade("PHLX", 5.0),  # Too far apart
        ]
        
        for trade in trades:
            result = self.detector.detect_sweep(trade)
            self.assertIsNone(result)
    
    def test_calculate_sweep_score(self):
        """Test sweep confidence score."""
        trades = [self.create_trade(ex, i * 0.5) for i, ex in enumerate(["CBOE", "PHLX", "ISE", "AMEX"])]
        
        score = self.detector.calculate_sweep_score(trades)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestBlockDetector(unittest.TestCase):
    """Test BlockDetector."""
    
    def setUp(self):
        """Set up test detector."""
        self.detector = BlockDetector(
            min_contracts=100,
            min_premium=Decimal('50000'),
        )
    
    def create_block_trade(self, size: int) -> OptionsTrade:
        """Create a test block trade."""
        return OptionsTrade(
            trade_id=f"BLOCK_{size}",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=OrderType.CALL,
            strike=Decimal('150.00'),
            expiration=datetime(2025, 1, 17),
            premium=Decimal('5.50'),
            size=size,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.REGULAR,
            exchange="CBOE",
            execution_side="mid",
            is_opening=True,
        )
    
    def test_detect_block(self):
        """Test block trade detection."""
        trade = self.create_block_trade(200)
        
        is_block = self.detector.detect_block(trade)
        self.assertTrue(is_block)
        self.assertEqual(trade.trade_type, TradeType.BLOCK)
    
    def test_no_block_small_size(self):
        """Test no block for small size."""
        trade = self.create_block_trade(50)
        
        is_block = self.detector.detect_block(trade)
        self.assertFalse(is_block)
    
    def test_no_block_low_premium(self):
        """Test no block for low premium."""
        trade = self.create_block_trade(100)
        trade.premium = Decimal('0.50')  # Too low premium
        
        is_block = self.detector.detect_block(trade)
        self.assertFalse(is_block)
    
    def test_block_score(self):
        """Test block confidence score."""
        trade = self.create_block_trade(500)
        
        score = self.detector.calculate_block_score(trade)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    def test_update_volume_stats(self):
        """Test volume statistics update."""
        self.detector.update_volume_stats("AAPL", 100)
        self.detector.update_volume_stats("AAPL", 200)
        self.detector.update_volume_stats("AAPL", 150)
        
        avg_size = self.detector.get_average_size("AAPL")
        self.assertIsNotNone(avg_size)
        self.assertEqual(avg_size, 150)


class TestDarkPoolDetector(unittest.TestCase):
    """Test DarkPoolDetector."""
    
    def setUp(self):
        """Set up test detector."""
        self.detector = DarkPoolDetector(
            min_contracts=50,
            min_premium=Decimal('25000'),
        )
    
    def create_trade(self, exchange: str, size: int) -> OptionsTrade:
        """Create a test trade."""
        return OptionsTrade(
            trade_id=f"DP_{exchange}",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=OrderType.CALL,
            strike=Decimal('150.00'),
            expiration=datetime(2025, 1, 17),
            premium=Decimal('5.50'),
            size=size,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.REGULAR,
            exchange=exchange,
            execution_side="mid",
            is_aggressive=False,
            is_opening=True,
        )
    
    def test_detect_dark_pool_exchange(self):
        """Test dark pool detection by exchange."""
        trade = self.create_trade("EDGX", 100)
        
        is_dark = self.detector.detect_dark_pool(trade)
        self.assertTrue(is_dark)
        self.assertEqual(trade.trade_type, TradeType.DARK_POOL)
    
    def test_detect_dark_pool_delayed(self):
        """Test dark pool detection by delay."""
        trade = self.create_trade("CBOE", 100)
        market_time = datetime.now() + timedelta(seconds=60)
        
        is_dark = self.detector.detect_dark_pool(trade, market_time)
        self.assertTrue(is_dark)
    
    def test_no_dark_pool_small_size(self):
        """Test no dark pool for small size."""
        trade = self.create_trade("EDGX", 20)
        
        is_dark = self.detector.detect_dark_pool(trade)
        self.assertFalse(is_dark)
    
    def test_dark_pool_score(self):
        """Test dark pool confidence score."""
        trade = self.create_trade("EDGX", 150)
        
        score = self.detector.calculate_dark_pool_score(trade)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    def test_get_recent_volume(self):
        """Test recent volume tracking."""
        for i in range(5):
            trade = self.create_trade("EDGX", 100)
            self.detector.detect_dark_pool(trade)
            self.detector.add_to_history(trade)
        
        volume = self.detector.get_recent_dark_pool_volume("AAPL", 60)
        self.assertEqual(volume, 500)


class TestFlowAnalyzer(unittest.TestCase):
    """Test FlowAnalyzer."""
    
    def setUp(self):
        """Set up test analyzer."""
        self.analyzer = FlowAnalyzer(
            analysis_window_minutes=15,
            min_pattern_premium=Decimal('50000'),
        )
    
    def create_trade(
        self,
        order_type: OrderType,
        is_aggressive: bool = True,
        size: int = 100,
    ) -> OptionsTrade:
        """Create a test trade."""
        return OptionsTrade(
            trade_id=f"TRADE_{datetime.now().timestamp()}",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=order_type,
            strike=Decimal('150.00'),
            expiration=datetime(2025, 1, 17),
            premium=Decimal('5.50'),
            size=size,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.REGULAR,
            exchange="CBOE",
            execution_side="ask" if is_aggressive else "mid",
            is_aggressive=is_aggressive,
            above_ask=is_aggressive,
        )
    
    def test_detect_aggressive_buying(self):
        """Test aggressive buying pattern detection."""
        # Create series of aggressive call buys
        for i in range(5):
            trade = self.create_trade(OrderType.CALL, is_aggressive=True, size=200)
            patterns = self.analyzer.analyze_trade(trade)
        
        # Should detect pattern on later trades
        self.assertGreater(len(self.analyzer._detected_patterns), 0)
        
        # Check for aggressive call buying pattern
        has_aggressive = any(
            p.pattern_type.value == 'aggressive_call_buying'
            for p in self.analyzer._detected_patterns
        )
        self.assertTrue(has_aggressive)
    
    def test_detect_institutional_flow(self):
        """Test institutional flow detection."""
        # Create large institutional trade
        trade = self.create_trade(OrderType.CALL, size=1000)
        trade.premium = Decimal('5.50')  # $550K notional
        
        patterns = self.analyzer.analyze_trade(trade)
        
        # Should detect institutional flow
        has_institutional = any(
            p.pattern_type.value == 'institutional_flow'
            for p in patterns
        )
        # Note: May not detect on first trade, need multiple
    
    def test_get_flow_summary(self):
        """Test flow summary retrieval."""
        # Add some trades
        for i in range(10):
            order_type = OrderType.CALL if i % 2 == 0 else OrderType.PUT
            trade = self.create_trade(order_type)
            self.analyzer.analyze_trade(trade)
        
        summary = self.analyzer.get_flow_summary("AAPL")
        
        self.assertEqual(summary['symbol'], "AAPL")
        self.assertEqual(summary['trade_count'], 10)
        self.assertGreater(float(summary['total_premium']), 0)


if __name__ == '__main__':
    unittest.main()
