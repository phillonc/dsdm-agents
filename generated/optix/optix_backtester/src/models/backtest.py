"""
Backtesting models
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class BacktestStatus(str, Enum):
    """Backtest execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionCostModel(BaseModel):
    """Transaction cost configuration"""
    commission_per_contract: float = Field(default=0.65, ge=0)
    slippage_percent: float = Field(default=0.1, ge=0, le=100)
    spread_cost_percent: float = Field(default=50.0, ge=0, le=100, 
                                        description="% of spread to pay (50=mid)")


class BacktestConfig(BaseModel):
    """Backtesting configuration"""
    initial_capital: float = Field(..., gt=0)
    start_date: datetime
    end_date: datetime
    symbols: list[str] = Field(..., min_items=1)
    
    # Transaction costs
    transaction_costs: TransactionCostModel = Field(default_factory=TransactionCostModel)
    
    # Position sizing
    max_position_size: int = Field(default=100, gt=0)
    max_positions: int = Field(default=10, gt=0)
    position_size_method: str = Field(default="fixed", description="fixed, percent, kelly")
    
    # Risk management
    max_loss_per_trade: Optional[float] = Field(None, gt=0)
    max_daily_loss: Optional[float] = Field(None, gt=0)
    
    # Data settings
    data_frequency: str = Field(default="1min", description="1min, 5min, 1hour, 1day")
    warm_up_period_days: int = Field(default=30, ge=0)
    
    # Strategy specific
    strategy_params: Dict[str, Any] = Field(default_factory=dict)


class Trade(BaseModel):
    """Individual trade record"""
    trade_id: str
    strategy_id: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    
    # Position details
    underlying_symbol: str
    legs_count: int
    
    # Entry/Exit prices
    entry_price: float
    exit_price: Optional[float] = None
    
    # P&L
    gross_pnl: float = 0.0
    commissions: float = 0.0
    slippage: float = 0.0
    net_pnl: float = 0.0
    
    # Returns
    return_percent: float = 0.0
    
    # Risk metrics
    max_adverse_excursion: float = 0.0
    max_favorable_excursion: float = 0.0
    
    # Additional info
    exit_reason: Optional[str] = None
    notes: Optional[str] = None
    
    @property
    def holding_period_seconds(self) -> Optional[float]:
        """Calculate holding period in seconds"""
        if self.exit_time:
            return (self.exit_time - self.entry_time).total_seconds()
        return None
    
    @property
    def is_winner(self) -> bool:
        """Check if trade was profitable"""
        return self.net_pnl > 0


class PerformanceMetrics(BaseModel):
    """Comprehensive performance metrics"""
    
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Return metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade metrics
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_trade: float = 0.0
    
    # Time metrics
    avg_holding_period_hours: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # Risk-adjusted metrics
    volatility: float = 0.0
    downside_deviation: float = 0.0
    var_95: float = 0.0  # Value at Risk
    cvar_95: float = 0.0  # Conditional VaR
    
    # Additional metrics
    expectancy: float = 0.0
    ulcer_index: float = 0.0
    recovery_factor: float = 0.0


class BacktestResult(BaseModel):
    """Complete backtest results"""
    backtest_id: str
    status: BacktestStatus
    config: BacktestConfig
    
    # Execution info
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    
    # Results
    trades: list[Trade] = Field(default_factory=list)
    performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    
    # Equity curve
    equity_curve: list[Dict[str, Any]] = Field(default_factory=list)
    
    # Volatility regime analysis
    regime_performance: Dict[str, PerformanceMetrics] = Field(default_factory=dict)
    
    # Errors
    error_message: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class WalkForwardResult(BaseModel):
    """Walk-forward optimization results"""
    optimization_id: str
    total_periods: int
    train_ratio: float
    
    # Results per period
    in_sample_results: list[BacktestResult] = Field(default_factory=list)
    out_of_sample_results: list[BacktestResult] = Field(default_factory=list)
    
    # Combined metrics
    combined_performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    
    # Overfitting metrics
    in_sample_sharpe: float = 0.0
    out_of_sample_sharpe: float = 0.0
    degradation_percent: float = 0.0
    
    # Stability metrics
    sharpe_stability: float = 0.0
    return_stability: float = 0.0


class MonteCarloResult(BaseModel):
    """Monte Carlo simulation results"""
    simulation_id: str
    iterations: int
    base_backtest_id: str
    
    # Distribution statistics
    mean_return: float = 0.0
    median_return: float = 0.0
    std_return: float = 0.0
    
    mean_sharpe: float = 0.0
    median_sharpe: float = 0.0
    
    mean_max_drawdown: float = 0.0
    median_max_drawdown: float = 0.0
    
    # Confidence intervals
    return_confidence_95: tuple[float, float] = (0.0, 0.0)
    sharpe_confidence_95: tuple[float, float] = (0.0, 0.0)
    drawdown_confidence_95: tuple[float, float] = (0.0, 0.0)
    
    # Risk of ruin
    probability_of_ruin: float = 0.0
    probability_of_profit: float = 0.0
    
    # All iteration results
    iteration_results: list[Dict[str, float]] = Field(default_factory=list)
