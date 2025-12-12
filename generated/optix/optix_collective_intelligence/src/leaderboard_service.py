"""
Leaderboard Service for ranking and displaying top traders.

This service handles leaderboard generation and ranking algorithms.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from .models import LeaderboardEntry, Trader, PerformanceMetrics
from .trader_service import TraderService
from .performance_service import PerformanceService


class LeaderboardService:
    """Service for managing leaderboards."""

    def __init__(
        self,
        trader_service: TraderService,
        performance_service: PerformanceService
    ):
        """
        Initialize the leaderboard service.

        Args:
            trader_service: TraderService instance
            performance_service: PerformanceService instance
        """
        self.trader_service = trader_service
        self.performance_service = performance_service
        self._leaderboard_cache: Dict[str, tuple] = {}  # key -> (entries, timestamp)

    def get_leaderboard(
        self,
        metric: str = "total_return",
        period: str = "all_time",
        limit: int = 100,
        min_trades: int = 10
    ) -> List[LeaderboardEntry]:
        """
        Get leaderboard rankings.

        Args:
            metric: Metric to rank by (total_return, win_rate, sharpe_ratio, etc.)
            period: Time period for metrics
            limit: Maximum number of entries
            min_trades: Minimum number of trades required

        Returns:
            List of LeaderboardEntry objects
        """
        cache_key = f"{metric}:{period}:{limit}:{min_trades}"

        # Check cache (5 minute TTL)
        if cache_key in self._leaderboard_cache:
            entries, timestamp = self._leaderboard_cache[cache_key]
            if (datetime.utcnow() - timestamp).seconds < 300:
                return entries

        # Get all traders
        traders = self.trader_service.get_all_traders()

        # Calculate metrics and filter
        entries = []
        for trader in traders:
            metrics = self.performance_service.get_metrics(trader.trader_id, period)

            if metrics and metrics.total_trades >= min_trades:
                # Get metric value
                metric_value = getattr(metrics, metric, 0.0)

                entry = LeaderboardEntry(
                    trader_id=trader.trader_id,
                    username=trader.username,
                    display_name=trader.display_name,
                    avatar_url=trader.avatar_url,
                    score=self._calculate_score(metrics),
                    metric_value=metric_value,
                    verified=trader.verified
                )
                entries.append(entry)

        # Sort by metric value
        entries = sorted(entries, key=lambda x: x.metric_value, reverse=True)

        # Assign ranks and calculate changes
        for i, entry in enumerate(entries[:limit], 1):
            entry.rank = i
            # TODO: Calculate change from previous ranking

        entries = entries[:limit]

        # Cache the result
        self._leaderboard_cache[cache_key] = (entries, datetime.utcnow())

        return entries

    def get_top_performers(
        self,
        period: str = "1m",
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """
        Get top performing traders for a period.

        Args:
            period: Time period
            limit: Number of top performers

        Returns:
            List of LeaderboardEntry objects
        """
        return self.get_leaderboard(
            metric="total_return",
            period=period,
            limit=limit,
            min_trades=5
        )

    def get_most_consistent(
        self,
        period: str = "3m",
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """
        Get most consistent traders.

        Args:
            period: Time period
            limit: Number of traders

        Returns:
            List of LeaderboardEntry objects
        """
        return self.get_leaderboard(
            metric="consistency_score",
            period=period,
            limit=limit,
            min_trades=20
        )

    def get_best_risk_adjusted(
        self,
        period: str = "6m",
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """
        Get traders with best risk-adjusted returns.

        Args:
            period: Time period
            limit: Number of traders

        Returns:
            List of LeaderboardEntry objects
        """
        return self.get_leaderboard(
            metric="sharpe_ratio",
            period=period,
            limit=limit,
            min_trades=15
        )

    def get_rising_stars(
        self,
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """
        Get rising star traders (new traders performing well).

        Args:
            limit: Number of traders

        Returns:
            List of LeaderboardEntry objects
        """
        traders = self.trader_service.get_all_traders()

        # Filter for recent traders
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        recent_traders = [
            t for t in traders
            if t.joined_date >= cutoff_date
        ]

        entries = []
        for trader in recent_traders:
            metrics = self.performance_service.get_metrics(trader.trader_id, "all_time")

            if metrics and metrics.total_trades >= 5:
                entry = LeaderboardEntry(
                    trader_id=trader.trader_id,
                    username=trader.username,
                    display_name=trader.display_name,
                    avatar_url=trader.avatar_url,
                    score=self._calculate_score(metrics),
                    metric_value=metrics.total_return,
                    verified=trader.verified
                )
                entries.append(entry)

        entries = sorted(entries, key=lambda x: x.score, reverse=True)

        for i, entry in enumerate(entries[:limit], 1):
            entry.rank = i

        return entries[:limit]

    def get_trader_rank(
        self,
        trader_id: str,
        metric: str = "total_return",
        period: str = "all_time"
    ) -> Optional[int]:
        """
        Get a trader's rank for a specific metric.

        Args:
            trader_id: ID of the trader
            metric: Metric to rank by
            period: Time period

        Returns:
            Rank (1-indexed) or None if not ranked
        """
        leaderboard = self.get_leaderboard(metric=metric, period=period, limit=1000)

        for entry in leaderboard:
            if entry.trader_id == trader_id:
                return entry.rank

        return None

    def get_category_leaderboards(
        self,
        period: str = "1m"
    ) -> Dict[str, List[LeaderboardEntry]]:
        """
        Get leaderboards for multiple categories.

        Args:
            period: Time period

        Returns:
            Dictionary mapping category name to leaderboard entries
        """
        return {
            "top_performers": self.get_top_performers(period=period),
            "most_consistent": self.get_most_consistent(period=period),
            "best_risk_adjusted": self.get_best_risk_adjusted(period=period),
            "rising_stars": self.get_rising_stars()
        }

    def _calculate_score(self, metrics: PerformanceMetrics) -> float:
        """
        Calculate composite score for ranking.

        Args:
            metrics: PerformanceMetrics object

        Returns:
            Composite score
        """
        # Weighted composite score
        return (
            metrics.total_return * 0.3 +
            metrics.win_rate * 0.2 +
            metrics.sharpe_ratio * 10 * 0.2 +
            metrics.consistency_score * 0.2 +
            metrics.risk_adjusted_return * 10 * 0.1
        )

    def clear_cache(self):
        """Clear the leaderboard cache."""
        self._leaderboard_cache.clear()
