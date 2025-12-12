"""
Walk-forward optimization to prevent overfitting
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
from uuid import uuid4

from ..models.backtest import (
    BacktestConfig, BacktestResult, WalkForwardResult,
    PerformanceMetrics
)
from ..engine.backtester import BacktestEngine
from ..strategies.base import StrategyBase
from ..data.market_data import MarketDataProvider


class WalkForwardOptimizer:
    """Walk-forward optimization engine"""
    
    def __init__(
        self,
        data_provider: MarketDataProvider,
        train_ratio: float = 0.7,
        num_periods: int = 5
    ):
        self.data_provider = data_provider
        self.train_ratio = train_ratio
        self.num_periods = num_periods
    
    async def optimize(
        self,
        base_config: BacktestConfig,
        strategy_class: type,
        param_grid: Dict[str, List[Any]]
    ) -> WalkForwardResult:
        """
        Run walk-forward optimization
        
        Args:
            base_config: Base backtest configuration
            strategy_class: Strategy class to optimize
            param_grid: Parameter grid to search
            
        Returns:
            Walk-forward optimization results
        """
        optimization_id = str(uuid4())
        
        # Split time period into windows
        windows = self._create_windows(
            base_config.start_date,
            base_config.end_date,
            self.num_periods
        )
        
        in_sample_results: List[BacktestResult] = []
        out_of_sample_results: List[BacktestResult] = []
        
        # Process each window
        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            print(f"Processing window {i+1}/{len(windows)}")
            
            # Optimize on in-sample period
            best_params = await self._optimize_period(
                base_config,
                strategy_class,
                param_grid,
                train_start,
                train_end
            )
            
            # Test on out-of-sample period
            is_result = await self._run_backtest(
                base_config,
                strategy_class,
                best_params,
                train_start,
                train_end
            )
            in_sample_results.append(is_result)
            
            oos_result = await self._run_backtest(
                base_config,
                strategy_class,
                best_params,
                test_start,
                test_end
            )
            out_of_sample_results.append(oos_result)
        
        # Calculate combined metrics
        combined_performance = self._combine_metrics(out_of_sample_results)
        
        # Calculate degradation
        is_sharpe = np.mean([r.performance.sharpe_ratio for r in in_sample_results])
        oos_sharpe = np.mean([r.performance.sharpe_ratio for r in out_of_sample_results])
        degradation = ((is_sharpe - oos_sharpe) / is_sharpe * 100) if is_sharpe != 0 else 0
        
        # Calculate stability
        oos_sharpes = [r.performance.sharpe_ratio for r in out_of_sample_results]
        sharpe_stability = 1 - (np.std(oos_sharpes) / np.mean(oos_sharpes)) if np.mean(oos_sharpes) != 0 else 0
        
        return WalkForwardResult(
            optimization_id=optimization_id,
            total_periods=len(windows),
            train_ratio=self.train_ratio,
            in_sample_results=in_sample_results,
            out_of_sample_results=out_of_sample_results,
            combined_performance=combined_performance,
            in_sample_sharpe=is_sharpe,
            out_of_sample_sharpe=oos_sharpe,
            degradation_percent=degradation,
            sharpe_stability=max(0, sharpe_stability)
        )
    
    def _create_windows(
        self,
        start_date: datetime,
        end_date: datetime,
        num_periods: int
    ) -> List[tuple]:
        """
        Create walk-forward windows
        
        Args:
            start_date: Overall start date
            end_date: Overall end date
            num_periods: Number of periods
            
        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        total_days = (end_date - start_date).days
        period_days = total_days // num_periods
        
        windows = []
        
        for i in range(num_periods):
            period_start = start_date + timedelta(days=i * period_days)
            period_end = period_start + timedelta(days=period_days)
            
            # Split into train/test
            train_days = int(period_days * self.train_ratio)
            train_start = period_start
            train_end = period_start + timedelta(days=train_days)
            test_start = train_end
            test_end = period_end
            
            windows.append((train_start, train_end, test_start, test_end))
        
        return windows
    
    async def _optimize_period(
        self,
        base_config: BacktestConfig,
        strategy_class: type,
        param_grid: Dict[str, List[Any]],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Optimize parameters for a single period
        
        Args:
            base_config: Base configuration
            strategy_class: Strategy class
            param_grid: Parameter grid
            start_date: Period start
            end_date: Period end
            
        Returns:
            Best parameters
        """
        best_sharpe = -np.inf
        best_params = {}
        
        # Generate parameter combinations
        param_combinations = self._generate_param_combinations(param_grid)
        
        for params in param_combinations:
            result = await self._run_backtest(
                base_config,
                strategy_class,
                params,
                start_date,
                end_date
            )
            
            if result.performance.sharpe_ratio > best_sharpe:
                best_sharpe = result.performance.sharpe_ratio
                best_params = params
        
        return best_params
    
    def _generate_param_combinations(
        self,
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """Generate all parameter combinations"""
        if not param_grid:
            return [{}]
        
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        
        combinations = []
        
        def recurse(index: int, current: Dict[str, Any]):
            if index == len(keys):
                combinations.append(current.copy())
                return
            
            key = keys[index]
            for value in values[index]:
                current[key] = value
                recurse(index + 1, current)
        
        recurse(0, {})
        return combinations
    
    async def _run_backtest(
        self,
        base_config: BacktestConfig,
        strategy_class: type,
        params: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:
        """Run single backtest"""
        config = BacktestConfig(
            initial_capital=base_config.initial_capital,
            start_date=start_date,
            end_date=end_date,
            symbols=base_config.symbols,
            transaction_costs=base_config.transaction_costs,
            max_position_size=base_config.max_position_size,
            max_positions=base_config.max_positions,
            strategy_params=params
        )
        
        engine = BacktestEngine(self.data_provider, config)
        strategy = strategy_class(params=params)
        
        return await engine.run(strategy)
    
    def _combine_metrics(
        self,
        results: List[BacktestResult]
    ) -> PerformanceMetrics:
        """Combine metrics from multiple results"""
        
        if not results:
            return PerformanceMetrics()
        
        # Aggregate trades
        all_trades = []
        for result in results:
            all_trades.extend(result.trades)
        
        if not all_trades:
            return PerformanceMetrics()
        
        # Calculate combined metrics
        winning_trades = [t for t in all_trades if t.is_winner]
        losing_trades = [t for t in all_trades if not t.is_winner]
        
        total_pnl = sum(t.net_pnl for t in all_trades)
        gross_profit = sum(t.net_pnl for t in winning_trades)
        gross_loss = abs(sum(t.net_pnl for t in losing_trades))
        
        return PerformanceMetrics(
            total_trades=len(all_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=(len(winning_trades) / len(all_trades) * 100),
            total_pnl=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=gross_profit / gross_loss if gross_loss > 0 else 0,
            avg_win=gross_profit / len(winning_trades) if winning_trades else 0,
            avg_loss=gross_loss / len(losing_trades) if losing_trades else 0,
            sharpe_ratio=np.mean([r.performance.sharpe_ratio for r in results]),
            sortino_ratio=np.mean([r.performance.sortino_ratio for r in results]),
            max_drawdown=max([r.performance.max_drawdown for r in results], default=0)
        )
