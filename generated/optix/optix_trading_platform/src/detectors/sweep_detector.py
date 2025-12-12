"""Detector for options sweep activity."""
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from ..models import OptionsTrade, TradeType


class SweepDetector:
    """Detects options sweep orders (multi-exchange aggressive fills)."""
    
    def __init__(
        self,
        min_legs: int = 4,
        max_time_window_seconds: float = 2.0,
        min_premium_per_leg: Decimal = Decimal('10000'),
    ):
        """
        Initialize sweep detector.
        
        Args:
            min_legs: Minimum number of exchange fills to qualify as sweep
            max_time_window_seconds: Max time between fills for sweep
            min_premium_per_leg: Minimum premium per leg to consider
        """
        self.min_legs = min_legs
        self.max_time_window = timedelta(seconds=max_time_window_seconds)
        self.min_premium_per_leg = min_premium_per_leg
        
        # Buffer to track potential sweeps
        self._trade_buffer: List[OptionsTrade] = []
        
    def detect_sweep(self, trade: OptionsTrade) -> Optional[List[OptionsTrade]]:
        """
        Detect if trade is part of a sweep order.
        
        Args:
            trade: Incoming options trade
            
        Returns:
            List of trades forming sweep if detected, None otherwise
        """
        # Add trade to buffer
        self._trade_buffer.append(trade)
        
        # Clean old trades from buffer
        self._clean_buffer(trade.timestamp)
        
        # Check for sweep pattern
        sweep_trades = self._find_sweep_pattern(trade)
        
        if sweep_trades:
            # Mark all trades as sweep
            for t in sweep_trades:
                t.trade_type = TradeType.SWEEP
            return sweep_trades
        
        return None
    
    def _clean_buffer(self, current_time: datetime) -> None:
        """Remove trades outside time window."""
        cutoff_time = current_time - self.max_time_window
        self._trade_buffer = [
            t for t in self._trade_buffer
            if t.timestamp >= cutoff_time
        ]
    
    def _find_sweep_pattern(self, latest_trade: OptionsTrade) -> Optional[List[OptionsTrade]]:
        """
        Find sweep pattern in buffer.
        
        A sweep is characterized by:
        - Same underlying, strike, expiration, order type
        - Multiple exchanges
        - Aggressive execution (at ask for buys, at bid for sells)
        - Rapid execution across exchanges
        """
        # Find matching trades
        matching_trades = [
            t for t in self._trade_buffer
            if (
                t.underlying_symbol == latest_trade.underlying_symbol and
                t.strike == latest_trade.strike and
                t.expiration == latest_trade.expiration and
                t.order_type == latest_trade.order_type and
                t.is_aggressive
            )
        ]
        
        if len(matching_trades) < self.min_legs:
            return None
        
        # Check for multiple exchanges
        exchanges = {t.exchange for t in matching_trades}
        if len(exchanges) < 2:  # At least 2 different exchanges
            return None
        
        # Check time window
        timestamps = [t.timestamp for t in matching_trades]
        time_span = max(timestamps) - min(timestamps)
        if time_span > self.max_time_window:
            return None
        
        # Check premium threshold
        total_premium = sum(t.notional_value for t in matching_trades)
        if total_premium < self.min_premium_per_leg * len(matching_trades):
            return None
        
        # Sort by timestamp
        matching_trades.sort(key=lambda t: t.timestamp)
        
        return matching_trades
    
    def is_aggressive_execution(self, trade: OptionsTrade) -> bool:
        """
        Determine if trade was aggressively executed.
        
        Aggressive = buyer hits ask or seller hits bid
        """
        return trade.execution_side in ['ask', 'above_ask'] or trade.above_ask
    
    def calculate_sweep_score(self, sweep_trades: List[OptionsTrade]) -> float:
        """
        Calculate confidence score for sweep detection.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not sweep_trades:
            return 0.0
        
        score = 0.0
        
        # More legs = higher confidence
        leg_score = min(len(sweep_trades) / 10.0, 0.3)
        score += leg_score
        
        # More exchanges = higher confidence
        exchanges = len({t.exchange for t in sweep_trades})
        exchange_score = min(exchanges / 5.0, 0.2)
        score += exchange_score
        
        # Tighter time window = higher confidence
        timestamps = [t.timestamp for t in sweep_trades]
        time_span = (max(timestamps) - min(timestamps)).total_seconds()
        time_score = max(0.2 - (time_span / 10.0), 0)
        score += time_score
        
        # All aggressive = higher confidence
        if all(t.is_aggressive for t in sweep_trades):
            score += 0.3
        
        return min(score, 1.0)
