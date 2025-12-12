"""Market maker positioning models."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from decimal import Decimal


class PositionBias(Enum):
    """Market maker position bias."""
    LONG_GAMMA = "long_gamma"
    SHORT_GAMMA = "short_gamma"
    NEUTRAL = "neutral"
    DELTA_HEDGING = "delta_hedging"


@dataclass
class MarketMakerPosition:
    """Represents estimated market maker positioning."""
    
    symbol: str
    underlying_symbol: str
    calculated_at: datetime
    
    # Greeks exposure (estimated)
    net_delta: Decimal
    net_gamma: Decimal
    net_vega: Decimal
    net_theta: Decimal
    
    # Position analysis
    position_bias: PositionBias
    hedge_pressure: str  # "buy", "sell", "neutral"
    
    # Volume metrics
    call_volume: int
    put_volume: int
    call_open_interest: int
    put_open_interest: int
    
    # Price levels
    max_pain_price: Optional[Decimal] = None
    gamma_strike: Optional[Decimal] = None  # Strike with max gamma
    
    # Confidence and metadata
    confidence: float = 0.0  # 0.0 to 1.0
    data_quality_score: float = 1.0
    metadata: Dict = field(default_factory=dict)
    
    @property
    def put_call_volume_ratio(self) -> Optional[Decimal]:
        """Calculate put/call volume ratio."""
        if self.call_volume == 0:
            return None
        return Decimal(self.put_volume) / Decimal(self.call_volume)
    
    @property
    def put_call_oi_ratio(self) -> Optional[Decimal]:
        """Calculate put/call open interest ratio."""
        if self.call_open_interest == 0:
            return None
        return Decimal(self.put_open_interest) / Decimal(self.call_open_interest)
    
    @property
    def is_gamma_squeeze_risk(self) -> bool:
        """Check if there's gamma squeeze risk."""
        return (
            self.position_bias == PositionBias.SHORT_GAMMA and
            abs(self.net_gamma) > Decimal('1000') and
            self.hedge_pressure == "buy"
        )
    
    def to_dict(self) -> dict:
        """Convert position to dictionary."""
        return {
            'symbol': self.symbol,
            'underlying_symbol': self.underlying_symbol,
            'calculated_at': self.calculated_at.isoformat(),
            'net_delta': str(self.net_delta),
            'net_gamma': str(self.net_gamma),
            'net_vega': str(self.net_vega),
            'net_theta': str(self.net_theta),
            'position_bias': self.position_bias.value,
            'hedge_pressure': self.hedge_pressure,
            'put_call_volume_ratio': str(self.put_call_volume_ratio) if self.put_call_volume_ratio else None,
            'put_call_oi_ratio': str(self.put_call_oi_ratio) if self.put_call_oi_ratio else None,
            'is_gamma_squeeze_risk': self.is_gamma_squeeze_risk,
            'confidence': self.confidence,
            'metadata': self.metadata,
        }
