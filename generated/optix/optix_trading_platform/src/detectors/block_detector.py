"""Detector for block trades (large institutional orders)."""
from typing import Optional
from decimal import Decimal

from ..models import OptionsTrade, TradeType


class BlockDetector:
    """Detects block trades - large institutional orders."""
    
    def __init__(
        self,
        min_contracts: int = 100,
        min_premium: Decimal = Decimal('100000'),
        size_percentile_threshold: float = 95.0,
    ):
        """
        Initialize block detector.
        
        Args:
            min_contracts: Minimum contract size for block
            min_premium: Minimum premium for block
            size_percentile_threshold: Percentile threshold vs recent volume
        """
        self.min_contracts = min_contracts
        self.min_premium = min_premium
        self.size_percentile_threshold = size_percentile_threshold
        
        # Track average volumes per symbol
        self._symbol_volumes: dict = {}
        
    def detect_block(
        self,
        trade: OptionsTrade,
        recent_avg_size: Optional[int] = None,
    ) -> bool:
        """
        Detect if trade is a block trade.
        
        Args:
            trade: Options trade to analyze
            recent_avg_size: Recent average trade size for comparison
            
        Returns:
            True if block trade detected
        """
        # Size threshold
        if trade.size < self.min_contracts:
            return False
        
        # Premium threshold
        if trade.notional_value < self.min_premium:
            return False
        
        # Compare to recent average if available
        if recent_avg_size and recent_avg_size > 0:
            size_ratio = trade.size / recent_avg_size
            # Trade is 10x+ average size
            if size_ratio < 10.0:
                return False
        
        # Check execution characteristics
        if not self._has_block_characteristics(trade):
            return False
        
        # Mark as block trade
        trade.trade_type = TradeType.BLOCK
        return True
    
    def _has_block_characteristics(self, trade: OptionsTrade) -> bool:
        """
        Check if trade has characteristics of a block trade.
        
        Block trades typically:
        - Execute at or near mid-market
        - Single large fill (not split)
        - May be marked as "opening" position
        """
        # Prefer mid-market or negotiated execution
        is_mid_execution = trade.execution_side == 'mid'
        
        # Opening positions are more likely institutional
        is_opening = trade.is_opening
        
        # Very large size suggests negotiated block
        is_very_large = trade.size >= 500
        
        return is_mid_execution or (is_opening and is_very_large)
    
    def calculate_block_score(
        self,
        trade: OptionsTrade,
        recent_avg_size: Optional[int] = None,
    ) -> float:
        """
        Calculate confidence score for block detection.
        
        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.0
        
        # Size score
        if trade.size >= 500:
            score += 0.3
        elif trade.size >= 250:
            score += 0.2
        elif trade.size >= self.min_contracts:
            score += 0.1
        
        # Premium score
        premium_millions = float(trade.notional_value) / 1_000_000
        if premium_millions >= 5.0:
            score += 0.3
        elif premium_millions >= 1.0:
            score += 0.2
        elif premium_millions >= 0.1:
            score += 0.1
        
        # Execution score
        if trade.execution_side == 'mid':
            score += 0.2
        
        # Opening position score
        if trade.is_opening:
            score += 0.1
        
        # Relative size score
        if recent_avg_size and recent_avg_size > 0:
            size_ratio = trade.size / recent_avg_size
            if size_ratio >= 20:
                score += 0.1
        
        return min(score, 1.0)
    
    def update_volume_stats(self, symbol: str, trade_size: int) -> None:
        """Update rolling volume statistics for symbol."""
        if symbol not in self._symbol_volumes:
            self._symbol_volumes[symbol] = {
                'trades': [],
                'avg_size': 0,
            }
        
        stats = self._symbol_volumes[symbol]
        stats['trades'].append(trade_size)
        
        # Keep only last 100 trades
        if len(stats['trades']) > 100:
            stats['trades'] = stats['trades'][-100:]
        
        # Update average
        stats['avg_size'] = sum(stats['trades']) / len(stats['trades'])
    
    def get_average_size(self, symbol: str) -> Optional[int]:
        """Get average trade size for symbol."""
        if symbol not in self._symbol_volumes:
            return None
        return int(self._symbol_volumes[symbol]['avg_size'])
