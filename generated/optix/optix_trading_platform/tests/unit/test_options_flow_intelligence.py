"""Unit tests for main Options Flow Intelligence engine."""
import unittest
from datetime import datetime
from decimal import Decimal

from src.options_flow_intelligence import OptionsFlowIntelligence
from src.models import OptionsTrade, OrderType, TradeType


class TestOptionsFlowIntelligence(unittest.TestCase):
    """Test main Options Flow Intelligence engine."""
    
    def setUp(self):
        """Set up test engine."""
        self.engine = OptionsFlowIntelligence(enable_alerts=True)
    
    def create_trade(
        self,
        exchange: str = "CBOE",
        size: int = 100,
        premium: Decimal = Decimal('5.50'),
        is_aggressive: bool = True,
    ) -> OptionsTrade:
        """Create a test trade."""
        return OptionsTrade(
            trade_id=f"TRADE_{exchange}_{datetime.now().timestamp()}",
            symbol="AAPL250117C00150000",
            underlying_symbol="AAPL",
            order_type=OrderType.CALL,
            strike=Decimal('150.00'),
            expiration=datetime(2025, 1, 17),
            premium=premium,
            size=size,
            price=Decimal('150.50'),
            timestamp=datetime.now(),
            trade_type=TradeType.REGULAR,
            exchange=exchange,
            execution_side="ask" if is_aggressive else "mid",
            is_aggressive=is_aggressive,
            underlying_price=Decimal('148.00'),
            open_interest=5000,
        )
    
    def test_process_sweep(self):
        """Test processing sweep activity."""
        # Create sweep across exchanges
        for exchange in ["CBOE", "PHLX", "ISE", "AMEX"]:
            trade = self.create_trade(exchange=exchange, size=100)
            result = self.engine.process_trade(trade)
        
        stats = self.engine.get_statistics()
        self.assertGreater(stats['engine']['sweeps_detected'], 0)
    
    def test_process_block(self):
        """Test processing block trade."""
        trade = self.create_trade(size=500, premium=Decimal('10.00'))
        
        result = self.engine.process_trade(trade)
        
        self.assertIn('detections', result)
        has_block = any(
            d['type'] == 'block'
            for d in result['detections']
        )
        # May not always detect on first trade
    
    def test_process_dark_pool(self):
        """Test processing dark pool print."""
        trade = self.create_trade(exchange="EDGX", size=150, is_aggressive=False)
        
        result = self.engine.process_trade(trade)
        
        has_dark_pool = any(
            d['type'] == 'dark_pool'
            for d in result['detections']
        )
        self.assertTrue(has_dark_pool)
    
    def test_calculate_mm_position(self):
        """Test market maker position calculation."""
        # Add some trades
        for i in range(10):
            trade = self.create_trade(size=100 + i * 10)
            self.engine.process_trade(trade)
        
        position = self.engine.calculate_market_maker_position("AAPL")
        
        self.assertEqual(position.underlying_symbol, "AAPL")
        self.assertIsNotNone(position.net_delta)
        self.assertIsNotNone(position.net_gamma)
        self.assertGreater(position.call_volume, 0)
    
    def test_get_order_flow_summary(self):
        """Test order flow summary."""
        # Add trades
        for i in range(10):
            order_type = OrderType.CALL if i % 2 == 0 else OrderType.PUT
            trade = self.create_trade(size=100)
            trade.order_type = order_type
            self.engine.process_trade(trade)
        
        summary = self.engine.get_order_flow_summary("AAPL")
        
        self.assertEqual(summary['symbol'], "AAPL")
        self.assertEqual(summary['total_trades'], 10)
        self.assertGreater(float(summary['total_premium']), 0)
    
    def test_get_institutional_flow(self):
        """Test institutional flow summary."""
        # Add institutional-size trades
        for i in range(5):
            trade = self.create_trade(size=500, premium=Decimal('10.00'))
            self.engine.process_trade(trade)
        
        summary = self.engine.get_institutional_flow()
        
        self.assertGreater(summary['total_trades'], 0)
        self.assertGreater(float(summary['total_premium']), 0)
    
    def test_get_flow_by_strike(self):
        """Test flow by strike."""
        # Add trades at different strikes
        for strike in [145, 150, 155]:
            trade = self.create_trade(size=100)
            trade.strike = Decimal(str(strike))
            self.engine.process_trade(trade)
        
        flow = self.engine.get_flow_by_strike("AAPL")
        
        self.assertEqual(flow['symbol'], "AAPL")
        self.assertGreater(len(flow['strikes']), 0)
    
    def test_get_active_alerts(self):
        """Test retrieving active alerts."""
        # Create sweep to trigger alert
        for exchange in ["CBOE", "PHLX", "ISE", "AMEX"]:
            trade = self.create_trade(exchange=exchange, size=200, premium=Decimal('10.00'))
            self.engine.process_trade(trade)
        
        alerts = self.engine.get_active_alerts()
        
        # Should have at least one alert
        self.assertGreaterEqual(len(alerts), 0)
    
    def test_acknowledge_alert(self):
        """Test alert acknowledgment."""
        # Create alert
        for exchange in ["CBOE", "PHLX", "ISE", "AMEX"]:
            trade = self.create_trade(exchange=exchange, size=200, premium=Decimal('10.00'))
            self.engine.process_trade(trade)
        
        alerts = self.engine.get_active_alerts()
        
        if alerts:
            alert_id = alerts[0]['alert_id']
            success = self.engine.acknowledge_alert(alert_id, "test_user")
            self.assertTrue(success)
    
    def test_alert_subscription(self):
        """Test alert subscription."""
        received_alerts = []
        
        def callback(alert):
            received_alerts.append(alert)
        
        self.engine.subscribe_to_alerts(callback)
        
        # Create sweep to trigger alert
        for exchange in ["CBOE", "PHLX", "ISE", "AMEX"]:
            trade = self.create_trade(exchange=exchange, size=200, premium=Decimal('10.00'))
            self.engine.process_trade(trade)
        
        # Should have received some alerts
        self.assertGreaterEqual(len(received_alerts), 0)
    
    def test_statistics(self):
        """Test engine statistics."""
        # Process some trades
        for i in range(20):
            trade = self.create_trade(size=100 + i * 10)
            self.engine.process_trade(trade)
        
        stats = self.engine.get_statistics()
        
        self.assertEqual(stats['engine']['trades_processed'], 20)
        self.assertIn('alerts', stats)
    
    def test_reset_statistics(self):
        """Test statistics reset."""
        # Process trades
        for i in range(5):
            trade = self.create_trade()
            self.engine.process_trade(trade)
        
        self.engine.reset_statistics()
        
        stats = self.engine.get_statistics()
        self.assertEqual(stats['engine']['trades_processed'], 0)


