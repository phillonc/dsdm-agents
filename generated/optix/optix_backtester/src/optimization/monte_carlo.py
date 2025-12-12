"""
Monte Carlo simulation for robustness testing
"""
from typing import List, Dict, Any
import numpy as np
from uuid import uuid4

from ..models.backtest import BacktestResult, MonteCarloResult, Trade


class MonteCarloSimulator:
    """Monte Carlo simulation engine"""
    
    def __init__(self, iterations: int = 1000, seed: int = None):
        self.iterations = iterations
        if seed:
            np.random.seed(seed)
    
    def simulate(
        self,
        base_result: BacktestResult,
        method: str = "bootstrap"
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation
        
        Args:
            base_result: Base backtest result
            method: Simulation method ('bootstrap', 'resample', 'parametric')
            
        Returns:
            Monte Carlo simulation results
        """
        simulation_id = str(uuid4())
        
        if method == "bootstrap":
            iteration_results = self._bootstrap_simulation(base_result.trades)
        elif method == "resample":
            iteration_results = self._resample_simulation(base_result.trades)
        elif method == "parametric":
            iteration_results = self._parametric_simulation(base_result.trades)
        else:
            raise ValueError(f"Unknown simulation method: {method}")
        
        # Extract metrics
        returns = [r['total_return'] for r in iteration_results]
        sharpes = [r['sharpe_ratio'] for r in iteration_results]
        drawdowns = [r['max_drawdown'] for r in iteration_results]
        
        # Calculate statistics
        return MonteCarloResult(
            simulation_id=simulation_id,
            iterations=self.iterations,
            base_backtest_id=base_result.backtest_id,
            mean_return=float(np.mean(returns)),
            median_return=float(np.median(returns)),
            std_return=float(np.std(returns)),
            mean_sharpe=float(np.mean(sharpes)),
            median_sharpe=float(np.median(sharpes)),
            mean_max_drawdown=float(np.mean(drawdowns)),
            median_max_drawdown=float(np.median(drawdowns)),
            return_confidence_95=(
                float(np.percentile(returns, 2.5)),
                float(np.percentile(returns, 97.5))
            ),
            sharpe_confidence_95=(
                float(np.percentile(sharpes, 2.5)),
                float(np.percentile(sharpes, 97.5))
            ),
            drawdown_confidence_95=(
                float(np.percentile(drawdowns, 2.5)),
                float(np.percentile(drawdowns, 97.5))
            ),
            probability_of_ruin=float(np.mean([r['total_return'] < -50 for r in iteration_results])),
            probability_of_profit=float(np.mean([r['total_return'] > 0 for r in iteration_results])),
            iteration_results=iteration_results
        )
    
    def _bootstrap_simulation(
        self,
        trades: List[Trade]
    ) -> List[Dict[str, float]]:
        """
        Bootstrap resampling simulation
        
        Randomly sample trades with replacement and recalculate metrics
        """
        if not trades:
            return []
        
        results = []
        
        for _ in range(self.iterations):
            # Sample trades with replacement
            sampled_trades = np.random.choice(
                trades,
                size=len(trades),
                replace=True
            )
            
            # Calculate metrics
            metrics = self._calculate_metrics(sampled_trades)
            results.append(metrics)
        
        return results
    
    def _resample_simulation(
        self,
        trades: List[Trade]
    ) -> List[Dict[str, float]]:
        """
        Resample trades in random order
        
        Tests if trade order affects results
        """
        if not trades:
            return []
        
        results = []
        trades_list = list(trades)
        
        for _ in range(self.iterations):
            # Shuffle trade order
            shuffled_trades = trades_list.copy()
            np.random.shuffle(shuffled_trades)
            
            # Calculate metrics
            metrics = self._calculate_metrics(shuffled_trades)
            results.append(metrics)
        
        return results
    
    def _parametric_simulation(
        self,
        trades: List[Trade]
    ) -> List[Dict[str, float]]:
        """
        Parametric simulation using fitted distribution
        
        Fits distribution to returns and generates synthetic trades
        """
        if not trades:
            return []
        
        # Extract returns
        returns = np.array([t.return_percent for t in trades])
        
        # Fit normal distribution
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Get trade characteristics
        avg_capital = np.mean([abs(t.entry_price) for t in trades])
        
        results = []
        
        for _ in range(self.iterations):
            # Generate synthetic returns
            synthetic_returns = np.random.normal(mu, sigma, len(trades))
            
            # Create synthetic trades
            synthetic_pnl = synthetic_returns * avg_capital / 100
            
            # Calculate metrics
            metrics = self._calculate_metrics_from_pnl(synthetic_pnl)
            results.append(metrics)
        
        return results
    
    def _calculate_metrics(
        self,
        trades: List[Trade]
    ) -> Dict[str, float]:
        """Calculate performance metrics from trades"""
        
        if not trades:
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0
            }
        
        # P&L
        total_pnl = sum(t.net_pnl for t in trades)
        initial_capital = 100000  # Assume default
        total_return = (total_pnl / initial_capital) * 100
        
        # Returns series
        returns = np.array([t.return_percent for t in trades])
        
        # Sharpe ratio (simplified)
        if len(returns) > 1:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252 / len(returns))
        else:
            sharpe = 0.0
        
        # Max drawdown
        cumulative = np.cumsum([t.net_pnl for t in trades])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / initial_capital * 100
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
        
        # Win rate
        winners = sum(1 for t in trades if t.is_winner)
        win_rate = (winners / len(trades)) * 100
        
        return {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate)
        }
    
    def _calculate_metrics_from_pnl(
        self,
        pnl_series: np.ndarray
    ) -> Dict[str, float]:
        """Calculate metrics from P&L series"""
        
        initial_capital = 100000
        total_pnl = np.sum(pnl_series)
        total_return = (total_pnl / initial_capital) * 100
        
        # Returns
        returns = pnl_series / initial_capital * 100
        
        # Sharpe
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252 / len(returns))
        else:
            sharpe = 0.0
        
        # Drawdown
        cumulative = np.cumsum(pnl_series)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / initial_capital * 100
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
        
        # Win rate
        winners = np.sum(pnl_series > 0)
        win_rate = (winners / len(pnl_series)) * 100 if len(pnl_series) > 0 else 0
        
        return {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate)
        }
    
    def calculate_risk_of_ruin(
        self,
        base_result: BacktestResult,
        ruin_threshold: float = -50.0
    ) -> float:
        """
        Calculate probability of ruin
        
        Args:
            base_result: Base backtest result
            ruin_threshold: Threshold return considered "ruin" (%)
            
        Returns:
            Probability of ruin (0-1)
        """
        mc_result = self.simulate(base_result, method="bootstrap")
        
        ruined_iterations = sum(
            1 for r in mc_result.iteration_results 
            if r['total_return'] <= ruin_threshold
        )
        
        return ruined_iterations / self.iterations
    
    def calculate_confidence_interval(
        self,
        values: List[float],
        confidence_level: float = 0.95
    ) -> tuple[float, float]:
        """
        Calculate confidence interval
        
        Args:
            values: List of values
            confidence_level: Confidence level (0-1)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        return (
            float(np.percentile(values, lower_percentile)),
            float(np.percentile(values, upper_percentile))
        )


class ScenarioAnalysis:
    """Scenario analysis for stress testing"""
    
    def __init__(self):
        pass
    
    def stress_test(
        self,
        base_result: BacktestResult,
        scenarios: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Run stress test scenarios
        
        Args:
            base_result: Base backtest result
            scenarios: Dict of scenario name -> parameter adjustments
            
        Returns:
            Dict of scenario results
        """
        results = {}
        
        for scenario_name, adjustments in scenarios.items():
            # Apply scenario adjustments to trades
            adjusted_trades = self._apply_scenario(
                base_result.trades,
                adjustments
            )
            
            # Recalculate metrics
            # (Simplified - would need full recalculation)
            results[scenario_name] = {
                'total_pnl': sum(t.net_pnl for t in adjusted_trades),
                'num_trades': len(adjusted_trades)
            }
        
        return results
    
    def _apply_scenario(
        self,
        trades: List[Trade],
        adjustments: Dict[str, float]
    ) -> List[Trade]:
        """Apply scenario adjustments to trades"""
        
        # Create adjusted copies of trades
        adjusted_trades = []
        
        for trade in trades:
            adjusted_trade = trade.copy()
            
            # Apply adjustments
            if 'slippage_multiplier' in adjustments:
                adjusted_trade.slippage *= adjustments['slippage_multiplier']
            
            if 'commission_multiplier' in adjustments:
                adjusted_trade.commissions *= adjustments['commission_multiplier']
            
            # Recalculate net P&L
            adjusted_trade.net_pnl = (
                adjusted_trade.gross_pnl - 
                adjusted_trade.commissions - 
                adjusted_trade.slippage
            )
            
            adjusted_trades.append(adjusted_trade)
        
        return adjusted_trades
