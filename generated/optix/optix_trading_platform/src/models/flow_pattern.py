"""Flow pattern detection models."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
from decimal import Decimal


class PatternType(Enum):
    """Type of flow pattern detected."""
    AGGRESSIVE_CALL_BUYING = "aggressive_call_buying"
    AGGRESSIVE_PUT_BUYING = "aggressive_put_buying"
    LARGE_SWEEP = "large_sweep"
    BLOCK_TRADE = "block_trade"
    DARK_POOL_PRINT = "dark_pool_print"
    SPREAD_PATTERN = "spread_pattern"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    UNUSUAL_VOLUME = "unusual_volume"
    INSTITUTIONAL_FLOW = "institutional_flow"


class SmartMoneySignal(Enum):
    """Smart money signal strength."""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


@dataclass
class FlowPattern:
    """Represents a detected flow pattern."""
    
    pattern_id: str
    pattern_type: PatternType
    symbol: str
    underlying_symbol: str
    detected_at: datetime
    
    # Pattern characteristics
    total_premium: Decimal
    total_contracts: int
    trade_count: int
    
    # Smart money indicators
    signal: SmartMoneySignal
    confidence_score: float  # 0.0 to 1.0
    
    # Related trades
    trade_ids: List[str] = field(default_factory=list)
    
    # Analysis details
    call_premium: Decimal = Decimal('0')
    put_premium: Decimal = Decimal('0')
    call_put_ratio: Optional[Decimal] = None
    
    # Timing and flow
    duration_seconds: Optional[float] = None
    average_execution_price: Optional[Decimal] = None
    
    # Market impact
    estimated_impact: str = "low"  # "low", "medium", "high"
    
    # Metadata
    description: str = ""
    metadata: Dict = field(default_factory=dict)
    
    @property
    def net_sentiment(self) -> str:
        """Calculate net sentiment from call/put premiums."""
        if self.call_premium > self.put_premium * Decimal('1.5'):
            return "bullish"
        elif self.put_premium > self.call_premium * Decimal('1.5'):
            return "bearish"
        else:
            return "neutral"
    
    @property
    def is_significant(self) -> bool:
        """Check if pattern is significant based on size and confidence."""
        return (
            self.confidence_score >= 0.7 and
            self.total_premium >= Decimal('100000')  # $100K+
        )
    
    def to_dict(self) -> dict:
        """Convert pattern to dictionary."""
        return {
            'pattern_id': self.pattern_id,
            'pattern_type': self.pattern_type.value,
            'symbol': self.symbol,
            'underlying_symbol': self.underlying_symbol,
            'detected_at': self.detected_at.isoformat(),
            'total_premium': str(self.total_premium),
            'total_contracts': self.total_contracts,
            'trade_count': self.trade_count,
            'signal': self.signal.value,
            'confidence_score': self.confidence_score,
            'net_sentiment': self.net_sentiment,
            'is_significant': self.is_significant,
            'description': self.description,
            'metadata': self.metadata,
        }
