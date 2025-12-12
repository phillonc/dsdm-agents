"""Unit tests for analyzers."""
import unittest
from datetime import datetime
from decimal import Decimal

from src.models import OptionsTrade, OrderType, TradeType
from src.analyzers import MarketMakerAnalyzer, OrderFlowAggregator


class TestMarketMakerAnalyzer(unittest.TestCase):
    """Test MarketMakerAnalyzer."""
    
    def setUp(self):
        """Set up test analyzer."""
        self.analyzer = MarketMakerAnalyzer()
    
    def create_trade(
        self,
        order_type: OrderType,
        size: int,
        strike: Decimal,
        is_opening: bool = True,
    ) -> OptionsTrade:
        """Create a test trade."""
        return OptionsTrade(
            trade_id=f"TRADE_{datetime.now().timestamp()}",
            symbol=f"AAPL250117{'C' if order_type == OrderType.CALL else 'P'}{int(strike * 1000):08d}",
            underlying_symbol="AAPL",
            order_type=order_type,
            strike=strike,
            expiration=datetime(2025, 1, 17),
            premium=Decimal('5.50'),
            size=size,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.REGULAR,
            exchange="CBOE",
            execution_side="ask",
            is_opening=is_opening,
            underlying_price=Decimal('150.00'),
            open_interest=1000,
        )
    
    def test_calculate_position(self):
        """Test market maker position calculation."""
        trades = [
            self.create_trade(OrderType.CALL, 100, Decimal('150.00')),
            self.create_trade(OrderType.CALL, 200, Decimal('155.00')),
            self.create_trade(OrderType.PUT, 150, Decimal('145.00')),
        ]
        
        position = self.analyzer.calculate_position("AAPL", trades)
        
        self.assertEqual(position.symbol, "AAPL")
        self.assertIsNotNone(position.net_delta)
        self.assertIsNotNone(position.net_gamma)
        self.assertEqual(position.call_volume, 300)
        self.assertEqual(position.put_volume, 150)
        self.assertGreater(position.confidence, 0.0)
    
    def test_position_bias_short_gamma(self):
        """Test short gamma position bias."""
        # Create trades that would make MM short gamma
        trades = [
            self.create_trade(OrderType.CALL, 500, Decimal('150.00')),
            self.create_trade(OrderType.CALL, 300, Decimal('155.00')),
        ]
        
        position = self.analyzer.calculate_position("AAPL", trades)
        
        # MMs are typically short when retail buys
        self.assertLess(position.net_gamma, Decimal('0'))
    
    def test_put_call_ratios(self):
        """Test put/call ratio calculations."""
        trades = [
            self.create_trade(OrderType.CALL, 100, Decimal('150.00')),
            self.create_trade(OrderType.PUT, 200, Decimal('145.00')),
        ]
        
        position = self.analyzer.calculate_position("AAPL", trades)
        
        self.assertIsNotNone(position.put_call_volume_ratio)
        self.assertEqual(float(position.put_call_volume_ratio), 2.0)
    
    def test_estimate_delta_atm_call(self):
        """Test delta estimation for ATM call."""
        trade = self.create_trade(OrderType.CALL, 100, Decimal('150.00'))
        
        delta = self.analyzer._estimate_delta(trade)
        
        # ATM call should have ~0.5 delta per contract
        expected = Decimal('0.5') * Decimal('100')
        self.assertAlmostEqual(float(delta), float(expected), places=0)
    
    def test_estimate_gamma_atm(self):
        """Test gamma estimation for ATM option."""
        trade = self.create_trade(OrderType.CALL, 100, Decimal('150.00'))
        
        gamma = self.analyzer._estimate_gamma(trade)
        
        # ATM option should have higher gamma
        self.assertGreater(gamma, Decimal('0'))


