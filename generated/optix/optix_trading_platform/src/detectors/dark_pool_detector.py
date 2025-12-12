"""Detector for dark pool prints (off-exchange large trades)."""
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timedelta

from ..models import OptionsTrade, TradeType


class DarkPoolDetector:
    """Detects dark pool prints and off-exchange large trades."""
    
    # Known dark pool/off-exchange venues
    DARK_POOL_EXCHANGES = {
        'EDGX', 'EDGA', 'BATS', 'BYX', 'BZX',
        'PEARL', 'MIAX', 'ISE', 'PHLX',
    }
    
    def __init__(
        self,
        min_contracts: int = 50,
        min_premium: Decimal = Decimal('50000'),
        delayed_print_threshold_seconds: float = 30.0,
    ):
        """
        Initialize dark pool detector.
        
        Args:
            min_contracts: Minimum contract size
            min_premium: Minimum premium for dark pool consideration
            delayed_print_threshold_seconds: Time delay suggesting off-exchange
        """
        self.min_contracts = min_contracts
        self.min_premium = min_premium
        self.delayed_print_threshold = timedelta(
            seconds=delayed_print_threshold_seconds
        )
        
        # Track recent prints for delay detection
        self._recent_prints: List[OptionsTrade] = []
        
    def detect_dark_pool(
        self,
        trade: OptionsTrade,
        market_timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Detect if trade is a dark pool print.
        
        Args:
            trade: Options trade to analyze
            market_timestamp: Current market time for delay calculation
            
        Returns:
            True if dark pool print detected
        """
        # Size threshold
        if trade.size < self.min_contracts:
            return False
        
        # Premium threshold
        if trade.notional_value < self.min_premium:
            return False
        
        # Check exchange
        is_dark_exchange = self._is_dark_pool_exchange(trade)
        
        # Check for delayed print
        is_delayed = False
        if market_timestamp:
            delay = market_timestamp - trade.timestamp
            is_delayed = delay > self.delayed_print_threshold
        
        # Check execution characteristics
        has_dp_characteristics = self._has_dark_pool_characteristics(trade)
        
        # Detect if any criteria met
        is_dark_pool = (
            is_dark_exchange or
            is_delayed or
            (has_dp_characteristics and trade.size >= 100)
        )
        
        if is_dark_pool:
            trade.trade_type = TradeType.DARK_POOL
            trade.metadata['dark_pool_detected'] = True
            trade.metadata['dark_exchange'] = is_dark_exchange
            trade.metadata['delayed_print'] = is_delayed
        
        return is_dark_pool
    
    def _is_dark_pool_exchange(self, trade: OptionsTrade) -> bool:
        """Check if trade executed on known dark pool venue."""
        return any(
            dp in trade.exchange.upper()
            for dp in self.DARK_POOL_EXCHANGES
        )
    
    def _has_dark_pool_characteristics(self, trade: OptionsTrade) -> bool:
        """
        Check if trade has dark pool characteristics.
        
        Dark pool trades typically:
        - Execute at mid-market or negotiated price
        - Large size with minimal market impact
        - No aggressive bid/ask hitting
        """
        # Mid-market execution suggests negotiated price
        is_mid_execution = trade.execution_side == 'mid'
        
        # Not aggressive (didn't hit bid/ask)
        is_passive = not trade.is_aggressive
        
        # Large size suggests institutional
        is_large = trade.size >= 100
        
        # Opening position more likely institutional
        is_opening = trade.is_opening
        
        return (is_mid_execution or is_passive) and is_large and is_opening
    
    def calculate_dark_pool_score(
        self,
        trade: OptionsTrade,
        market_timestamp: Optional[datetime] = None,
    ) -> float:
        """
        Calculate confidence score for dark pool detection.
        
        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.0
        
        # Exchange score
        if self._is_dark_pool_exchange(trade):
            score += 0.4
        
        # Delay score
        if market_timestamp:
            delay_seconds = (market_timestamp - trade.timestamp).total_seconds()
            if delay_seconds > 60:
                score += 0.3
            elif delay_seconds > 30:
                score += 0.2
        
        # Execution characteristics
        if trade.execution_side == 'mid':
            score += 0.2
        
        if not trade.is_aggressive:
            score += 0.1
        
        # Size score
        if trade.size >= 200:
            score += 0.2
        elif trade.size >= 100:
            score += 0.1
        
        # Premium score
        if trade.notional_value >= Decimal('500000'):
            score += 0.2
        elif trade.notional_value >= Decimal('100000'):
            score += 0.1
        
        return min(score, 1.0)
    
    def add_to_history(self, trade: OptionsTrade) -> None:
        """Add trade to history for pattern detection."""
        self._recent_prints.append(trade)
        
        # Keep only last hour
        cutoff = datetime.now() - timedelta(hours=1)
        self._recent_prints = [
            t for t in self._recent_prints
            if t.timestamp >= cutoff
        ]
    
    def get_recent_dark_pool_volume(
        self,
        symbol: str,
        lookback_minutes: int = 60,
    ) -> int:
        """Get recent dark pool volume for symbol."""
        cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        
        return sum(
            t.size for t in self._recent_prints
            if (
                t.underlying_symbol == symbol and
                t.timestamp >= cutoff and
                t.trade_type == TradeType.DARK_POOL
            )
        )
