"""Analyzer for identifying smart money flow patterns."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import uuid

from ..models import (
    OptionsTrade, FlowPattern, PatternType, SmartMoneySignal, OrderType
)


class FlowAnalyzer:
    """Analyzes options flow to identify smart money patterns."""
    
    def __init__(
        self,
        analysis_window_minutes: int = 15,
        min_pattern_premium: Decimal = Decimal('100000'),
    ):
        """
        Initialize flow analyzer.
        
        Args:
            analysis_window_minutes: Time window for pattern analysis
            min_pattern_premium: Minimum premium to consider pattern
        """
        self.analysis_window = timedelta(minutes=analysis_window_minutes)
        self.min_pattern_premium = min_pattern_premium
        
        # Store recent trades for analysis
        self._trade_history: List[OptionsTrade] = []
        
        # Pattern cache
        self._detected_patterns: List[FlowPattern] = []
        
    def analyze_trade(self, trade: OptionsTrade) -> List[FlowPattern]:
        """
        Analyze incoming trade for flow patterns.
        
        Args:
            trade: New options trade
            
        Returns:
            List of detected patterns
        """
        # Add to history
        self._trade_history.append(trade)
        self._clean_history(trade.timestamp)
        
        detected_patterns = []
        
        # Check for various patterns
        if pattern := self._detect_aggressive_buying(trade):
            detected_patterns.append(pattern)
        
        if pattern := self._detect_spread_pattern(trade):
            detected_patterns.append(pattern)
        
        if pattern := self._detect_unusual_volume(trade):
            detected_patterns.append(pattern)
        
        if pattern := self._detect_institutional_flow(trade):
            detected_patterns.append(pattern)
        
        # Store detected patterns
        self._detected_patterns.extend(detected_patterns)
        
        return detected_patterns
    
    def _clean_history(self, current_time: datetime) -> None:
        """Remove trades outside analysis window."""
        cutoff = current_time - self.analysis_window
        self._trade_history = [
            t for t in self._trade_history
            if t.timestamp >= cutoff
        ]
    
    def _detect_aggressive_buying(
        self,
        trade: OptionsTrade,
    ) -> Optional[FlowPattern]:
        """
        Detect aggressive call or put buying.
        
        Characteristics:
        - Rapid sequence of aggressive buys
        - Above ask execution
        - Increasing size
        """
        if not trade.is_aggressive:
            return None
        
        # Find related aggressive trades
        related_trades = [
            t for t in self._trade_history
            if (
                t.underlying_symbol == trade.underlying_symbol and
                t.order_type == trade.order_type and
                t.is_aggressive and
                (trade.timestamp - t.timestamp).total_seconds() <= 300  # 5 min
            )
        ]
        
        if len(related_trades) < 3:
            return None
        
        # Calculate metrics
        total_premium = sum(t.notional_value for t in related_trades)
        
        if total_premium < self.min_pattern_premium:
            return None
        
        # Determine pattern type and signal
        if trade.order_type == OrderType.CALL:
            pattern_type = PatternType.AGGRESSIVE_CALL_BUYING
            signal = SmartMoneySignal.BULLISH
        else:
            pattern_type = PatternType.AGGRESSIVE_PUT_BUYING
            signal = SmartMoneySignal.BEARISH
        
        # Calculate confidence
        confidence = self._calculate_aggressive_buying_confidence(related_trades)
        
        return FlowPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_type=pattern_type,
            symbol=trade.symbol,
            underlying_symbol=trade.underlying_symbol,
            detected_at=trade.timestamp,
            total_premium=total_premium,
            total_contracts=sum(t.size for t in related_trades),
            trade_count=len(related_trades),
            signal=signal,
            confidence_score=confidence,
            trade_ids=[t.trade_id for t in related_trades],
            call_premium=total_premium if trade.order_type == OrderType.CALL else Decimal('0'),
            put_premium=total_premium if trade.order_type == OrderType.PUT else Decimal('0'),
            description=f"Aggressive {trade.order_type.value} buying detected",
            metadata={
                'all_above_ask': all(t.above_ask for t in related_trades),
                'avg_premium': float(total_premium / len(related_trades)),
            }
        )
    
    def _detect_spread_pattern(
        self,
        trade: OptionsTrade,
    ) -> Optional[FlowPattern]:
        """
        Detect spread patterns (vertical, calendar, diagonal).
        
        Looks for simultaneous long/short positions at different strikes or dates.
        """
        # Find trades with same underlying in time window
        related_trades = [
            t for t in self._trade_history
            if (
                t.underlying_symbol == trade.underlying_symbol and
                t.order_type == trade.order_type and
                abs((trade.timestamp - t.timestamp).total_seconds()) <= 10
            )
        ]
        
        if len(related_trades) < 2:
            return None
        
        # Check for different strikes (vertical spread)
        strikes = {t.strike for t in related_trades}
        if len(strikes) >= 2:
            pattern_type = PatternType.SPREAD_PATTERN
            
            total_premium = sum(t.notional_value for t in related_trades)
            
            # Determine signal from net premium
            net_debit = sum(
                t.notional_value if t.is_opening else -t.notional_value
                for t in related_trades
            )
            
            if net_debit > 0:
                signal = (SmartMoneySignal.BULLISH if trade.order_type == OrderType.CALL
                         else SmartMoneySignal.BEARISH)
            else:
                signal = SmartMoneySignal.NEUTRAL
            
            return FlowPattern(
                pattern_id=str(uuid.uuid4()),
                pattern_type=pattern_type,
                symbol=trade.symbol,
                underlying_symbol=trade.underlying_symbol,
                detected_at=trade.timestamp,
                total_premium=abs(net_debit),
                total_contracts=sum(t.size for t in related_trades),
                trade_count=len(related_trades),
                signal=signal,
                confidence_score=0.7,
                trade_ids=[t.trade_id for t in related_trades],
                description=f"{trade.order_type.value.capitalize()} spread pattern detected",
                metadata={
                    'strikes': [str(s) for s in sorted(strikes)],
                    'spread_type': 'vertical',
                    'net_debit': str(net_debit),
                }
            )
        
        return None
    
    def _detect_unusual_volume(
        self,
        trade: OptionsTrade,
    ) -> Optional[FlowPattern]:
        """
        Detect unusual volume spikes.
        
        Compare recent volume to historical average.
        """
        # Get recent volume for this contract
        recent_volume = sum(
            t.size for t in self._trade_history
            if (
                t.symbol == trade.symbol and
                t.underlying_symbol == trade.underlying_symbol and
                t.strike == trade.strike and
                t.expiration == trade.expiration
            )
        )
        
        # Check against open interest if available
        if trade.open_interest and trade.open_interest > 0:
            volume_oi_ratio = Decimal(recent_volume) / Decimal(trade.open_interest)
            
            # Unusual if volume > 50% of open interest
            if volume_oi_ratio > Decimal('0.5'):
                total_premium = sum(
                    t.notional_value for t in self._trade_history
                    if t.symbol == trade.symbol
                )
                
                # Determine signal from call/put ratio
                call_premium = sum(
                    t.notional_value for t in self._trade_history
                    if t.symbol == trade.symbol and t.order_type == OrderType.CALL
                )
                put_premium = total_premium - call_premium
                
                if call_premium > put_premium * Decimal('1.5'):
                    signal = SmartMoneySignal.BULLISH
                elif put_premium > call_premium * Decimal('1.5'):
                    signal = SmartMoneySignal.BEARISH
                else:
                    signal = SmartMoneySignal.NEUTRAL
                
                return FlowPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type=PatternType.UNUSUAL_VOLUME,
                    symbol=trade.symbol,
                    underlying_symbol=trade.underlying_symbol,
                    detected_at=trade.timestamp,
                    total_premium=total_premium,
                    total_contracts=recent_volume,
                    trade_count=len([t for t in self._trade_history if t.symbol == trade.symbol]),
                    signal=signal,
                    confidence_score=min(float(volume_oi_ratio), 1.0),
                    call_premium=call_premium,
                    put_premium=put_premium,
                    description=f"Unusual volume detected: {recent_volume} contracts",
                    metadata={
                        'volume_oi_ratio': str(volume_oi_ratio),
                        'open_interest': trade.open_interest,
                    }
                )
        
        return None
    
    def _detect_institutional_flow(
        self,
        trade: OptionsTrade,
    ) -> Optional[FlowPattern]:
        """
        Detect institutional flow patterns.
        
        Characteristics:
        - Large notional value
        - Multiple large trades
        - Strategic timing
        """
        if trade.notional_value < Decimal('500000'):
            return None
        
        # Find other large institutional-size trades
        institutional_trades = [
            t for t in self._trade_history
            if (
                t.underlying_symbol == trade.underlying_symbol and
                t.notional_value >= Decimal('250000')
            )
        ]
        
        if len(institutional_trades) < 2:
            return None
        
        total_premium = sum(t.notional_value for t in institutional_trades)
        
        # Analyze sentiment
        call_premium = sum(
            t.notional_value for t in institutional_trades
            if t.order_type == OrderType.CALL
        )
        put_premium = total_premium - call_premium
        
        if call_premium > put_premium * Decimal('2'):
            signal = SmartMoneySignal.STRONG_BULLISH
        elif call_premium > put_premium * Decimal('1.2'):
            signal = SmartMoneySignal.BULLISH
        elif put_premium > call_premium * Decimal('2'):
            signal = SmartMoneySignal.STRONG_BEARISH
        elif put_premium > call_premium * Decimal('1.2'):
            signal = SmartMoneySignal.BEARISH
        else:
            signal = SmartMoneySignal.NEUTRAL
        
        return FlowPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_type=PatternType.INSTITUTIONAL_FLOW,
            symbol=trade.symbol,
            underlying_symbol=trade.underlying_symbol,
            detected_at=trade.timestamp,
            total_premium=total_premium,
            total_contracts=sum(t.size for t in institutional_trades),
            trade_count=len(institutional_trades),
            signal=signal,
            confidence_score=0.85,
            trade_ids=[t.trade_id for t in institutional_trades],
            call_premium=call_premium,
            put_premium=put_premium,
            description=f"Institutional flow detected: ${float(total_premium):,.0f}",
            estimated_impact="high",
            metadata={
                'avg_trade_size': sum(t.size for t in institutional_trades) / len(institutional_trades),
                'largest_trade': str(max(t.notional_value for t in institutional_trades)),
            }
        )
    
    def _calculate_aggressive_buying_confidence(
        self,
        trades: List[OptionsTrade],
    ) -> float:
        """Calculate confidence score for aggressive buying pattern."""
        score = 0.5  # Base score
        
        # More trades = higher confidence
        if len(trades) >= 5:
            score += 0.2
        
        # All above ask = higher confidence
        if all(t.above_ask for t in trades):
            score += 0.2
        
        # Large total premium
        total_premium = sum(t.notional_value for t in trades)
        if total_premium > Decimal('1000000'):
            score += 0.1
        
        return min(score, 1.0)
    
    def get_flow_summary(
        self,
        symbol: str,
        lookback_minutes: Optional[int] = None,
    ) -> Dict:
        """
        Get flow summary for a symbol.
        
        Args:
            symbol: Underlying symbol
            lookback_minutes: Lookback period (None = use analysis window)
            
        Returns:
            Dictionary with flow summary statistics
        """
        if lookback_minutes:
            cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        else:
            cutoff = datetime.now() - self.analysis_window
        
        relevant_trades = [
            t for t in self._trade_history
            if t.underlying_symbol == symbol and t.timestamp >= cutoff
        ]
        
        if not relevant_trades:
            return {
                'symbol': symbol,
                'trade_count': 0,
                'total_premium': '0',
                'call_premium': '0',
                'put_premium': '0',
            }
        
        call_trades = [t for t in relevant_trades if t.order_type == OrderType.CALL]
        put_trades = [t for t in relevant_trades if t.order_type == OrderType.PUT]
        
        call_premium = sum(t.notional_value for t in call_trades)
        put_premium = sum(t.notional_value for t in put_trades)
        
        return {
            'symbol': symbol,
            'trade_count': len(relevant_trades),
            'total_premium': str(call_premium + put_premium),
            'call_premium': str(call_premium),
            'put_premium': str(put_premium),
            'call_put_ratio': str(call_premium / put_premium) if put_premium > 0 else 'inf',
            'avg_trade_size': sum(t.size for t in relevant_trades) / len(relevant_trades),
            'largest_trade': str(max(t.notional_value for t in relevant_trades)),
        }
