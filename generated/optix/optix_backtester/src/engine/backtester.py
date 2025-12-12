"""
Core backtesting engine
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
from uuid import uuid4

from ..models.backtest import (
    BacktestConfig, BacktestResult, BacktestStatus,
    Trade, PerformanceMetrics
)
from ..models.option import (
    OptionStrategy, OptionLeg, OptionSide, MarketConditions
)
from ..data.market_data import MarketDataProvider, HistoricalDataReplayer
from ..execution.order_executor import OrderExecutor, FillType
from ..strategies.base import StrategyBase


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(
        self,
        data_provider: MarketDataProvider,
        config: BacktestConfig
    ):
        self.data_provider = data_provider
        self.config = config
        self.replayer = HistoricalDataReplayer(data_provider)
        self.executor = OrderExecutor(config.transaction_costs)
        
        # State
        self.capital = config.initial_capital
        self.positions: Dict[str, OptionStrategy] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        
    async def run(
        self,
        strategy: StrategyBase
    ) -> BacktestResult:
        """
        Run backtest
        
        Args:
            strategy: Trading strategy to test
            
        Returns:
            BacktestResult with complete analysis
        """
        backtest_id = str(uuid4())
        start_time = datetime.now()
        
        try:
            # Initialize result
            result = BacktestResult(
                backtest_id=backtest_id,
                status=BacktestStatus.RUNNING,
                config=self.config,
                start_time=start_time
            )
            
            # Run backtest for each symbol
            for symbol in self.config.symbols:
                await self._backtest_symbol(symbol, strategy)
            
            # Calculate performance metrics
            performance = self._calculate_performance_metrics()
            
            # Build result
            result.status = BacktestStatus.COMPLETED
            result.end_time = datetime.now()
            result.execution_time_seconds = (
                result.end_time - start_time
            ).total_seconds()
            result.trades = self.trades
            result.performance = performance
            result.equity_curve = self.equity_curve
            result.regime_performance = self._analyze_regime_performance()
            
            return result
            
        except Exception as e:
            return BacktestResult(
                backtest_id=backtest_id,
                status=BacktestStatus.FAILED,
                config=self.config,
                start_time=start_time,
                end_time=datetime.now(),
                error_message=str(e)
            )
    
    async def _backtest_symbol(
        self,
        symbol: str,
        strategy: StrategyBase
    ) -> None:
        """Backtest a single symbol"""
        
        # Get market conditions for the period
        conditions = await self.replayer.replay_session(
            symbol,
            self.config.start_date,
            self.config.end_date,
            self.config.data_frequency
        )
        
        # Iterate through time
        for condition in conditions:
            # Update strategy with current market state
            await self._update_positions(condition, strategy)
            
            # Check for new signals
            signals = await strategy.generate_signals(
                condition,
                self.positions,
                self.capital
            )
            
            # Execute signals
            for signal in signals:
                await self._execute_signal(signal, condition)
            
            # Record equity
            self._record_equity(condition.timestamp)
            
            # Check risk limits
            self._check_risk_limits()
    
    async def _execute_signal(
        self,
        strategy: OptionStrategy,
        condition: MarketConditions
    ) -> None:
        """Execute a strategy signal"""
        
        # Get quotes for the strategy legs
        quotes = await self.replayer.get_option_quotes_at_time(
            condition.underlying_symbol,
            condition.timestamp
        )
        
        # Build quote map
        quote_map = {
            q.contract.contract_symbol: q for q in quotes
        }
        
        total_cost = 0.0
        total_commission = 0.0
        total_slippage = 0.0
        
        # Execute each leg
        for leg in strategy.legs:
            quote = quote_map.get(leg.contract.contract_symbol)
            if not quote:
                continue  # Skip if no quote available
            
            # Execute order
            fill_price, commission, slippage = self.executor.execute_market_order(
                quote, leg.side, leg.quantity
            )
            
            # Update leg with execution details
            leg.entry_price = fill_price
            
            # Track costs
            multiplier = 1 if leg.side == OptionSide.BUY else -1
            total_cost += fill_price * leg.quantity * multiplier * 100
            total_commission += commission
            total_slippage += slippage
        
        # Update capital
        self.capital -= (total_cost + total_commission + total_slippage)
        
        # Add to positions
        strategy.entry_time = condition.timestamp
        self.positions[strategy.strategy_id] = strategy
    
    async def _update_positions(
        self,
        condition: MarketConditions,
        strategy: StrategyBase
    ) -> None:
        """Update existing positions and check exits"""
        
        positions_to_close = []
        
        for strategy_id, position in self.positions.items():
            # Check if strategy should be closed
            should_exit, exit_reason = await strategy.should_exit(
                position, condition, self.capital
            )
            
            if should_exit:
                positions_to_close.append((strategy_id, exit_reason))
        
        # Close positions
        for strategy_id, exit_reason in positions_to_close:
            await self._close_position(strategy_id, condition, exit_reason)
    
    async def _close_position(
        self,
        strategy_id: str,
        condition: MarketConditions,
        exit_reason: str
    ) -> None:
        """Close a position"""
        
        position = self.positions.get(strategy_id)
        if not position:
            return
        
        # Get current quotes
        quotes = await self.replayer.get_option_quotes_at_time(
            condition.underlying_symbol,
            condition.timestamp
        )
        
        quote_map = {
            q.contract.contract_symbol: q for q in quotes
        }
        
        total_proceeds = 0.0
        total_commission = 0.0
        total_slippage = 0.0
        entry_cost = 0.0
        
        # Close each leg (reverse the position)
        for leg in position.legs:
            if leg.entry_price is None:
                continue
            
            quote = quote_map.get(leg.contract.contract_symbol)
            if not quote:
                continue
            
            # Reverse the side for closing
            close_side = OptionSide.SELL if leg.side == OptionSide.BUY else OptionSide.BUY
            
            # Execute close
            fill_price, commission, slippage = self.executor.execute_market_order(
                quote, close_side, leg.quantity
            )
            
            leg.exit_price = fill_price
            
            # Calculate proceeds (opposite sign of entry)
            multiplier = 1 if close_side == OptionSide.BUY else -1
            total_proceeds -= fill_price * leg.quantity * multiplier * 100
            
            # Entry cost
            entry_multiplier = 1 if leg.side == OptionSide.BUY else -1
            entry_cost += leg.entry_price * leg.quantity * entry_multiplier * 100
            
            total_commission += commission
            total_slippage += slippage
        
        # Calculate P&L
        gross_pnl = total_proceeds + entry_cost
        net_pnl = gross_pnl - total_commission - total_slippage
        
        # Update capital
        self.capital += total_proceeds - total_commission - total_slippage
        
        # Create trade record
        trade = Trade(
            trade_id=str(uuid4()),
            strategy_id=strategy_id,
            entry_time=position.entry_time,
            exit_time=condition.timestamp,
            underlying_symbol=condition.underlying_symbol,
            legs_count=len(position.legs),
            entry_price=abs(entry_cost),
            exit_price=abs(total_proceeds),
            gross_pnl=gross_pnl,
            commissions=total_commission,
            slippage=total_slippage,
            net_pnl=net_pnl,
            return_percent=(net_pnl / abs(entry_cost) * 100) if entry_cost != 0 else 0,
            exit_reason=exit_reason
        )
        
        self.trades.append(trade)
        
        # Remove from positions
        position.exit_time = condition.timestamp
        del self.positions[strategy_id]
    
    def _record_equity(self, timestamp: datetime) -> None:
        """Record current equity"""
        
        # Calculate mark-to-market value of positions
        # (simplified - in reality would need current quotes)
        positions_value = sum(
            pos.calculate_cost_basis() for pos in self.positions.values()
        )
        
        total_equity = self.capital + positions_value
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': total_equity,
            'cash': self.capital,
            'positions_value': positions_value,
            'num_positions': len(self.positions)
        })
    
    def _check_risk_limits(self) -> None:
        """Check and enforce risk limits"""
        
        if self.config.max_daily_loss:
            daily_pnl = self._calculate_daily_pnl()
            if daily_pnl < -self.config.max_daily_loss:
                # Close all positions (simplified)
                pass
    
    def _calculate_daily_pnl(self) -> float:
        """Calculate P&L for current day"""
        if not self.equity_curve:
            return 0.0
        
        current_equity = self.equity_curve[-1]['equity']
        start_of_day_equity = self.config.initial_capital
        
        # Find start of day equity
        for entry in reversed(self.equity_curve[:-1]):
            if entry['timestamp'].date() < self.equity_curve[-1]['timestamp'].date():
                break
            start_of_day_equity = entry['equity']
        
        return current_equity - start_of_day_equity
    
    def _calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        if not self.trades:
            return PerformanceMetrics()
        
        # Basic counts
        winning_trades = [t for t in self.trades if t.is_winner]
        losing_trades = [t for t in self.trades if not t.is_winner]
        
        total_trades = len(self.trades)
        num_winners = len(winning_trades)
        num_losers = len(losing_trades)
        
        # P&L metrics
        total_pnl = sum(t.net_pnl for t in self.trades)
        gross_profit = sum(t.net_pnl for t in winning_trades)
        gross_loss = abs(sum(t.net_pnl for t in losing_trades))
        
        # Returns
        total_return = (total_pnl / self.config.initial_capital) * 100
        
        # Calculate annualized return
        days = (self.config.end_date - self.config.start_date).days
        years = days / 365.25
        annualized_return = (
            (1 + total_return / 100) ** (1 / years) - 1
        ) * 100 if years > 0 else 0
        
        # Drawdown
        equity_series = pd.Series([e['equity'] for e in self.equity_curve])
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax * 100
        max_drawdown_pct = abs(drawdown.min()) if len(drawdown) > 0 else 0
        max_drawdown = abs((equity_series - cummax).min())
        
        # Returns for Sharpe/Sortino
        if len(self.equity_curve) > 1:
            returns = pd.Series([
                (self.equity_curve[i]['equity'] - self.equity_curve[i-1]['equity']) / 
                self.equity_curve[i-1]['equity']
                for i in range(1, len(self.equity_curve))
            ])
            
            volatility = returns.std() * np.sqrt(252)
            sharpe_ratio = (
                (annualized_return / 100 - 0.04) / volatility
            ) if volatility > 0 else 0
            
            # Sortino - only downside deviation
            downside_returns = returns[returns < 0]
            downside_dev = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
            sortino_ratio = (
                (annualized_return / 100 - 0.04) / downside_dev
            ) if downside_dev > 0 else 0
        else:
            volatility = 0
            sharpe_ratio = 0
            sortino_ratio = 0
            downside_dev = 0
        
        # Trade statistics
        avg_win = gross_profit / num_winners if num_winners > 0 else 0
        avg_loss = gross_loss / num_losers if num_losers > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Time metrics
        holding_periods = [
            t.holding_period_seconds / 3600 
            for t in self.trades 
            if t.holding_period_seconds
        ]
        avg_holding_hours = np.mean(holding_periods) if holding_periods else 0
        
        # Consecutive wins/losses
        max_consec_wins = 0
        max_consec_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade.is_winner:
                current_wins += 1
                current_losses = 0
                max_consec_wins = max(max_consec_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consec_losses = max(max_consec_losses, current_losses)
        
        # Risk metrics
        returns_list = [t.net_pnl for t in self.trades]
        var_95 = np.percentile(returns_list, 5) if returns_list else 0
        cvar_95 = np.mean([r for r in returns_list if r <= var_95]) if returns_list else 0
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=num_winners,
            losing_trades=num_losers,
            win_rate=(num_winners / total_trades * 100) if total_trades > 0 else 0,
            total_pnl=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            max_drawdown_percent=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=annualized_return / max_drawdown_pct if max_drawdown_pct > 0 else 0,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=max([t.net_pnl for t in self.trades], default=0),
            largest_loss=min([t.net_pnl for t in self.trades], default=0),
            avg_trade=total_pnl / total_trades if total_trades > 0 else 0,
            avg_holding_period_hours=avg_holding_hours,
            max_consecutive_wins=max_consec_wins,
            max_consecutive_losses=max_consec_losses,
            volatility=volatility,
            downside_deviation=downside_dev,
            var_95=var_95,
            cvar_95=cvar_95,
            expectancy=(
                (num_winners / total_trades * avg_win) - 
                (num_losers / total_trades * avg_loss)
            ) if total_trades > 0 else 0
        )
    
    def _analyze_regime_performance(self) -> Dict[str, PerformanceMetrics]:
        """Analyze performance by volatility regime"""
        
        # Group trades by regime (simplified - would need regime data)
        regimes = ['low', 'medium', 'high']
        regime_perf = {}
        
        for regime in regimes:
            # Filter trades by regime (placeholder)
            regime_trades = self.trades  # Would filter by actual regime
            
            if regime_trades:
                # Calculate metrics for regime (simplified)
                regime_perf[regime] = PerformanceMetrics(
                    total_trades=len(regime_trades)
                )
        
        return regime_perf
