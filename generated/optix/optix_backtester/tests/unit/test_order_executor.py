"""
Unit tests for order executor
"""
import pytest
from datetime import datetime, date

from src.execution.order_executor import (
    OrderExecutor, PositionSizer, FillType
)
from src.models.backtest import TransactionCostModel
from src.models.option import (
    OptionContract, OptionQuote, OptionType, OptionSide
)


@pytest.fixture
def transaction_costs():
    """Create transaction cost model"""
    return TransactionCostModel(
        commission_per_contract=0.65,
        slippage_percent=0.1,
        spread_cost_percent=50.0
    )


@pytest.fixture
def executor(transaction_costs):
    """Create order executor"""
    return OrderExecutor(transaction_costs)


@pytest.fixture
def sample_quote():
    """Create sample option quote"""
    contract = OptionContract(
        symbol="SPY",
        expiration=date(2024, 12, 31),
        strike=450.0,
        option_type=OptionType.CALL
    )
    
    return OptionQuote(
        contract=contract,
        timestamp=datetime.now(),
        bid=5.00,
        ask=5.20,
        last=5.10,
        volume=1000,
        open_interest=5000,
        implied_volatility=0.25
    )


class TestOrderExecutor:
    """Test OrderExecutor"""
    
    def test_market_order_buy(self, executor, sample_quote):
        """Test market order execution - buy"""
        fill_price, commission, slippage = executor.execute_market_order(
            sample_quote,
            OptionSide.BUY,
            quantity=10
        )
        
        # Should fill at ask or higher
        assert fill_price >= sample_quote.ask
        
        # Commission should be calculated
        assert commission == 0.65 * 10
        
        # Slippage should be positive
        assert slippage >= 0
    
    def test_market_order_sell(self, executor, sample_quote):
        """Test market order execution - sell"""
        fill_price, commission, slippage = executor.execute_market_order(
            sample_quote,
            OptionSide.SELL,
            quantity=10
        )
        
        # Should fill at bid or lower
        assert fill_price <= sample_quote.bid
        
        # Commission should be calculated
        assert commission == 0.65 * 10
    
    def test_limit_order_buy_fills(self, executor, sample_quote):
        """Test limit order that should fill"""
        result = executor.execute_limit_order(
            sample_quote,
            OptionSide.BUY,
            quantity=10,
            limit_price=5.30  # Above ask, should fill
        )
        
        assert result is not None
        fill_price, commission, slippage = result
        assert fill_price == 5.30
        assert commission == 0.65 * 10
    
    def test_limit_order_buy_no_fill(self, executor, sample_quote):
        """Test limit order that won't fill"""
        result = executor.execute_limit_order(
            sample_quote,
            OptionSide.BUY,
            quantity=10,
            limit_price=4.50  # Below ask, won't fill
        )
        
        assert result is None
    
    def test_limit_order_sell_fills(self, executor, sample_quote):
        """Test sell limit order that should fill"""
        result = executor.execute_limit_order(
            sample_quote,
            OptionSide.SELL,
            quantity=10,
            limit_price=4.80  # Below bid, should fill
        )
        
        assert result is not None
        fill_price, commission, slippage = result
        assert fill_price == 4.80
    
    def test_limit_order_sell_no_fill(self, executor, sample_quote):
        """Test sell limit order that won't fill"""
        result = executor.execute_limit_order(
            sample_quote,
            OptionSide.SELL,
            quantity=10,
            limit_price=5.50  # Above bid, won't fill
        )
        
        assert result is None
    
    def test_mid_price_execution(self, executor, sample_quote):
        """Test execution at mid price"""
        fill_price, commission, spread_cost = executor.execute_at_mid(
            sample_quote,
            OptionSide.BUY,
            quantity=10
        )
        
        # Should fill at mid
        assert fill_price == sample_quote.mid_price
        
        # Commission calculated
        assert commission == 0.65 * 10
        
        # Spread cost calculated
        assert spread_cost > 0
    
    def test_slippage_with_liquidity(self, executor, sample_quote):
        """Test slippage scales with order size"""
        # Small order
        _, _, slippage_small = executor.execute_market_order(
            sample_quote,
            OptionSide.BUY,
            quantity=1
        )
        
        # Large order
        _, _, slippage_large = executor.execute_market_order(
            sample_quote,
            OptionSide.BUY,
            quantity=100
        )
        
        # Large order should have more slippage
        assert slippage_large > slippage_small
    
    def test_fill_probability(self, executor, sample_quote):
        """Test fill probability calculation"""
        # Limit at ask - high probability
        prob_high = executor.simulate_fill_probability(
            sample_quote,
            OptionSide.BUY,
            limit_price=sample_quote.ask
        )
        
        assert prob_high > 0.9
        
        # Limit at bid - low probability
        prob_low = executor.simulate_fill_probability(
            sample_quote,
            OptionSide.BUY,
            limit_price=sample_quote.bid
        )
        
        assert prob_low < 0.5
    
    def test_transaction_cost_application(self, executor):
        """Test applying transaction costs to P&L"""
        gross_pnl = 1000.0
        commission = 65.0
        slippage = 10.0
        
        net_pnl = executor.apply_transaction_costs(
            gross_pnl,
            commission,
            slippage
        )
        
        assert net_pnl == 925.0


class TestPositionSizer:
    """Test PositionSizer"""
    
    def test_fixed_quantity(self):
        """Test fixed quantity sizing"""
        size = PositionSizer.fixed_quantity(10)
        assert size == 10
    
    def test_percent_of_capital(self):
        """Test percent of capital sizing"""
        size = PositionSizer.percent_of_capital(
            capital=100000,
            percent=10,
            option_price=5.0
        )
        
        # 10% of 100k = 10k, divided by 500 per contract = 20 contracts
        assert size == 20
    
    def test_percent_of_capital_minimum(self):
        """Test minimum position size"""
        size = PositionSizer.percent_of_capital(
            capital=1000,
            percent=1,
            option_price=100.0
        )
        
        # Should return at least 1
        assert size >= 1
    
    def test_kelly_criterion(self):
        """Test Kelly criterion sizing"""
        size = PositionSizer.kelly_criterion(
            win_rate=0.6,
            avg_win=100,
            avg_loss=50,
            capital=100000,
            option_price=5.0
        )
        
        # Should return reasonable size
        assert size >= 1
        assert size < 1000  # Not over-leveraged
    
    def test_kelly_criterion_zero_loss(self):
        """Test Kelly with zero average loss"""
        size = PositionSizer.kelly_criterion(
            win_rate=0.6,
            avg_win=100,
            avg_loss=0,
            capital=100000,
            option_price=5.0
        )
        
        # Should handle edge case
        assert size >= 1
    
    def test_kelly_criterion_low_win_rate(self):
        """Test Kelly with low win rate"""
        size = PositionSizer.kelly_criterion(
            win_rate=0.3,
            avg_win=100,
            avg_loss=50,
            capital=100000,
            option_price=5.0
        )
        
        # Should be conservative with low win rate
        assert size >= 1
