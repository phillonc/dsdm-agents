"""
Personalization Service - Learns user patterns and provides customized recommendations
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import numpy as np
import pandas as pd
from collections import defaultdict, Counter

from ..models.user_models import (
    UserProfile, TradingStyle, RiskTolerance, StrategyPreference,
    TradingPattern, PersonalizedInsight, InsightType, InsightPriority,
    UserStatistics
)
from ..models.pattern_models import ChartPattern
from ..models.analysis_models import PredictionSignal


class PersonalizationService:
    """
    Service for learning user trading patterns and providing
    personalized insights and recommendations
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_sample_size = self.config.get('min_sample_size', 10)
        
    async def learn_trading_patterns(
        self,
        user_id: str,
        trade_history: pd.DataFrame,
        user_profile: UserProfile
    ) -> List[TradingPattern]:
        """
        Learn trading patterns from user's historical trades
        
        Args:
            user_id: User identifier
            trade_history: DataFrame with user's trade history
            user_profile: User's profile
            
        Returns:
            List of identified trading patterns
        """
        patterns = []
        
        if len(trade_history) < self.min_sample_size:
            return patterns
        
        # Analyze entry patterns
        entry_patterns = await self._analyze_entry_patterns(user_id, trade_history)
        patterns.extend(entry_patterns)
        
        # Analyze exit patterns
        exit_patterns = await self._analyze_exit_patterns(user_id, trade_history)
        patterns.extend(exit_patterns)
        
        # Analyze time-of-day patterns
        time_patterns = await self._analyze_time_patterns(user_id, trade_history)
        patterns.extend(time_patterns)
        
        # Analyze position sizing patterns
        sizing_patterns = await self._analyze_sizing_patterns(user_id, trade_history)
        patterns.extend(sizing_patterns)
        
        # Analyze strategy preference patterns
        strategy_patterns = await self._analyze_strategy_patterns(
            user_id, trade_history, user_profile
        )
        patterns.extend(strategy_patterns)
        
        return patterns
    
    async def generate_personalized_insights(
        self,
        user_id: str,
        user_profile: UserProfile,
        trading_patterns: List[TradingPattern],
        current_signals: List[PredictionSignal],
        detected_patterns: List[ChartPattern],
        user_statistics: Optional[UserStatistics] = None
    ) -> List[PersonalizedInsight]:
        """
        Generate personalized insights for user
        
        Args:
            user_id: User identifier
            user_profile: User's profile
            trading_patterns: Learned trading patterns
            current_signals: Current market signals
            detected_patterns: Detected chart patterns
            user_statistics: User's trading statistics
            
        Returns:
            List of personalized insights
        """
        insights = []
        
        # Generate opportunity insights
        opportunity_insights = await self._generate_opportunity_insights(
            user_id, user_profile, current_signals, detected_patterns
        )
        insights.extend(opportunity_insights)
        
        # Generate warning insights
        warning_insights = await self._generate_warning_insights(
            user_id, user_profile, trading_patterns, user_statistics
        )
        insights.extend(warning_insights)
        
        # Generate performance insights
        if user_statistics:
            performance_insights = await self._generate_performance_insights(
                user_id, user_statistics, trading_patterns
            )
            insights.extend(performance_insights)
        
        # Generate educational insights
        educational_insights = await self._generate_educational_insights(
            user_id, user_profile, trading_patterns
        )
        insights.extend(educational_insights)
        
        # Sort by relevance and priority
        insights = sorted(
            insights,
            key=lambda x: (x.priority.value, -x.relevance_score),
            reverse=True
        )
        
        return insights
    
    async def calculate_relevance_score(
        self,
        user_profile: UserProfile,
        signal: PredictionSignal,
        pattern: Optional[ChartPattern] = None
    ) -> float:
        """
        Calculate how relevant a signal/pattern is to the user
        
        Args:
            user_profile: User's profile
            signal: Trading signal
            pattern: Optional chart pattern
            
        Returns:
            Relevance score between 0 and 1
        """
        relevance_factors = []
        
        # Symbol preference
        if signal.symbol in user_profile.preferred_symbols:
            relevance_factors.append(1.0)
        else:
            relevance_factors.append(0.5)
        
        # Time horizon alignment
        time_horizon_match = self._match_time_horizon(
            signal.time_horizon,
            user_profile.trading_style
        )
        relevance_factors.append(time_horizon_match)
        
        # Risk tolerance alignment
        risk_match = self._match_risk_tolerance(
            signal.signal_strength.value,
            user_profile.risk_tolerance
        )
        relevance_factors.append(risk_match)
        
        # Strategy alignment
        if pattern:
            strategy_match = self._match_strategy(
                pattern.pattern_type.value,
                user_profile.preferred_strategies
            )
            relevance_factors.append(strategy_match)
        
        # Calculate weighted average
        relevance_score = np.mean(relevance_factors)
        
        return relevance_score
    
    async def update_user_profile(
        self,
        user_id: str,
        user_profile: UserProfile,
        recent_trades: pd.DataFrame,
        trading_patterns: List[TradingPattern]
    ) -> UserProfile:
        """
        Update user profile based on recent activity
        
        Args:
            user_id: User identifier
            user_profile: Current user profile
            recent_trades: Recent trade data
            trading_patterns: Learned patterns
            
        Returns:
            Updated user profile
        """
        updated_profile = user_profile.copy()
        updated_profile.updated_at = datetime.utcnow()
        
        # Update preferred symbols based on frequency
        if len(recent_trades) > 0:
            symbol_counts = recent_trades['symbol'].value_counts()
            top_symbols = symbol_counts.head(10).index.tolist()
            updated_profile.preferred_symbols = top_symbols
        
        # Update preferred strategies based on success rate
        if trading_patterns:
            successful_strategies = [
                p.pattern_type for p in trading_patterns
                if p.success_rate > 0.6
            ]
            if successful_strategies:
                strategy_counter = Counter(successful_strategies)
                # Convert to StrategyPreference enum if possible
                updated_profile.preferred_strategies = [
                    self._map_to_strategy_preference(s)
                    for s, _ in strategy_counter.most_common(5)
                ]
        
        # Update risk tolerance based on typical position sizes
        if len(recent_trades) > 0:
            avg_position_size = recent_trades['position_size'].mean()
            if 'account_size' in recent_trades.columns:
                account_size = recent_trades['account_size'].iloc[-1]
                position_size_ratio = avg_position_size / account_size
                
                if position_size_ratio > 0.15:
                    updated_profile.risk_tolerance = RiskTolerance.AGGRESSIVE
                elif position_size_ratio > 0.10:
                    updated_profile.risk_tolerance = RiskTolerance.MODERATE
                else:
                    updated_profile.risk_tolerance = RiskTolerance.CONSERVATIVE
        
        return updated_profile
    
    # Private helper methods
    
    async def _analyze_entry_patterns(
        self,
        user_id: str,
        trade_history: pd.DataFrame
    ) -> List[TradingPattern]:
        """Analyze user's entry patterns"""
        patterns = []
        
        # Group trades by entry conditions
        entry_conditions = defaultdict(list)
        
        for _, trade in trade_history.iterrows():
            conditions = trade.get('entry_conditions', [])
            if isinstance(conditions, list):
                for condition in conditions:
                    entry_conditions[condition].append(trade)
        
        # Analyze each entry condition
        for condition, trades in entry_conditions.items():
            if len(trades) >= self.min_sample_size:
                trades_df = pd.DataFrame(trades)
                
                # Calculate success rate
                winning_trades = len(trades_df[trades_df['profit'] > 0])
                success_rate = winning_trades / len(trades_df)
                
                # Calculate average return
                avg_return = trades_df['profit'].mean()
                
                # Calculate holding period
                if 'entry_time' in trades_df.columns and 'exit_time' in trades_df.columns:
                    holding_periods = (
                        pd.to_datetime(trades_df['exit_time']) -
                        pd.to_datetime(trades_df['entry_time'])
                    ).dt.total_seconds() / 3600
                    avg_holding_period = holding_periods.mean()
                else:
                    avg_holding_period = 24.0
                
                pattern = TradingPattern(
                    pattern_id=f"tp_{uuid.uuid4().hex[:8]}",
                    user_id=user_id,
                    pattern_type=f"entry_{condition}",
                    frequency=len(trades),
                    success_rate=success_rate,
                    average_return=avg_return,
                    average_holding_period=avg_holding_period,
                    common_entry_conditions=[condition],
                    confidence=min(0.95, len(trades) / 50),
                    sample_size=len(trades),
                    associated_symbols=trades_df['symbol'].value_counts().head(5).index.tolist()
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _analyze_exit_patterns(
        self,
        user_id: str,
        trade_history: pd.DataFrame
    ) -> List[TradingPattern]:
        """Analyze user's exit patterns"""
        patterns = []
        
        # Analyze exit timing
        if 'exit_reason' in trade_history.columns:
            exit_reasons = trade_history['exit_reason'].value_counts()
            
            for reason, count in exit_reasons.items():
                if count >= self.min_sample_size:
                    reason_trades = trade_history[trade_history['exit_reason'] == reason]
                    
                    winning_trades = len(reason_trades[reason_trades['profit'] > 0])
                    success_rate = winning_trades / len(reason_trades)
                    
                    pattern = TradingPattern(
                        pattern_id=f"tp_{uuid.uuid4().hex[:8]}",
                        user_id=user_id,
                        pattern_type=f"exit_{reason}",
                        frequency=count,
                        success_rate=success_rate,
                        average_return=reason_trades['profit'].mean(),
                        average_holding_period=0.0,
                        common_exit_conditions=[reason],
                        confidence=min(0.95, count / 50),
                        sample_size=count
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def _analyze_time_patterns(
        self,
        user_id: str,
        trade_history: pd.DataFrame
    ) -> List[TradingPattern]:
        """Analyze time-of-day patterns"""
        patterns = []
        
        if 'entry_time' not in trade_history.columns:
            return patterns
        
        # Extract hour of day
        trade_history['hour'] = pd.to_datetime(
            trade_history['entry_time']
        ).dt.hour
        
        # Group by hour
        hourly_performance = trade_history.groupby('hour').agg({
            'profit': ['mean', 'count']
        })
        
        # Find best performing hours
        best_hours = hourly_performance[
            (hourly_performance[('profit', 'count')] >= self.min_sample_size) &
            (hourly_performance[('profit', 'mean')] > 0)
        ]
        
        if len(best_hours) > 0:
            best_hour = best_hours[('profit', 'mean')].idxmax()
            hour_trades = trade_history[trade_history['hour'] == best_hour]
            
            pattern = TradingPattern(
                pattern_id=f"tp_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                pattern_type="time_of_day",
                frequency=len(hour_trades),
                success_rate=len(hour_trades[hour_trades['profit'] > 0]) / len(hour_trades),
                average_return=hour_trades['profit'].mean(),
                average_holding_period=0.0,
                preferred_time_of_day=f"{best_hour}:00",
                confidence=min(0.9, len(hour_trades) / 30),
                sample_size=len(hour_trades)
            )
            patterns.append(pattern)
        
        return patterns
    
    async def _analyze_sizing_patterns(
        self,
        user_id: str,
        trade_history: pd.DataFrame
    ) -> List[TradingPattern]:
        """Analyze position sizing patterns"""
        patterns = []
        
        if 'position_size' not in trade_history.columns:
            return patterns
        
        # Categorize position sizes
        position_sizes = trade_history['position_size']
        percentiles = position_sizes.quantile([0.33, 0.67])
        
        def categorize_size(size):
            if size <= percentiles[0.33]:
                return 'small'
            elif size <= percentiles[0.67]:
                return 'medium'
            else:
                return 'large'
        
        trade_history['size_category'] = position_sizes.apply(categorize_size)
        
        # Analyze performance by size category
        for category in ['small', 'medium', 'large']:
            category_trades = trade_history[
                trade_history['size_category'] == category
            ]
            
            if len(category_trades) >= self.min_sample_size:
                winning_trades = len(category_trades[category_trades['profit'] > 0])
                success_rate = winning_trades / len(category_trades)
                
                pattern = TradingPattern(
                    pattern_id=f"tp_{uuid.uuid4().hex[:8]}",
                    user_id=user_id,
                    pattern_type=f"position_size_{category}",
                    frequency=len(category_trades),
                    success_rate=success_rate,
                    average_return=category_trades['profit'].mean(),
                    average_holding_period=0.0,
                    typical_position_size=category_trades['position_size'].mean(),
                    confidence=min(0.9, len(category_trades) / 50),
                    sample_size=len(category_trades)
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _analyze_strategy_patterns(
        self,
        user_id: str,
        trade_history: pd.DataFrame,
        user_profile: UserProfile
    ) -> List[TradingPattern]:
        """Analyze strategy preference patterns"""
        patterns = []
        
        if 'strategy' not in trade_history.columns:
            return patterns
        
        strategy_performance = trade_history.groupby('strategy').agg({
            'profit': ['mean', 'count', lambda x: (x > 0).sum()]
        })
        
        for strategy in strategy_performance.index:
            count = strategy_performance.loc[strategy, ('profit', 'count')]
            
            if count >= self.min_sample_size:
                avg_return = strategy_performance.loc[strategy, ('profit', 'mean')]
                wins = strategy_performance.loc[strategy, ('profit', '<lambda>')]
                success_rate = wins / count
                
                pattern = TradingPattern(
                    pattern_id=f"tp_{uuid.uuid4().hex[:8]}",
                    user_id=user_id,
                    pattern_type=f"strategy_{strategy}",
                    frequency=count,
                    success_rate=success_rate,
                    average_return=avg_return,
                    average_holding_period=0.0,
                    confidence=min(0.95, count / 50),
                    sample_size=count
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _generate_opportunity_insights(
        self,
        user_id: str,
        user_profile: UserProfile,
        current_signals: List[PredictionSignal],
        detected_patterns: List[ChartPattern]
    ) -> List[PersonalizedInsight]:
        """Generate opportunity insights"""
        insights = []
        
        for signal in current_signals:
            # Calculate relevance
            relevance_score = await self.calculate_relevance_score(
                user_profile, signal
            )
            
            if relevance_score < 0.5:
                continue
            
            # Find related patterns
            related_patterns = [
                p.pattern_id for p in detected_patterns
                if p.symbol == signal.symbol
            ]
            
            # Determine priority
            if signal.confidence > 0.8 and relevance_score > 0.8:
                priority = InsightPriority.HIGH
            elif signal.confidence > 0.7:
                priority = InsightPriority.MEDIUM
            else:
                priority = InsightPriority.LOW
            
            # Generate action items
            action_items = self._generate_action_items(signal, user_profile)
            
            # Create insight
            insight = PersonalizedInsight(
                insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                insight_type=InsightType.OPPORTUNITY,
                priority=priority,
                title=f"{signal.signal_type.value.title()} Signal on {signal.symbol}",
                description=self._generate_opportunity_description(
                    signal, user_profile, relevance_score
                ),
                symbol=signal.symbol,
                actionable=True,
                action_items=action_items,
                relevance_score=relevance_score,
                confidence=signal.confidence,
                expiry=datetime.utcnow() + timedelta(hours=24),
                related_patterns=related_patterns,
                related_signals=[signal.signal_id]
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_warning_insights(
        self,
        user_id: str,
        user_profile: UserProfile,
        trading_patterns: List[TradingPattern],
        user_statistics: Optional[UserStatistics]
    ) -> List[PersonalizedInsight]:
        """Generate warning insights"""
        insights = []
        
        # Check for negative patterns
        negative_patterns = [
            p for p in trading_patterns
            if p.success_rate < 0.4 and p.frequency > self.min_sample_size
        ]
        
        for pattern in negative_patterns:
            insight = PersonalizedInsight(
                insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                insight_type=InsightType.WARNING,
                priority=InsightPriority.HIGH,
                title=f"Low Success Rate in {pattern.pattern_type}",
                description=f"Your {pattern.pattern_type} strategy has a success rate of only {pattern.success_rate:.1%} over {pattern.frequency} trades. Consider reviewing or avoiding this approach.",
                actionable=True,
                action_items=[
                    "Review past trades with this pattern",
                    "Consider adjusting entry/exit criteria",
                    "Reduce position size for this strategy"
                ],
                relevance_score=0.9,
                confidence=pattern.confidence,
                related_patterns=[pattern.pattern_id]
            )
            insights.append(insight)
        
        # Check for drawdown warnings
        if user_statistics and user_statistics.max_drawdown < -0.15:
            insight = PersonalizedInsight(
                insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                insight_type=InsightType.WARNING,
                priority=InsightPriority.URGENT,
                title="Significant Drawdown Detected",
                description=f"Your account has experienced a {user_statistics.max_drawdown:.1%} drawdown. Consider reducing position sizes and reviewing your risk management.",
                actionable=True,
                action_items=[
                    "Review and tighten stop losses",
                    "Reduce position sizes by 50%",
                    "Take a break and reassess strategy"
                ],
                relevance_score=1.0,
                confidence=1.0
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_performance_insights(
        self,
        user_id: str,
        user_statistics: UserStatistics,
        trading_patterns: List[TradingPattern]
    ) -> List[PersonalizedInsight]:
        """Generate performance insights"""
        insights = []
        
        # Best performing strategy
        if trading_patterns:
            best_pattern = max(trading_patterns, key=lambda p: p.success_rate)
            
            insight = PersonalizedInsight(
                insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                insight_type=InsightType.PERFORMANCE,
                priority=InsightPriority.MEDIUM,
                title=f"Your Best Strategy: {best_pattern.pattern_type}",
                description=f"Your {best_pattern.pattern_type} strategy has achieved a {best_pattern.success_rate:.1%} success rate with an average return of {best_pattern.average_return:.2%}. Consider focusing more on this approach.",
                actionable=True,
                action_items=[
                    f"Increase allocation to {best_pattern.pattern_type} trades",
                    "Document what makes this strategy successful",
                    "Look for similar setups more frequently"
                ],
                relevance_score=0.95,
                confidence=best_pattern.confidence,
                related_patterns=[best_pattern.pattern_id]
            )
            insights.append(insight)
        
        # Win rate insight
        if user_statistics.win_rate > 0.6:
            insight = PersonalizedInsight(
                insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                insight_type=InsightType.PERFORMANCE,
                priority=InsightPriority.LOW,
                title=f"Strong Win Rate: {user_statistics.win_rate:.1%}",
                description=f"You're maintaining a strong win rate of {user_statistics.win_rate:.1%}. Keep up the consistent execution!",
                actionable=False,
                relevance_score=0.8,
                confidence=1.0
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_educational_insights(
        self,
        user_id: str,
        user_profile: UserProfile,
        trading_patterns: List[TradingPattern]
    ) -> List[PersonalizedInsight]:
        """Generate educational insights"""
        insights = []
        
        # Suggest learning based on experience level
        if user_profile.experience_level == "beginner":
            insight = PersonalizedInsight(
                insight_id=f"ins_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                insight_type=InsightType.EDUCATION,
                priority=InsightPriority.LOW,
                title="Risk Management Fundamentals",
                description="As a newer trader, mastering risk management is crucial. Learn about position sizing, stop losses, and risk-reward ratios.",
                actionable=True,
                action_items=[
                    "Review risk management best practices",
                    "Calculate risk per trade (recommend 1-2% max)",
                    "Always use stop losses"
                ],
                relevance_score=0.85,
                confidence=1.0,
                learning_content={
                    "topics": ["risk_management", "position_sizing", "stop_losses"],
                    "resources": ["risk_management_guide", "position_sizing_calculator"]
                }
            )
            insights.append(insight)
        
        return insights
    
    def _match_time_horizon(
        self,
        signal_horizon: str,
        trading_style: TradingStyle
    ) -> float:
        """Match signal time horizon with trading style"""
        horizon_map = {
            TradingStyle.SCALPER: {'1m': 1.0, '5m': 0.8, '15m': 0.5},
            TradingStyle.DAY_TRADER: {'5m': 0.7, '15m': 1.0, '1H': 0.9, '4H': 0.5},
            TradingStyle.SWING_TRADER: {'1H': 0.6, '4H': 0.9, '1D': 1.0, '1W': 0.8},
            TradingStyle.POSITION_TRADER: {'1D': 0.8, '1W': 1.0, '1M': 1.0},
            TradingStyle.INVESTOR: {'1W': 0.7, '1M': 1.0, '3M': 1.0}
        }
        
        style_horizons = horizon_map.get(trading_style, {})
        return style_horizons.get(signal_horizon, 0.5)
    
    def _match_risk_tolerance(
        self,
        signal_strength: str,
        risk_tolerance: RiskTolerance
    ) -> float:
        """Match signal strength with risk tolerance"""
        # Higher risk tolerance = comfortable with stronger signals
        if risk_tolerance == RiskTolerance.AGGRESSIVE:
            return 1.0 if 'strong' in signal_strength else 0.7
        elif risk_tolerance == RiskTolerance.MODERATE:
            return 0.9 if 'moderate' in signal_strength else 0.8
        else:  # Conservative
            return 0.9 if signal_strength == 'moderate' else 0.6
    
    def _match_strategy(
        self,
        pattern_type: str,
        preferred_strategies: List[StrategyPreference]
    ) -> float:
        """Match pattern with preferred strategies"""
        # Map pattern types to strategies
        strategy_patterns = {
            StrategyPreference.MOMENTUM: ['breakout', 'bull_flag', 'bear_flag'],
            StrategyPreference.MEAN_REVERSION: ['double_top', 'double_bottom'],
            StrategyPreference.BREAKOUT: ['ascending_triangle', 'breakout'],
            StrategyPreference.TREND_FOLLOWING: ['head_shoulders', 'wedge']
        }
        
        for strategy in preferred_strategies:
            if strategy in strategy_patterns:
                if any(p in pattern_type for p in strategy_patterns[strategy]):
                    return 1.0
        
        return 0.5
    
    def _generate_action_items(
        self,
        signal: PredictionSignal,
        user_profile: UserProfile
    ) -> List[str]:
        """Generate actionable items for signal"""
        actions = []
        
        if signal.signal_type.value in ['buy', 'strong_buy']:
            actions.append(f"Consider entry near ${signal.current_price:.2f}")
            if signal.price_target:
                actions.append(f"Target price: ${signal.price_target:.2f}")
            actions.append("Set appropriate stop loss based on risk tolerance")
        elif signal.signal_type.value in ['sell', 'strong_sell']:
            actions.append(f"Consider exit or short entry near ${signal.current_price:.2f}")
            if signal.price_target:
                actions.append(f"Target price: ${signal.price_target:.2f}")
        
        # Add risk management reminder
        if user_profile.max_risk_per_trade:
            actions.append(
                f"Risk no more than ${user_profile.max_risk_per_trade:.2f} on this trade"
            )
        
        return actions
    
    def _generate_opportunity_description(
        self,
        signal: PredictionSignal,
        user_profile: UserProfile,
        relevance_score: float
    ) -> str:
        """Generate description for opportunity insight"""
        description_parts = []
        
        # Personalized opening
        if relevance_score > 0.8:
            description_parts.append(
                f"Based on your {user_profile.trading_style.value} profile, "
                f"this setup aligns well with your preferences."
            )
        
        # Signal details
        change_pct = (
            (signal.predicted_price - signal.current_price) / signal.current_price * 100
        )
        description_parts.append(
            f"{signal.symbol} shows a {signal.signal_type.value} signal "
            f"with {signal.confidence:.1%} confidence, "
            f"projecting a {abs(change_pct):.1f}% move over {signal.time_horizon}."
        )
        
        # Contributing factors
        if signal.contributing_factors:
            top_factors = signal.contributing_factors[:2]
            description_parts.append(
                f"Key factors: {', '.join(top_factors)}"
            )
        
        return " ".join(description_parts)
    
    def _map_to_strategy_preference(self, strategy_name: str) -> StrategyPreference:
        """Map strategy name to StrategyPreference enum"""
        strategy_map = {
            'momentum': StrategyPreference.MOMENTUM,
            'mean_reversion': StrategyPreference.MEAN_REVERSION,
            'breakout': StrategyPreference.BREAKOUT,
            'trend_following': StrategyPreference.TREND_FOLLOWING,
            'volatility': StrategyPreference.VOLATILITY,
        }
        return strategy_map.get(strategy_name.lower(), StrategyPreference.MOMENTUM)