class TestOrderFlowAggregator(unittest.TestCase):
    """Test OrderFlowAggregator."""
    
    def setUp(self):
        """Set up test aggregator."""
        self.aggregator = OrderFlowAggregator(
            institutional_threshold=Decimal('100000'),
            aggregation_window_minutes=60,
        )
    
    def create_trade(
        self,
        order_type: OrderType,
        size: int,
        premium: Decimal = Decimal('5.50'),
    ) -> OptionsTrade:
        """Create a test trade."""
        return OptionsTrade(
            trade_id=f"TRADE_{datetime.now().timestamp()}",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=order_type,
            strike=Decimal('150.00'),
            expiration=datetime(2025, 1, 17),
            premium=premium,
            size=size,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.REGULAR,
            exchange="CBOE",
            execution_side="ask",
        )
    
    def test_add_trade(self):
        """Test adding trades."""
        trade = self.create_trade(OrderType.CALL, 100)
        self.aggregator.add_trade(trade)
        
        self.assertEqual(len(self.aggregator._all_trades), 1)
    
    def test_institutional_tracking(self):
        """Test institutional trade tracking."""
        # Regular trade
        small_trade = self.create_trade(OrderType.CALL, 10, Decimal('1.00'))
        self.aggregator.add_trade(small_trade)
        
        # Institutional trade
        large_trade = self.create_trade(OrderType.CALL, 500, Decimal('5.50'))
        self.aggregator.add_trade(large_trade)
        
        self.assertEqual(len(self.aggregator._all_trades), 2)
        self.assertEqual(len(self.aggregator._institutional_trades), 1)
    
    def test_get_flow_by_symbol(self):
        """Test flow summary by symbol."""
        # Add various trades
        for i in range(10):
            order_type = OrderType.CALL if i % 2 == 0 else OrderType.PUT
            trade = self.create_trade(order_type, 100 + i * 10)
            self.aggregator.add_trade(trade)
        
        flow = self.aggregator.get_flow_by_symbol("AAPL")
        
        self.assertEqual(flow['symbol'], "AAPL")
        self.assertEqual(flow['total_trades'], 10)
        self.assertGreater(float(flow['total_premium']), 0)
        self.assertEqual(flow['call']['trades'], 5)
        self.assertEqual(flow['put']['trades'], 5)
    
    def test_sentiment_calculation(self):
        """Test sentiment calculation."""
        # Bullish flow
        for i in range(5):
            trade = self.create_trade(OrderType.CALL, 100)
            self.aggregator.add_trade(trade)
        
        flow = self.aggregator.get_flow_by_symbol("AAPL")
        self.assertIn(flow['sentiment'], ['bullish', 'very_bullish'])
        
        # Add bearish flow
        for i in range(10):
            trade = self.create_trade(OrderType.PUT, 100)
            self.aggregator.add_trade(trade)
        
        flow = self.aggregator.get_flow_by_symbol("AAPL")
        self.assertIn(flow['sentiment'], ['bearish', 'very_bearish'])
    
    def test_get_institutional_flow_summary(self):
        """Test institutional flow summary."""
        # Add institutional trades
        for i in range(5):
            order_type = OrderType.CALL if i < 3 else OrderType.PUT
            trade = self.create_trade(order_type, 500, Decimal('5.50'))
            self.aggregator.add_trade(trade)
        
        summary = self.aggregator.get_institutional_flow_summary()
        
        self.assertEqual(summary['total_trades'], 5)
        self.assertGreater(float(summary['total_premium']), 0)
        self.assertGreater(len(summary['symbols']), 0)
    
    def test_get_flow_by_strike(self):
        """Test flow aggregation by strike."""
        # Add trades at different strikes
        for strike in [145, 150, 155]:
            for order_type in [OrderType.CALL, OrderType.PUT]:
                trade = self.create_trade(order_type, 100)
                trade.strike = Decimal(str(strike))
                self.aggregator.add_trade(trade)
        
        flow = self.aggregator.get_flow_by_strike("AAPL")
        
        self.assertEqual(len(flow['strikes']), 3)
        self.assertEqual(flow['symbol'], "AAPL")


class TestMarketMakerGreeks(unittest.TestCase):
    """Test Greeks calculations."""
    
    def setUp(self):
        """Set up test analyzer."""
        self.analyzer = MarketMakerAnalyzer()
    
    def create_trade(
        self,
        order_type: OrderType,
        strike: Decimal,
        underlying_price: Decimal,
        size: int = 100,
    ) -> OptionsTrade:
        """Create a test trade."""
        return OptionsTrade(
            trade_id=f"TRADE_{datetime.now().timestamp()}",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=order_type,
            strike=strike,
            expiration=datetime(2025, 1, 17),
            premium=Decimal('5.50'),
            size=size,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.REGULAR,
            exchange="CBOE",
            execution_side="ask",
            underlying_price=underlying_price,
        )
    
    def test_itm_call_delta(self):
        """Test ITM call delta estimation."""
        trade = self.create_trade(
            OrderType.CALL,
            Decimal('140.00'),
            Decimal('150.00')
        )
        
        delta = self.analyzer._estimate_delta(trade)
        
        # ITM call should have high delta
        per_contract = delta / Decimal(trade.size)
        self.assertGreater(per_contract, Decimal('0.6'))
    
    def test_otm_call_delta(self):
        """Test OTM call delta estimation."""
        trade = self.create_trade(
            OrderType.CALL,
            Decimal('160.00'),
            Decimal('150.00')
        )
        
        delta = self.analyzer._estimate_delta(trade)
        
        # OTM call should have low delta
        per_contract = delta / Decimal(trade.size)
        self.assertLess(per_contract, Decimal('0.4'))
    
    def test_atm_gamma_high(self):
        """Test ATM gamma is highest."""
        atm_trade = self.create_trade(
            OrderType.CALL,
            Decimal('150.00'),
            Decimal('150.00')
        )
        otm_trade = self.create_trade(
            OrderType.CALL,
            Decimal('160.00'),
            Decimal('150.00')
        )
        
        atm_gamma = self.analyzer._estimate_gamma(atm_trade)
        otm_gamma = self.analyzer._estimate_gamma(otm_trade)
        
        self.assertGreater(atm_gamma, otm_gamma)
    
    def test_put_negative_delta(self):
        """Test put has negative delta."""
        trade = self.create_trade(
            OrderType.PUT,
            Decimal('150.00'),
            Decimal('150.00')
        )
        
        delta = self.analyzer._estimate_delta(trade)
        
        self.assertLess(delta, Decimal('0'))


if __name__ == '__main__':
    unittest.main()
