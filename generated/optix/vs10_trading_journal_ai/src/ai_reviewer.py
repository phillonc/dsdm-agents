"""
AI Reviewer Module for Trading Journal AI.

This module generates weekly AI review summaries with P&L analysis, win rates,
improvement tips, and personalized insights.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from statistics import mean, median, stdev
from sqlalchemy.orm import Session

from .models import (
    Trade, WeeklyReview, TradeStatus, SetupType, 
    MarketCondition, Sentiment
)
from .pattern_analyzer import PatternAnalyzer

logger = logging.getLogger(__name__)


class AIReviewer:
    """
    AI-powered weekly review generator with insights and recommendations.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the AI reviewer.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.pattern_analyzer = PatternAnalyzer(db_session)
    
    def generate_weekly_review(
        self,
        user_id: str,
        week_start: Optional[datetime] = None
    ) -> WeeklyReview:
        """
        Generate a comprehensive weekly review with AI insights.
        
        Args:
            user_id: User identifier
            week_start: Optional week start date (defaults to last Monday)
            
        Returns:
            WeeklyReview object with complete analysis
        """
        # Calculate week boundaries
        if not week_start:
            today = datetime.utcnow().date()
            week_start = today - timedelta(days=today.weekday())  # Last Monday
            week_start = datetime.combine(week_start, datetime.min.time())
        
        week_end = week_start + timedelta(days=7)
        
        # Get trades for the week
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= week_start,
            Trade.entry_date < week_end,
            Trade.status == TradeStatus.CLOSED
        ).all()
        
        # Calculate basic metrics
        metrics = self._calculate_basic_metrics(trades)
        
        # Analyze patterns
        setup_performance = self._analyze_weekly_setups(trades)
        time_performance = self._analyze_weekly_time_patterns(trades)
        market_performance = self._analyze_weekly_market_conditions(trades)
        
        # Generate AI insights
        insights = self._generate_insights(trades, metrics, setup_performance)
        
        # Generate improvement tips
        tips = self._generate_improvement_tips(trades, metrics, setup_performance)
        
        # Discover patterns
        patterns = self._discover_patterns(trades)
        
        # Behavioral analysis
        behavioral = self._analyze_behavior(trades)
        
        # Generate summary text
        summary = self._generate_summary_text(metrics, insights, tips)
        
        # Create weekly review record
        review = WeeklyReview(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            total_trades=metrics['total_trades'],
            winning_trades=metrics['winning_trades'],
            losing_trades=metrics['losing_trades'],
            win_rate=metrics['win_rate'],
            gross_pnl=metrics['gross_pnl'],
            net_pnl=metrics['net_pnl'],
            average_win=metrics['average_win'],
            average_loss=metrics['average_loss'],
            profit_factor=metrics['profit_factor'],
            largest_win=metrics['largest_win'],
            largest_loss=metrics['largest_loss'],
            top_performing_setups=setup_performance['top'],
            worst_performing_setups=setup_performance['worst'],
            best_trading_hours=time_performance,
            market_condition_performance=market_performance,
            key_insights=insights,
            improvement_tips=tips,
            pattern_discoveries=patterns,
            behavioral_analysis=behavioral,
            summary_text=summary
        )
        
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        
        logger.info(f"Generated weekly review for user {user_id}: {week_start} to {week_end}")
        return review
    
    def _calculate_basic_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        """Calculate basic performance metrics."""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'gross_pnl': 0.0,
                'net_pnl': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'profit_factor': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0
            }
        
        winning_trades = [t for t in trades if t.net_pnl > 0]
        losing_trades = [t for t in trades if t.net_pnl <= 0]
        
        gross_pnl = sum(t.gross_pnl for t in trades if t.gross_pnl)
        net_pnl = sum(t.net_pnl for t in trades if t.net_pnl)
        
        average_win = mean([t.net_pnl for t in winning_trades]) if winning_trades else 0.0
        average_loss = mean([t.net_pnl for t in losing_trades]) if losing_trades else 0.0
        
        total_wins = sum(t.net_pnl for t in winning_trades) if winning_trades else 0.0
        total_losses = abs(sum(t.net_pnl for t in losing_trades)) if losing_trades else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        all_pnls = [t.net_pnl for t in trades if t.net_pnl is not None]
        largest_win = max(all_pnls) if all_pnls else 0.0
        largest_loss = min(all_pnls) if all_pnls else 0.0
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(trades) * 100) if trades else 0.0,
            'gross_pnl': round(gross_pnl, 2),
            'net_pnl': round(net_pnl, 2),
            'average_win': round(average_win, 2),
            'average_loss': round(average_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2)
        }
    
    def _analyze_weekly_setups(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze setup performance for the week."""
        setup_stats = {}
        
        for trade in trades:
            if not trade.setup_type:
                continue
            
            setup = trade.setup_type.value
            if setup not in setup_stats:
                setup_stats[setup] = {
                    'trades': 0,
                    'wins': 0,
                    'total_pnl': 0.0
                }
            
            stats = setup_stats[setup]
            stats['trades'] += 1
            stats['total_pnl'] += trade.net_pnl or 0
            if trade.net_pnl and trade.net_pnl > 0:
                stats['wins'] += 1
        
        # Calculate win rates
        for setup, stats in setup_stats.items():
            stats['win_rate'] = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
        
        # Get top and worst performers
        sorted_setups = sorted(setup_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
        
        top_setups = {}
        worst_setups = {}
        
        if sorted_setups:
            for setup, stats in sorted_setups[:3]:
                top_setups[setup] = {
                    'trades': stats['trades'],
                    'win_rate': round(stats['win_rate'], 2),
                    'total_pnl': round(stats['total_pnl'], 2)
                }
            
            for setup, stats in sorted_setups[-3:]:
                worst_setups[setup] = {
                    'trades': stats['trades'],
                    'win_rate': round(stats['win_rate'], 2),
                    'total_pnl': round(stats['total_pnl'], 2)
                }
        
        return {
            'top': top_setups,
            'worst': worst_setups
        }
    
    def _analyze_weekly_time_patterns(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze time-of-day patterns for the week."""
        hourly_pnl = {}
        
        for trade in trades:
            hour = trade.entry_date.hour
            hour_key = f"{hour:02d}:00"
            
            if hour_key not in hourly_pnl:
                hourly_pnl[hour_key] = []
            
            hourly_pnl[hour_key].append(trade.net_pnl or 0)
        
        # Calculate average P&L per hour
        hourly_avg = {}
        for hour, pnls in hourly_pnl.items():
            hourly_avg[hour] = round(mean(pnls), 2)
        
        # Get best 3 hours
        best_hours = sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'best_hours': [hour for hour, _ in best_hours],
            'hourly_average_pnl': hourly_avg
        }
    
    def _analyze_weekly_market_conditions(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze performance under different market conditions."""
        condition_stats = {}
        
        for trade in trades:
            if not trade.market_condition:
                continue
            
            condition = trade.market_condition.value
            if condition not in condition_stats:
                condition_stats[condition] = {
                    'trades': 0,
                    'wins': 0,
                    'total_pnl': 0.0
                }
            
            stats = condition_stats[condition]
            stats['trades'] += 1
            stats['total_pnl'] += trade.net_pnl or 0
            if trade.net_pnl and trade.net_pnl > 0:
                stats['wins'] += 1
        
        # Calculate win rates
        for condition, stats in condition_stats.items():
            stats['win_rate'] = round((stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0, 2)
            stats['total_pnl'] = round(stats['total_pnl'], 2)
        
        return condition_stats
    
    def _generate_insights(
        self,
        trades: List[Trade],
        metrics: Dict[str, Any],
        setup_performance: Dict[str, Any]
    ) -> List[str]:
        """Generate AI-powered insights."""
        insights = []
        
        # Win rate insight
        win_rate = metrics['win_rate']
        if win_rate >= 60:
            insights.append(f"Excellent win rate of {win_rate:.1f}% - you're maintaining strong consistency.")
        elif win_rate >= 50:
            insights.append(f"Solid win rate of {win_rate:.1f}% - you're on the right track.")
        elif win_rate >= 40:
            insights.append(f"Win rate of {win_rate:.1f}% needs improvement. Focus on trade quality over quantity.")
        else:
            insights.append(f"Win rate of {win_rate:.1f}% is concerning. Review your entry criteria and risk management.")
        
        # P&L insight
        net_pnl = metrics['net_pnl']
        if net_pnl > 0:
            insights.append(f"Profitable week with ${net_pnl:,.2f} net P&L. Keep up the good work!")
        else:
            insights.append(f"Week ended with ${abs(net_pnl):,.2f} loss. Focus on reducing risk and improving setup selection.")
        
        # Profit factor insight
        profit_factor = metrics['profit_factor']
        if profit_factor >= 2.0:
            insights.append(f"Outstanding profit factor of {profit_factor:.2f} - your winners far exceed your losers.")
        elif profit_factor >= 1.5:
            insights.append(f"Good profit factor of {profit_factor:.2f} - maintain your risk/reward discipline.")
        elif profit_factor < 1.0:
            insights.append(f"Profit factor of {profit_factor:.2f} indicates losses exceed wins. Review risk management.")
        
        # Setup insight
        if setup_performance['top']:
            best_setup = list(setup_performance['top'].keys())[0]
            best_stats = setup_performance['top'][best_setup]
            insights.append(f"Your {best_setup} setup performed best with {best_stats['win_rate']:.1f}% win rate and ${best_stats['total_pnl']:,.2f} P&L.")
        
        # Risk/reward insight
        avg_win = metrics['average_win']
        avg_loss = abs(metrics['average_loss'])
        if avg_win > 0 and avg_loss > 0:
            rr_ratio = avg_win / avg_loss
            if rr_ratio >= 2.0:
                insights.append(f"Excellent risk/reward ratio of {rr_ratio:.2f}:1 - you're letting winners run.")
            elif rr_ratio < 1.0:
                insights.append(f"Risk/reward ratio of {rr_ratio:.2f}:1 needs improvement - cut losses quicker and let winners run.")
        
        return insights
    
    def _generate_improvement_tips(
        self,
        trades: List[Trade],
        metrics: Dict[str, Any],
        setup_performance: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized improvement tips."""
        tips = []
        
        # Based on win rate
        if metrics['win_rate'] < 50:
            tips.append("Focus on higher probability setups. Wait for better confirmation signals before entering.")
            tips.append("Review your losing trades to identify common mistakes in entry timing.")
        
        # Based on profit factor
        if metrics['profit_factor'] < 1.5:
            tips.append("Improve your risk/reward by setting wider profit targets and tighter stop losses.")
            tips.append("Consider scaling out of positions to lock in profits while letting runners work.")
        
        # Based on trade volume
        if metrics['total_trades'] > 50:
            tips.append("You may be overtrading. Focus on quality over quantity - wait for A+ setups only.")
        elif metrics['total_trades'] < 5:
            tips.append("Low trade volume. Ensure you're not missing good opportunities due to over-caution.")
        
        # Based on setup performance
        if setup_performance['worst']:
            worst_setup = list(setup_performance['worst'].keys())[0]
            worst_stats = setup_performance['worst'][worst_setup]
            if worst_stats['total_pnl'] < -100:
                tips.append(f"Avoid {worst_setup} setups for now - they're costing you ${abs(worst_stats['total_pnl']):,.2f}.")
        
        # Based on largest loss
        if abs(metrics['largest_loss']) > metrics['average_win'] * 3:
            tips.append("Your largest loss is too big. Always use stop losses and honor them.")
        
        # General tips
        tips.append("Keep detailed notes on each trade to identify what works and what doesn't.")
        tips.append("Review your best trades weekly and work to replicate those conditions.")
        
        return tips[:5]  # Return top 5 tips
    
    def _discover_patterns(self, trades: List[Trade]) -> List[str]:
        """Discover trading patterns in the weekly data."""
        patterns = []
        
        if not trades:
            return patterns
        
        # Day of week pattern
        dow_pnl = {}
        for trade in trades:
            dow = trade.entry_date.strftime('%A')
            if dow not in dow_pnl:
                dow_pnl[dow] = []
            dow_pnl[dow].append(trade.net_pnl or 0)
        
        for day, pnls in dow_pnl.items():
            avg_pnl = mean(pnls)
            if avg_pnl > 100:
                patterns.append(f"{day}s are highly profitable for you (avg ${avg_pnl:.2f})")
            elif avg_pnl < -100:
                patterns.append(f"Consider avoiding trades on {day}s (avg loss ${abs(avg_pnl):.2f})")
        
        # Symbol concentration
        symbol_counts = {}
        for trade in trades:
            symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1
        
        most_traded = max(symbol_counts.items(), key=lambda x: x[1]) if symbol_counts else None
        if most_traded and most_traded[1] > len(trades) * 0.3:
            patterns.append(f"You're heavily concentrated in {most_traded[0]} ({most_traded[1]} trades)")
        
        # Sentiment pattern
        sentiment_trades = [t for t in trades if t.sentiment]
        if sentiment_trades:
            disciplined_trades = [t for t in sentiment_trades if t.sentiment == Sentiment.DISCIPLINED]
            if disciplined_trades:
                disciplined_pnl = mean([t.net_pnl for t in disciplined_trades if t.net_pnl])
                patterns.append(f"Disciplined trades average ${disciplined_pnl:.2f} P&L - stick to your plan!")
        
        return patterns
    
    def _analyze_behavior(self, trades: List[Trade]) -> Dict[str, Any]:
        """Analyze trading behavior patterns."""
        if not trades:
            return {}
        
        behavior = {
            'discipline_score': 0,
            'emotional_trades': 0,
            'disciplined_trades': 0,
            'average_hold_time': 0
        }
        
        # Count emotional vs disciplined trades
        for trade in trades:
            if trade.sentiment in [Sentiment.FOMO, Sentiment.REVENGE, Sentiment.IMPULSIVE, Sentiment.ANXIOUS]:
                behavior['emotional_trades'] += 1
            elif trade.sentiment in [Sentiment.DISCIPLINED, Sentiment.CONFIDENT, Sentiment.CALM]:
                behavior['disciplined_trades'] += 1
        
        # Calculate discipline score
        total_sentiment_trades = behavior['emotional_trades'] + behavior['disciplined_trades']
        if total_sentiment_trades > 0:
            behavior['discipline_score'] = round(
                (behavior['disciplined_trades'] / total_sentiment_trades) * 100,
                2
            )
        
        # Calculate average hold time
        hold_times = []
        for trade in trades:
            if trade.exit_date and trade.entry_date:
                hold_time = (trade.exit_date - trade.entry_date).total_seconds() / 3600  # hours
                hold_times.append(hold_time)
        
        if hold_times:
            behavior['average_hold_time'] = round(mean(hold_times), 2)
        
        return behavior
    
    def _generate_summary_text(
        self,
        metrics: Dict[str, Any],
        insights: List[str],
        tips: List[str]
    ) -> str:
        """Generate human-readable summary text."""
        summary_parts = []
        
        # Opening
        if metrics['net_pnl'] > 0:
            summary_parts.append(f"Great week! You closed {metrics['total_trades']} trades with a net profit of ${metrics['net_pnl']:,.2f}.")
        else:
            summary_parts.append(f"This week you completed {metrics['total_trades']} trades with a net loss of ${abs(metrics['net_pnl']):,.2f}.")
        
        # Performance
        summary_parts.append(f"Your win rate was {metrics['win_rate']:.1f}% ({metrics['winning_trades']} wins, {metrics['losing_trades']} losses).")
        
        # Key metrics
        summary_parts.append(f"Average winner: ${metrics['average_win']:.2f}, Average loser: ${abs(metrics['average_loss']):.2f}, Profit Factor: {metrics['profit_factor']:.2f}.")
        
        # Top insight
        if insights:
            summary_parts.append(f"\n\nKey Insight: {insights[0]}")
        
        # Top tip
        if tips:
            summary_parts.append(f"\n\nTop Recommendation: {tips[0]}")
        
        return " ".join(summary_parts)
    
    def get_weekly_reviews(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[WeeklyReview]:
        """
        Get recent weekly reviews for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of reviews to return
            
        Returns:
            List of weekly reviews
        """
        return self.db.query(WeeklyReview).filter(
            WeeklyReview.user_id == user_id
        ).order_by(WeeklyReview.week_start.desc()).limit(limit).all()
    
    def get_review_by_date(
        self,
        user_id: str,
        date: datetime
    ) -> Optional[WeeklyReview]:
        """
        Get weekly review for a specific date.
        
        Args:
            user_id: User identifier
            date: Date within the week
            
        Returns:
            WeeklyReview if found, None otherwise
        """
        return self.db.query(WeeklyReview).filter(
            WeeklyReview.user_id == user_id,
            WeeklyReview.week_start <= date,
            WeeklyReview.week_end > date
        ).first()
