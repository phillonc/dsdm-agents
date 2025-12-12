"""
Performance Service for calculating and managing trader performance metrics.

This service handles performance calculations, analytics, and metrics.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import math
from .models import Trade, PerformanceMetrics, TradeStatus
from .exceptions import NotFoundError, ValidationError


class PerformanceService:
    """Service for managing performance metrics."""

    def __init__(self):
        """Initialize the performance service."""
        self._metrics_cache: Dict[str, Dict[str, PerformanceMetrics]] = {}
        self._trades: Dict[str, Trade] = {}
        self._trader_trades_index: Dict[str, List[str]] = {}

    def add_trade(self, trade: Trade) -> Trade:
        """
        Add a trade to the performance tracking system.

        Args:
            trade: Trade object to add

        Returns:
            The added Trade object
        """
        self._trades[trade.trade_id] = trade

        if trade.trader_id not in self._trader_trades_index:
            self._trader_trades_index[trade.trader_id] = []
        self._trader_trades_index[trade.trader_id].append(trade.trade_id)

        # Invalidate cache for this trader
        if trade.trader_id in self._metrics_cache:
            del self._metrics_cache[trade.trader_id]

        return trade

    def get_trader_trades(
        self,
        trader_id: str,
        status: Optional[TradeStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Trade]:
        """
        Get trades for a specific trader.

        Args:
            trader_id: ID of the trader
            status: Optional status filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of Trade objects
        """
        trade_ids = self._trader_trades_index.get(trader_id, [])
        trades = [self._trades[tid] for tid in trade_ids if tid in self._trades]

        if status:
            trades = [t for t in trades if t.status == status]

        if start_date:
            trades = [t for t in trades if t.opened_at >= start_date]

        if end_date:
            trades = [t for t in trades if t.opened_at <= end_date]

        return sorted(trades, key=lambda x: x.opened_at, reverse=True)

    def calculate_metrics(
        self,
        trader_id: str,
        period: str = "all_time",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PerformanceMetrics:
        """
        Calculate performance metrics for a trader.

        Args:
            trader_id: ID of the trader
            period: Time period (all_time, 1y, 6m, 3m, 1m, 1w)
            start_date: Optional custom start date
            end_date: Optional custom end date

        Returns:
            PerformanceMetrics object

        Raises:
            ValidationError: If period is invalid
        """
        # Check cache first
        cache_key = f"{trader_id}:{period}"
        if cache_key in self._metrics_cache.get(trader_id, {}):
            cached = self._metrics_cache[trader_id][cache_key]
            if (datetime.utcnow() - cached.calculated_at).seconds < 300:  # 5 min cache
                return cached

        # Determine date range
        if not start_date:
            if period == "1w":
                start_date = datetime.utcnow() - timedelta(days=7)
            elif period == "1m":
                start_date = datetime.utcnow() - timedelta(days=30)
            elif period == "3m":
                start_date = datetime.utcnow() - timedelta(days=90)
            elif period == "6m":
                start_date = datetime.utcnow() - timedelta(days=180)
            elif period == "1y":
                start_date = datetime.utcnow() - timedelta(days=365)

        if not end_date:
            end_date = datetime.utcnow()

        # Get closed trades for the period
        trades = self.get_trader_trades(
            trader_id,
            status=TradeStatus.CLOSED,
            start_date=start_date,
            end_date=end_date
        )

        if not trades:
            return PerformanceMetrics(
                trader_id=trader_id,
                period=period
            )

        # Calculate basic metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.profit_loss > 0)
        losing_trades = sum(1 for t in trades if t.profit_loss < 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        # Calculate returns
        returns = [t.profit_loss_percentage for t in trades]
        total_return = sum(returns)
        average_return = total_return / total_trades if total_trades > 0 else 0.0
        best_trade = max(returns) if returns else 0.0
        worst_trade = min(returns) if returns else 0.0

        # Calculate trade duration
        durations = [
            (t.closed_at - t.opened_at).total_seconds() / 3600
            for t in trades if t.closed_at
        ]
        average_duration = sum(durations) / len(durations) if durations else 0.0

        # Calculate advanced metrics
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        sortino_ratio = self._calculate_sortino_ratio(returns)
        max_drawdown = self._calculate_max_drawdown(trades)
        profit_factor = self._calculate_profit_factor(trades)
        consistency_score = self._calculate_consistency_score(returns)
        risk_adjusted_return = self._calculate_risk_adjusted_return(
            average_return,
            returns
        )

        metrics = PerformanceMetrics(
            trader_id=trader_id,
            period=period,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            average_return=average_return,
            best_trade=best_trade,
            worst_trade=worst_trade,
            average_trade_duration=average_duration,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            consistency_score=consistency_score,
            risk_adjusted_return=risk_adjusted_return
        )

        # Cache the result
        if trader_id not in self._metrics_cache:
            self._metrics_cache[trader_id] = {}
        self._metrics_cache[trader_id][cache_key] = metrics

        return metrics

    def _calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sharpe ratio."""
        if not returns or len(returns) < 2:
            return 0.0

        avg_return = sum(returns) / len(returns)
        std_dev = math.sqrt(
            sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        )

        if std_dev == 0:
            return 0.0

        return (avg_return - risk_free_rate) / std_dev

    def _calculate_sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if not returns or len(returns) < 2:
            return 0.0

        avg_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return 0.0

        downside_dev = math.sqrt(
            sum(r ** 2 for r in downside_returns) / len(downside_returns)
        )

        if downside_dev == 0:
            return 0.0

        return (avg_return - risk_free_rate) / downside_dev

    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """Calculate maximum drawdown."""
        if not trades:
            return 0.0

        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0

        for trade in sorted(trades, key=lambda x: x.opened_at):
            cumulative += trade.profit_loss_percentage
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_profit_factor(self, trades: List[Trade]) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if not trades:
            return 0.0

        gross_profit = sum(t.profit_loss for t in trades if t.profit_loss > 0)
        gross_loss = abs(sum(t.profit_loss for t in trades if t.profit_loss < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def _calculate_consistency_score(self, returns: List[float]) -> float:
        """Calculate consistency score (0-100)."""
        if not returns or len(returns) < 3:
            return 0.0

        # Calculate coefficient of variation
        avg_return = sum(returns) / len(returns)
        if avg_return == 0:
            return 0.0

        std_dev = math.sqrt(
            sum((r - avg_return) ** 2 for r in returns) / len(returns)
        )
        cv = std_dev / abs(avg_return)

        # Convert to 0-100 score (lower CV = higher consistency)
        consistency = max(0, min(100, 100 - (cv * 20)))
        return consistency

    def _calculate_risk_adjusted_return(
        self,
        avg_return: float,
        returns: List[float]
    ) -> float:
        """Calculate risk-adjusted return."""
        if not returns or len(returns) < 2:
            return 0.0

        std_dev = math.sqrt(
            sum((r - avg_return) ** 2 for r in returns) / len(returns)
        )

        if std_dev == 0:
            return 0.0

        return avg_return / std_dev

    def get_metrics(
        self,
        trader_id: str,
        period: str = "all_time"
    ) -> Optional[PerformanceMetrics]:
        """
        Get cached metrics or calculate if not available.

        Args:
            trader_id: ID of the trader
            period: Time period

        Returns:
            PerformanceMetrics object or None
        """
        return self.calculate_metrics(trader_id, period)

    def compare_traders(
        self,
        trader_ids: List[str],
        period: str = "all_time"
    ) -> Dict[str, PerformanceMetrics]:
        """
        Compare performance metrics for multiple traders.

        Args:
            trader_ids: List of trader IDs
            period: Time period

        Returns:
            Dictionary mapping trader_id to PerformanceMetrics
        """
        return {
            trader_id: self.calculate_metrics(trader_id, period)
            for trader_id in trader_ids
        }
