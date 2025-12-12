"""
Pattern Analyzer Module for Trading Journal AI.

This module discovers patterns in trading history including win rates by setup,
time of day analysis, market condition correlations, and behavioral patterns.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from statistics import mean, median, stdev
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .models import (
    Trade, TradeStatus, SetupType, MarketCondition, 
    Sentiment, TradeDirection
)

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """
    AI-powered pattern discovery engine for trading analysis.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the pattern analyzer.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def analyze_setup_performance(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_trades: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze performance by setup type.
        
        Args:
            user_id: User identifier
            start_date: Optional start date
            end_date: Optional end date
            min_trades: Minimum trades required for analysis
            
        Returns:
            Dictionary with setup performance analysis
        """
        query = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.status == TradeStatus.CLOSED,
            Trade.setup_type.isnot(None),
            Trade.net_pnl.isnot(None)
        )
        
        if start_date:
            query = query.filter(Trade.entry_date >= start_date)
        if end_date:
            query = query.filter(Trade.entry_date <= end_date)
        
        trades = query.all()
        
        # Group by setup type
        setup_stats = defaultdict(lambda: {
            'trades': [],
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'pnl_list': []
        })
        
        for trade in trades:
            setup = trade.setup_type.value
            stats = setup_stats[setup]
            
            stats['trades'].append(trade)
            stats['pnl_list'].append(trade.net_pnl)
            stats['total_pnl'] += trade.net_pnl
            
            if trade.net_pnl > 0:
                stats['winning_trades'] += 1
            else:
                stats['losing_trades'] += 1
        
        # Calculate metrics
        results = {}
        for setup, stats in setup_stats.items():
            total_trades = len(stats['trades'])
            
            if total_trades < min_trades:
                continue
            
            win_rate = (stats['winning_trades'] / total_trades * 100) if total_trades > 0 else 0
            avg_pnl = stats['total_pnl'] / total_trades if total_trades > 0 else 0
            
            winning_pnls = [t.net_pnl for t in stats['trades'] if t.net_pnl > 0]
            losing_pnls = [t.net_pnl for t in stats['trades'] if t.net_pnl <= 0]
            
            avg_win = mean(winning_pnls) if winning_pnls else 0
            avg_loss = mean(losing_pnls) if losing_pnls else 0
            
            profit_factor = abs(sum(winning_pnls) / sum(losing_pnls)) if losing_pnls and sum(losing_pnls) != 0 else 0
            
            results[setup] = {
                'total_trades': total_trades,
                'winning_trades': stats['winning_trades'],
                'losing_trades': stats['losing_trades'],
                'win_rate': round(win_rate, 2),
                'total_pnl': round(stats['total_pnl'], 2),
                'average_pnl': round(avg_pnl, 2),
                'average_win': round(avg_win, 2),
                'average_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'max_win': round(max(stats['pnl_list']), 2) if stats['pnl_list'] else 0,
                'max_loss': round(min(stats['pnl_list']), 2) if stats['pnl_list'] else 0
            }
        
        # Sort by profitability
        sorted_results = dict(sorted(
            results.items(),
            key=lambda x: x[1]['total_pnl'],
            reverse=True
        ))
        
        return {
            'setup_performance': sorted_results,
            'best_setup': max(results.items(), key=lambda x: x[1]['total_pnl'])[0] if results else None,
            'worst_setup': min(results.items(), key=lambda x: x[1]['total_pnl'])[0] if results else None,
            'highest_win_rate': max(results.items(), key=lambda x: x[1]['win_rate'])[0] if results else None
        }
    
    def analyze_time_of_day_patterns(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analyze performance by time of day.
        
        Args:
            user_id: User identifier
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dictionary with time-of-day analysis
        """
        query = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.status == TradeStatus.CLOSED,
            Trade.net_pnl.isnot(None)
        )
        
        if start_date:
            query = query.filter(Trade.entry_date >= start_date)
        if end_date:
            query = query.filter(Trade.entry_date <= end_date)
        
        trades = query.all()
        
        # Group by hour
        hourly_stats = defaultdict(lambda: {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'pnl_list': []
        })
        
        for trade in trades:
            hour = trade.entry_date.hour
            stats = hourly_stats[hour]
            
            stats['trades'] += 1
            stats['pnl_list'].append(trade.net_pnl)
            stats['total_pnl'] += trade.net_pnl
            
            if trade.net_pnl > 0:
                stats['wins'] += 1
            else:
                stats['losses'] += 1
        
        # Calculate metrics
        results = {}
        for hour, stats in hourly_stats.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['total_pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            
            results[f"{hour:02d}:00"] = {
                'total_trades': stats['trades'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': round(win_rate, 2),
                'total_pnl': round(stats['total_pnl'], 2),
                'average_pnl': round(avg_pnl, 2)
            }
        
        # Find best trading hours
        best_hours = sorted(
            results.items(),
            key=lambda x: x[1]['total_pnl'],
            reverse=True
        )[:3]
        
        worst_hours = sorted(
            results.items(),
            key=lambda x: x[1]['total_pnl']
        )[:3]
        
        return {
            'hourly_performance': dict(sorted(results.items())),
            'best_trading_hours': [h[0] for h in best_hours],
            'worst_trading_hours': [h[0] for h in worst_hours],
            'morning_performance': self._aggregate_time_range(results, 6, 12),
            'afternoon_performance': self._aggregate_time_range(results, 12, 16),
            'closing_performance': self._aggregate_time_range(results, 15, 17)
        }
    
    def _aggregate_time_range(
        self,
        hourly_results: Dict[str, Any],
        start_hour: int,
        end_hour: int
    ) -> Dict[str, Any]:
        """
        Aggregate hourly results for a time range.
        
        Args:
            hourly_results: Hourly performance data
            start_hour: Start hour (inclusive)
            end_hour: End hour (exclusive)
            
        Returns:
            Aggregated metrics
        """
        total_trades = 0
        total_wins = 0
        total_pnl = 0.0
        
        for hour in range(start_hour, end_hour):
            key = f"{hour:02d}:00"
            if key in hourly_results:
                stats = hourly_results[key]
                total_trades += stats['total_trades']
                total_wins += stats['wins']
                total_pnl += stats['total_pnl']
        
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2)
        }
    
    def analyze_market_conditions(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analyze performance under different market conditions.
        
        Args:
            user_id: User identifier
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dictionary with market condition analysis
        """
        query = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.status == TradeStatus.CLOSED,
            Trade.market_condition.isnot(None),
            Trade.net_pnl.isnot(None)
        )
        
        if start_date:
            query = query.filter(Trade.entry_date >= start_date)
        if end_date:
            query = query.filter(Trade.entry_date <= end_date)
        
        trades = query.all()
        
        # Group by market condition
        condition_stats = defaultdict(lambda: {
            'trades': 0,
            'wins': 0,
            'total_pnl': 0.0
        })
        
        for trade in trades:
            condition = trade.market_condition.value
            stats = condition_stats[condition]
            
            stats['trades'] += 1
            stats['total_pnl'] += trade.net_pnl
            
            if trade.net_pnl > 0:
                stats['wins'] += 1
        
        # Calculate metrics
        results = {}
        for condition, stats in condition_stats.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            
            results[condition] = {
                'total_trades': stats['trades'],
                'wins': stats['wins'],
                'win_rate': round(win_rate, 2),
                'total_pnl': round(stats['total_pnl'], 2)
            }
        
        return {
            'market_condition_performance': results,
            'best_condition': max(results.items(), key=lambda x: x[1]['total_pnl'])[0] if results else None,
            'worst_condition': min(results.items(), key=lambda x: x[1]['total_pnl'])[0] if results else None
        }
    
    def detect_behavioral_patterns(
        self,
        user_id: str,
        lookback_days: int = 90
    ) -> Dict[str, Any]:
        """
        Detect behavioral patterns like FOMO trades, revenge trading, overtrading.
        
        Args:
            user_id: User identifier
            lookback_days: Number of days to analyze
            
        Returns:
            Dictionary with behavioral pattern analysis
        """
        start_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.status == TradeStatus.CLOSED
        ).order_by(Trade.entry_date).all()
        
        if not trades:
            return {'patterns': [], 'warnings': []}
        
        patterns = []
        warnings = []
        
        # Detect FOMO patterns (trades after big wins with higher risk)
        fomo_trades = self._detect_fomo_trades(trades)
        if fomo_trades:
            patterns.append({
                'type': 'FOMO',
                'count': len(fomo_trades),
                'description': 'Trades entered impulsively after large wins',
                'avg_pnl': round(mean([t.net_pnl for t in fomo_trades]), 2)
            })
            
            if len(fomo_trades) > len(trades) * 0.2:  # More than 20% are FOMO
                warnings.append("High frequency of FOMO trades detected. Consider taking breaks after big wins.")
        
        # Detect revenge trading (quick trades after losses)
        revenge_trades = self._detect_revenge_trades(trades)
        if revenge_trades:
            patterns.append({
                'type': 'REVENGE',
                'count': len(revenge_trades),
                'description': 'Quick trades entered after losses',
                'avg_pnl': round(mean([t.net_pnl for t in revenge_trades]), 2)
            })
            
            if len(revenge_trades) > len(trades) * 0.15:  # More than 15% are revenge
                warnings.append("Revenge trading pattern detected. Take time to reset after losses.")
        
        # Detect overtrading (excessive trades on certain days)
        overtraded_days = self._detect_overtrading(trades)
        if overtraded_days:
            patterns.append({
                'type': 'OVERTRADING',
                'count': len(overtraded_days),
                'description': 'Days with excessive number of trades',
                'avg_trades_per_day': round(mean([d['trade_count'] for d in overtraded_days]), 2)
            })
            
            warnings.append(f"Overtrading detected on {len(overtraded_days)} days. Consider setting daily trade limits.")
        
        # Analyze sentiment correlation with performance
        sentiment_analysis = self._analyze_sentiment_performance(trades)
        if sentiment_analysis:
            patterns.append({
                'type': 'SENTIMENT',
                'data': sentiment_analysis,
                'description': 'Performance correlation with trading sentiment'
            })
        
        # Detect winning/losing streaks
        streaks = self._detect_streaks(trades)
        if streaks:
            patterns.append({
                'type': 'STREAKS',
                'data': streaks,
                'description': 'Winning and losing streak analysis'
            })
        
        return {
            'patterns': patterns,
            'warnings': warnings,
            'total_trades_analyzed': len(trades)
        }
    
    def _detect_fomo_trades(self, trades: List[Trade]) -> List[Trade]:
        """Detect FOMO trades - trades entered quickly after large wins."""
        fomo_trades = []
        
        for i in range(1, len(trades)):
            prev_trade = trades[i - 1]
            current_trade = trades[i]
            
            # Check if previous trade was a big win
            if prev_trade.net_pnl and prev_trade.net_pnl > 0:
                # Check if current trade was entered within 30 minutes
                time_diff = (current_trade.entry_date - prev_trade.exit_date).total_seconds() / 60
                
                if time_diff < 30 and current_trade.sentiment == Sentiment.FOMO:
                    fomo_trades.append(current_trade)
                    current_trade.is_fomo = True
        
        return fomo_trades
    
    def _detect_revenge_trades(self, trades: List[Trade]) -> List[Trade]:
        """Detect revenge trades - quick trades after losses."""
        revenge_trades = []
        
        for i in range(1, len(trades)):
            prev_trade = trades[i - 1]
            current_trade = trades[i]
            
            # Check if previous trade was a loss
            if prev_trade.net_pnl and prev_trade.net_pnl < 0:
                # Check if current trade was entered within 15 minutes
                time_diff = (current_trade.entry_date - prev_trade.exit_date).total_seconds() / 60
                
                if time_diff < 15 and current_trade.sentiment == Sentiment.REVENGE:
                    revenge_trades.append(current_trade)
                    current_trade.is_revenge = True
        
        return revenge_trades
    
    def _detect_overtrading(self, trades: List[Trade], threshold: int = 10) -> List[Dict[str, Any]]:
        """Detect days with excessive trading."""
        daily_trades = defaultdict(list)
        
        for trade in trades:
            date_key = trade.entry_date.date()
            daily_trades[date_key].append(trade)
        
        overtraded_days = []
        for date, day_trades in daily_trades.items():
            if len(day_trades) >= threshold:
                total_pnl = sum(t.net_pnl for t in day_trades if t.net_pnl)
                overtraded_days.append({
                    'date': date.isoformat(),
                    'trade_count': len(day_trades),
                    'total_pnl': round(total_pnl, 2)
                })
                
                # Mark trades as overtraded
                for trade in day_trades:
                    trade.is_overtraded = True
        
        return overtraded_days
    
    def _analyze_sentiment_performance(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze performance by sentiment."""
        sentiment_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0.0})
        
        for trade in trades:
            if trade.sentiment:
                sentiment = trade.sentiment.value
                stats = sentiment_stats[sentiment]
                
                if trade.net_pnl > 0:
                    stats['wins'] += 1
                else:
                    stats['losses'] += 1
                stats['total_pnl'] += trade.net_pnl
        
        results = {}
        for sentiment, stats in sentiment_stats.items():
            total = stats['wins'] + stats['losses']
            win_rate = (stats['wins'] / total * 100) if total > 0 else 0
            
            results[sentiment] = {
                'win_rate': round(win_rate, 2),
                'total_pnl': round(stats['total_pnl'], 2)
            }
        
        return results
    
    def _detect_streaks(self, trades: List[Trade]) -> Dict[str, Any]:
        """Detect winning and losing streaks."""
        current_streak = 0
        current_type = None
        max_win_streak = 0
        max_loss_streak = 0
        
        for trade in trades:
            is_win = trade.net_pnl > 0
            
            if current_type is None:
                current_type = 'win' if is_win else 'loss'
                current_streak = 1
            elif (current_type == 'win' and is_win) or (current_type == 'loss' and not is_win):
                current_streak += 1
            else:
                # Streak broken
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
        
        return {
            'max_winning_streak': max_win_streak,
            'max_losing_streak': max_loss_streak
        }
    
    def get_best_performing_strategies(
        self,
        user_id: str,
        top_n: int = 5,
        min_trades: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Identify best performing trading strategies.
        
        Args:
            user_id: User identifier
            top_n: Number of top strategies to return
            min_trades: Minimum trades required
            
        Returns:
            List of best performing strategies
        """
        # Combine setup type, market condition, and time of day
        setup_analysis = self.analyze_setup_performance(user_id, min_trades=min_trades)
        time_analysis = self.analyze_time_of_day_patterns(user_id)
        market_analysis = self.analyze_market_conditions(user_id)
        
        strategies = []
        
        # Add top setups
        for setup, stats in list(setup_analysis.get('setup_performance', {}).items())[:top_n]:
            strategies.append({
                'strategy': f"{setup} Setup",
                'win_rate': stats['win_rate'],
                'total_pnl': stats['total_pnl'],
                'total_trades': stats['total_trades'],
                'profit_factor': stats['profit_factor']
            })
        
        return sorted(strategies, key=lambda x: x['total_pnl'], reverse=True)[:top_n]