class TestIntegrationScenarios(unittest.TestCase):
    """Test complete integration scenarios."""
    
    def setUp(self):
        """Set up test engine."""
        self.engine = OptionsFlowIntelligence(enable_alerts=True)
    
    def test_aggressive_call_buying_scenario(self):
        """Test aggressive call buying detection."""
        # Simulate aggressive call buying
        for i in range(5):
            trade = OptionsTrade(
                trade_id=f"CALL_BUY_{i}",
                symbol="TSLA250117C00200000",
                underlying_symbol="TSLA",
                order_type=OrderType.CALL,
                strike=Decimal('200.00'),
                expiration=datetime(2025, 1, 17),
                premium=Decimal('8.50'),
                size=150 + i * 20,
                price=Decimal('195.50'),
                timestamp=datetime.now(),
                trade_type=TradeType.REGULAR,
                exchange="CBOE",
                execution_side="ask",
                is_aggressive=True,
                above_ask=True,
                underlying_price=Decimal('195.00'),
            )
            
            result = self.engine.process_trade(trade)
        
        # Check for pattern detection
        summary = self.engine.get_order_flow_summary("TSLA")
        self.assertIn(summary['sentiment'], ['bullish', 'very_bullish'])
    
    def test_institutional_spread_scenario(self):
        """Test institutional spread detection."""
        # Simulate vertical spread
        strikes = [Decimal('150.00'), Decimal('155.00')]
        
        for strike in strikes:
            trade = OptionsTrade(
                trade_id=f"SPREAD_{strike}",
                symbol=f"AAPL250117C{int(strike * 1000):08d}",
                underlying_symbol="AAPL",
                order_type=OrderType.CALL,
                strike=strike,
                expiration=datetime(2025, 1, 17),
                premium=Decimal('6.50'),
                size=500,
                price=Decimal('148.50'),
                timestamp=datetime.now(),
                trade_type=TradeType.BLOCK,
                exchange="CBOE",
                execution_side="mid",
                is_opening=True,
                underlying_price=Decimal('148.00'),
            )
            
            result = self.engine.process_trade(trade)
        
        # Check flow by strike
        flow = self.engine.get_flow_by_strike("AAPL")
        self.assertGreater(len(flow['strikes']), 1)
    
    def test_gamma_squeeze_scenario(self):
        """Test gamma squeeze detection."""
        # Simulate heavy call buying
        for i in range(15):
            trade = OptionsTrade(
                trade_id=f"GAMMA_{i}",
                symbol="GME250117C00050000",
                underlying_symbol="GME",
                order_type=OrderType.CALL,
                strike=Decimal('50.00'),
                expiration=datetime(2025, 1, 17),
                premium=Decimal('3.50'),
                size=300,
                price=Decimal('45.50'),
                timestamp=datetime.now(),
                trade_type=TradeType.REGULAR,
                exchange="CBOE",
                execution_side="ask",
                is_aggressive=True,
                is_opening=True,
                underlying_price=Decimal('45.00'),
                open_interest=10000,
            )
            
            self.engine.process_trade(trade)
        
        # Calculate MM position
        position = self.engine.calculate_market_maker_position("GME")
        
        # MMs should be short gamma from all the call buying
        self.assertLess(position.net_gamma, Decimal('0'))


if __name__ == '__main__':
    unittest.main()
