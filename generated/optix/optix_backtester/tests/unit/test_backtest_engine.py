"""
Unit tests for backtest engine
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from src.engine.backtester import BacktestEngine
from src.models.backtest import BacktestConfig, TransactionCostModel, BacktestStatus
from src.models.option import MarketConditions
from src.data.market_data import SimulatedMarketDataProvider
from src.strategies.example import SimpleStrategy


@pytest.fixture
def backtest_config():
    """Create test backtest configuration"""
    return BacktestConfig(
        initial_capital=100000.0,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        symbols=["SPY"],
        transaction_costs=TransactionCostModel(
            commission_per_contract=0.65,
            slippage_percent=0.1
        ),
        max_position_size=10,
        max_positions=5
    )


@pytest.fixture
def data_provider():
    """Create simulated data provider"""
    return SimulatedMarketDataProvider(seed=42)


@pytest.mark.asyncio
class TestBacktestEngine:
    """Test BacktestEngine"""
    
    async def test_engine_initialization(self, backtest_config, data_provider):
        """Test engine initialization"""
        engine = BacktestEngine(data_provider, backtest_config)
        
        assert engine.config == backtest_config
        assert engine.capital == backtest_config.initial_capital
        assert len(engine.positions) == 0
        assert len(engine.trades) == 0
    
    async def test_run_backtest(self, backtest_config, data_provider):
        """Test running backtest"""
        engine = BacktestEngine(data_provider, backtest_config)
        strategy = SimpleStrategy()
        
        result = await engine.run(strategy)
        
        assert result.backtest_id is not None
        assert result.status == BacktestStatus.COMPLETED
        assert result.config == backtest_config
        assert result.performance is not None
    
    async def test_capital_tracking(self, backtest_config, data_provider):
        """Test capital tracking during backtest"""
        engine = BacktestEngine(data_provider, backtest_config)
        strategy = SimpleStrategy()
        
        initial_capital = engine.capital
        
        await engine.run(strategy)
        
        # Capital should change after trading
        # (may be higher or lower depending on results)
        assert engine.capital != initial_capital or len(engine.trades) == 0
    
    async def test_equity_curve_generation(self, backtest_config, data_provider):
        """Test equity curve generation"""
        engine = BacktestEngine(data_provider, backtest_config)
        strategy = SimpleStrategy()
        
        result = await engine.run(strategy)
        
        # Should have equity curve data
        assert len(result.equity_curve) > 0
        
        # Each entry should have required fields
        for entry in result.equity_curve:
            assert 'timestamp' in entry
            assert 'equity' in entry
            assert 'cash' in entry
    
    async def test_performance_metrics_calculation(self, backtest_config, data_provider):
        """Test performance metrics calculation"""
        engine = BacktestEngine(data_provider, backtest_config)
        strategy = SimpleStrategy()
        
        result = await engine.run(strategy)
        
        # Check key metrics are calculated
        perf = result.performance
        assert perf.total_trades >= 0
        assert perf.win_rate >= 0 and perf.win_rate <= 100
        assert perf.sharpe_ratio is not None
        assert perf.max_drawdown >= 0
    
    async def test_trade_recording(self, backtest_config, data_provider):
        """Test trade recording"""
        engine = BacktestEngine(data_provider, backtest_config)
        strategy = SimpleStrategy()
        
        result = await engine.run(strategy)
        
        # Each trade should have proper fields
        for trade in result.trades:
            assert trade.trade_id is not None
            assert trade.entry_time is not None
            assert trade.underlying_symbol is not None
            assert trade.net_pnl is not None
    
    async def test_position_limits(self, backtest_config, data_provider):
        """Test position limits are enforced"""
        engine = BacktestEngine(data_provider, backtest_config)
        strategy = SimpleStrategy()
        
        result = await engine.run(strategy)
        
        # Should never exceed max positions
        for equity_entry in result.equity_curve:
            assert equity_entry['num_positions'] <= backtest_config.max_positions


class TestPerformanceCalculations:
    """Test performance metric calculations"""
    
    def test_win_rate_calculation(self, backtest_config, data_provider):
        """Test win rate calculation"""
        engine = BacktestEngine(data_provider, backtest_config)
        
        # Mock trades
        from src.models.backtest import Trade
        from uuid import uuid4
        
        engine.trades = [
            Trade(
                trade_id=str(uuid4()),
                strategy_id="test",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                underlying_symbol="SPY",
                legs_count=1,
                entry_price=100,
                exit_price=110,
                gross_pnl=10,
                net_pnl=9,
                return_percent=9.0
            ),
            Trade(
                trade_id=str(uuid4()),
                strategy_id="test",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                underlying_symbol="SPY",
                legs_count=1,
                entry_price=100,
                exit_price=90,
                gross_pnl=-10,
                net_pnl=-11,
                return_percent=-11.0
            )
        ]
        
        metrics = engine._calculate_performance_metrics()
        
        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.win_rate == 50.0
    
    def test_profit_factor_calculation(self, backtest_config, data_provider):
        """Test profit factor calculation"""
        engine = BacktestEngine(data_provider, backtest_config)
        
        from src.models.backtest import Trade
        from uuid import uuid4
        
        engine.trades = [
            Trade(
                trade_id=str(uuid4()),
                strategy_id="test",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                underlying_symbol="SPY",
                legs_count=1,
                entry_price=100,
                exit_price=120,
                gross_pnl=20,
                net_pnl=19,
                return_percent=19.0
            ),
            Trade(
                trade_id=str(uuid4()),
                strategy_id="test",
                entry_time=datetime.now(),
                exit_time=datetime.now(),
                underlying_symbol="SPY",
                legs_count=1,
                entry_price=100,
                exit_price=90,
                gross_pnl=-10,
                net_pnl=-11,
                return_percent=-11.0
            )
        ]
        
        metrics = engine._calculate_performance_metrics()
        
        assert metrics.gross_profit == 19
        assert metrics.gross_loss == 11
        assert metrics.profit_factor == pytest.approx(19/11, rel=0.01)
    
    def test_empty_trades_metrics(self, backtest_config, data_provider):
        """Test metrics calculation with no trades"""
        engine = BacktestEngine(data_provider, backtest_config)
        
        metrics = engine._calculate_performance_metrics()
        
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0
        assert metrics.total_pnl == 0
