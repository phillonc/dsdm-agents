"""
Analytics Engine Module for Trading Journal AI.

This module provides comprehensive performance analytics including
by symbol, strategy, time period, and advanced metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from statistics import mean, median, stdev
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from .models import (
    Trade, TradeStatus, PerformanceMetric,
    SetupType, MarketCondition, TradeDirection
)

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Comprehensive performance analytics engine.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the analytics engine.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def calculate_performance_metrics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            user_id: User identifier
            start_date: Start date for analysis
            end_date: End date for analysis
            filters: Optional filters (symbol, setup_type, etc.)
            
        Returns:
            Dictionary of performance metrics
        """
        # Build query
        query = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.entry_date <= end_date,
            Trade.status == TradeStatus.CLOSED,
            Trade.net_pnl.isnot(None)
        )
        
        # Apply filters
        if filters:
            if 'symbol' in filters:
                query = query.filter(Trade.symbol == filters['symbol'])
            if 'setup_type' in filters:
                query = query.filter(Trade.setup_type == filters['setup_type'])
            if 'direction' in filters:
                query = query.filter(Trade.direction == filters['direction'])
            if 'market_condition' in filters:
                query = query.filter(Trade.market_condition == filters['market_condition'])
        
        trades = query.all()
        
        if not trades:
            return self._empty_metrics()
        
        # Calculate metrics
        return self._calculate_metrics_from_trades(trades, start_date, end_date)
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'gross_pnl': 0.0,
            'net_pnl': 0.0,
            'average_pnl': 0.0,
            'average_win': 0.0,
            'average_loss': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_streak': 0,
            'loss_streak': 0,
            'total_commissions': 0.0
        }
    
    def _calculate_metrics_from_trades(
        self,
        trades: List[Trade],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate all metrics from trade list."""
        winning_trades = [t for t in trades if t.net_pnl > 0]
        losing_trades = [t for t in trades if t.net_pnl <= 0]
        
        # Basic metrics
        total_trades = len(trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0
        
        # P&L metrics
        gross_pnl = sum(t.gross_pnl for t in trades if t.gross_pnl)
        net_pnl = sum(t.net_pnl for t in trades if t.net_pnl)
        average_pnl = net_pnl / total_trades if total_trades > 0 else 0.0
        
        total_wins = sum(t.net_pnl for t in winning_trades) if winning_trades else 0.0
        total_losses = abs(sum(t.net_pnl for t in losing_trades)) if losing_trades else 0.0
        
        average_win = total_wins / winning_count if winning_count > 0 else 0.0
        average_loss = -total_losses / losing_count if losing_count > 0 else 0.0
        
        all_pnls = [t.net_pnl for t in trades if t.net_pnl is not None]
        largest_win = max(all_pnls) if all_pnls else 0.0
        largest_loss = min(all_pnls) if all_pnls else 0.0
        
        # Advanced metrics
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        expectancy = (win_rate / 100 * average_win) - ((1 - win_rate / 100) * abs(average_loss))
        
        # Sharpe ratio (simplified)
        if len(all_pnls) > 1:
            returns_std = stdev(all_pnls)
            sharpe_ratio = (average_pnl / returns_std) if returns_std > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Max drawdown
        max_drawdown = self._calculate_max_drawdown(trades)
        
        # Streaks
        win_streak, loss_streak = self._calculate_streaks(trades)
        
        # Commissions
        total_commissions = sum(
            (t.entry_commission or 0) + (t.exit_commission or 0) 
            for t in trades
        )
        
        return {
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'total_trades': total_trades,
            'winning_trades': winning_count,
            'losing_trades': losing_count,
            'win_rate': round(win_rate, 2),
            'gross_pnl': round(gross_pnl, 2),
            'net_pnl': round(net_pnl, 2),
            'average_pnl': round(average_pnl, 2),
            'average_win': round(average_win, 2),
            'average_loss': round(average_loss, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'expectancy': round(expectancy, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'max_win_streak': win_streak,
            'max_loss_streak': loss_streak,
            'total_commissions': round(total_commissions, 2)
        }
    
    def _calculate_max_drawdown(self, trades: List[Trade]) -> float:
        """Calculate maximum drawdown."""
        if not trades:
            return 0.0
        
        # Sort by exit date
        sorted_trades = sorted(trades, key=lambda t: t.exit_date or t.entry_date)
        
        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0
        
        for trade in sorted_trades:
            cumulative_pnl += trade.net_pnl or 0
            
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown
    
    def _calculate_streaks(self, trades: List[Trade]) -> Tuple[int, int]:
        """Calculate max winning and losing streaks."""
        if not trades:
            return 0, 0
        
        sorted_trades = sorted(trades, key=lambda t: t.exit_date or t.entry_date)
        
        current_streak = 0
        current_type = None
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in sorted_trades:
            is_win = trade.net_pnl > 0
            
            if current_type is None:
                current_type = 'win' if is_win else 'loss'
                current_streak = 1
            elif (current_type == 'win' and is_win) or (current_type == 'loss' and not is_win):
                current_streak += 1
            else:
                if current_type == 'win':
                    max_win_streak = max(max_win_streak, current_streak)
                else:
                    max_loss_streak = max(max_loss_streak, current_streak)
                
                current_type = 'win' if is_win else 'loss'
                current_streak = 1
        
        # Check final streak
        if current_type == 'win':
            max_win_streak = max(max_win_streak, current_streak)
        else:
            max_loss_streak = max(max_loss_streak, current_streak)
        
        return max_win_streak, max_loss_streak
    
    def analyze_by_symbol(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        min_trades: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze performance by symbol.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            min_trades: Minimum trades per symbol
            
        Returns:
            Symbol performance analysis
        """
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.entry_date <= end_date,
            Trade.status == TradeStatus.CLOSED,
            Trade.net_pnl.isnot(None)
        ).all()
        
        # Group by symbol
        symbol_trades = defaultdict(list)
        for trade in trades:
            symbol_trades[trade.symbol].append(trade)
        
        # Calculate metrics per symbol
        results = {}
        for symbol, sym_trades in symbol_trades.items():
            if len(sym_trades) < min_trades:
                continue
            
            metrics = self._calculate_metrics_from_trades(sym_trades, start_date, end_date)
            results[symbol] = metrics
        
        # Sort by profitability
        sorted_results = dict(sorted(
            results.items(),
            key=lambda x: x[1]['net_pnl'],
            reverse=True
        ))
        
        return {
            'by_symbol': sorted_results,
            'most_profitable': max(results.items(), key=lambda x: x[1]['net_pnl'])[0] if results else None,
            'least_profitable': min(results.items(), key=lambda x: x[1]['net_pnl'])[0] if results else None,
            'most_traded': max(results.items(), key=lambda x: x[1]['total_trades'])[0] if results else None
        }
    
    def analyze_by_setup_type(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Analyze performance by setup type.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            
        Returns:
            Setup type performance analysis
        """
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.entry_date <= end_date,
            Trade.status == TradeStatus.CLOSED,
            Trade.setup_type.isnot(None),
            Trade.net_pnl.isnot(None)
        ).all()
        
        # Group by setup type
        setup_trades = defaultdict(list)
        for trade in trades:
            setup_trades[trade.setup_type.value].append(trade)
        
        # Calculate metrics per setup
        results = {}
        for setup, setup_list in setup_trades.items():
            metrics = self._calculate_metrics_from_trades(setup_list, start_date, end_date)
            results[setup] = metrics
        
        return {
            'by_setup': results,
            'best_setup': max(results.items(), key=lambda x: x[1]['win_rate'])[0] if results else None
        }
    
    def analyze_by_time_of_day(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Analyze performance by time of day.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            
        Returns:
            Time of day performance analysis
        """
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.entry_date <= end_date,
            Trade.status == TradeStatus.CLOSED,
            Trade.net_pnl.isnot(None)
        ).all()
        
        # Group by hour
        hourly_trades = defaultdict(list)
        for trade in trades:
            hour = trade.entry_date.hour
            hourly_trades[hour].append(trade)
        
        # Calculate metrics per hour
        results = {}
        for hour, hour_trades in hourly_trades.items():
            metrics = self._calculate_metrics_from_trades(hour_trades, start_date, end_date)
            results[f"{hour:02d}:00"] = metrics
        
        # Find best hours
        sorted_hours = sorted(
            results.items(),
            key=lambda x: x[1]['net_pnl'],
            reverse=True
        )
        
        return {
            'by_hour': dict(sorted(results.items())),
            'best_hours': [h[0] for h in sorted_hours[:3]],
            'worst_hours': [h[0] for h in sorted_hours[-3:]]
        }
    
    def analyze_by_day_of_week(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Analyze performance by day of week.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            
        Returns:
            Day of week performance analysis
        """
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.entry_date <= end_date,
            Trade.status == TradeStatus.CLOSED,
            Trade.net_pnl.isnot(None)
        ).all()
        
        # Group by day of week
        day_trades = defaultdict(list)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for trade in trades:
            day = day_names[trade.entry_date.weekday()]
            day_trades[day].append(trade)
        
        # Calculate metrics per day
        results = {}
        for day, day_list in day_trades.items():
            metrics = self._calculate_metrics_from_trades(day_list, start_date, end_date)
            results[day] = metrics
        
        return {
            'by_day': results,
            'best_day': max(results.items(), key=lambda x: x[1]['net_pnl'])[0] if results else None,
            'worst_day': min(results.items(), key=lambda x: x[1]['net_pnl'])[0] if results else None
        }
    
    def generate_equity_curve(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Generate equity curve data.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            
        Returns:
            List of equity curve data points
        """
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.entry_date <= end_date,
            Trade.status == TradeStatus.CLOSED,
            Trade.net_pnl.isnot(None)
        ).order_by(Trade.exit_date).all()
        
        equity_curve = []
        cumulative_pnl = 0.0
        
        for trade in trades:
            cumulative_pnl += trade.net_pnl or 0
            equity_curve.append({
                'date': (trade.exit_date or trade.entry_date).isoformat(),
                'trade_pnl': round(trade.net_pnl or 0, 2),
                'cumulative_pnl': round(cumulative_pnl, 2)
            })
        
        return equity_curve
    
    def calculate_monthly_performance(
        self,
        user_id: str,
        year: int
    ) -> Dict[str, Any]:
        """
        Calculate monthly performance for a year.
        
        Args:
            user_id: User identifier
            year: Year to analyze
            
        Returns:
            Monthly performance breakdown
        """
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.entry_date <= end_date,
            Trade.status == TradeStatus.CLOSED,
            Trade.net_pnl.isnot(None)
        ).all()
        
        # Group by month
        monthly_trades = defaultdict(list)
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        for trade in trades:
            month = month_names[trade.entry_date.month - 1]
            monthly_trades[month].append(trade)
        
        # Calculate metrics per month
        results = {}
        for month in month_names:
            if month in monthly_trades:
                month_start = datetime(year, month_names.index(month) + 1, 1)
                if month_names.index(month) == 11:
                    month_end = datetime(year, 12, 31, 23, 59, 59)
                else:
                    month_end = datetime(year, month_names.index(month) + 2, 1) - timedelta(seconds=1)
                
                metrics = self._calculate_metrics_from_trades(
                    monthly_trades[month],
                    month_start,
                    month_end
                )
                results[month] = metrics
            else:
                results[month] = self._empty_metrics()
        
        # Calculate year totals
        all_trades = [t for trades_list in monthly_trades.values() for t in trades_list]
        year_metrics = self._calculate_metrics_from_trades(all_trades, start_date, end_date) if all_trades else self._empty_metrics()
        
        return {
            'year': year,
            'monthly': results,
            'yearly_total': year_metrics
        }
    
    def save_performance_metric(
        self,
        user_id: str,
        metric_type: str,
        metric_key: str,
        period_start: datetime,
        period_end: datetime,
        metrics_data: Dict[str, Any]
    ) -> PerformanceMetric:
        """
        Save calculated performance metric to database.
        
        Args:
            user_id: User identifier
            metric_type: Type of metric (by_symbol, by_setup, etc.)
            metric_key: Specific key (symbol name, setup type, etc.)
            period_start: Period start date
            period_end: Period end date
            metrics_data: Calculated metrics
            
        Returns:
            PerformanceMetric object
        """
        metric = PerformanceMetric(
            user_id=user_id,
            metric_type=metric_type,
            metric_key=metric_key,
            period_start=period_start,
            period_end=period_end,
            total_trades=metrics_data.get('total_trades', 0),
            winning_trades=metrics_data.get('winning_trades', 0),
            losing_trades=metrics_data.get('losing_trades', 0),
            win_rate=metrics_data.get('win_rate', 0.0),
            total_pnl=metrics_data.get('net_pnl', 0.0),
            average_pnl=metrics_data.get('average_pnl', 0.0),
            max_win=metrics_data.get('largest_win', 0.0),
            max_loss=metrics_data.get('largest_loss', 0.0),
            profit_factor=metrics_data.get('profit_factor', 0.0),
            expectancy=metrics_data.get('expectancy', 0.0),
            metrics_data=metrics_data
        )
        
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        
        return metric
