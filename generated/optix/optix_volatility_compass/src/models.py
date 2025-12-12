"""
Data models for Volatility Compass feature.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum


class VolatilityCondition(Enum):
    """Volatility condition categories."""
    EXTREMELY_HIGH = "extremely_high"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    EXTREMELY_LOW = "extremely_low"


class StrategyType(Enum):
    """Trading strategy types based on volatility."""
    SELL_PREMIUM = "sell_premium"
    BUY_PREMIUM = "buy_premium"
    NEUTRAL = "neutral"


@dataclass
class VolatilityMetrics:
    """Core volatility metrics for a symbol."""
    symbol: str
    timestamp: datetime
    
    # Current IV metrics
    current_iv: float  # Current implied volatility (annualized)
    iv_rank: float  # IV Rank (0-100)
    iv_percentile: float  # IV Percentile (0-100)
    
    # Historical volatility
    historical_volatility_30d: float
    historical_volatility_60d: float
    historical_volatility_90d: float
    
    # IV vs HV comparison
    iv_hv_ratio: float  # Current IV / HV ratio
    
    # Volatility condition
    condition: VolatilityCondition
    
    # Additional metrics
    average_iv_30d: float
    average_iv_60d: float
    min_iv_52w: float
    max_iv_52w: float


@dataclass
class VolatilitySkew:
    """Volatility skew analysis for a specific expiration."""
    symbol: str
    expiration_date: datetime
    days_to_expiration: int
    
    # ATM (at-the-money) reference
    atm_strike: float
    atm_iv: float
    
    # Call side data (OTM calls)
    call_strikes: List[float]
    call_ivs: List[float]
    call_skew_slope: float  # Slope of call skew
    
    # Put side data (OTM puts)
    put_strikes: List[float]
    put_ivs: List[float]
    put_skew_slope: float  # Slope of put skew
    
    # Skew metrics
    put_call_skew_ratio: float  # Average put IV / Average call IV
    skew_type: str  # "normal", "reverse", "flat"


@dataclass
class TermStructurePoint:
    """Single point in the volatility term structure."""
    expiration_date: datetime
    days_to_expiration: int
    atm_iv: float
    call_iv_avg: float
    put_iv_avg: float
    volume: int
    open_interest: int


@dataclass
class VolatilityTermStructure:
    """Complete term structure analysis."""
    symbol: str
    timestamp: datetime
    current_price: float
    
    # Term structure points (sorted by expiration)
    term_points: List[TermStructurePoint]
    
    # Term structure shape
    structure_shape: str  # "contango", "backwardation", "flat"
    front_month_iv: float
    back_month_iv: float
    term_structure_slope: float


@dataclass
class VolatilitySurfacePoint:
    """Single point on the volatility surface."""
    strike: float
    days_to_expiration: int
    implied_volatility: float
    delta: Optional[float] = None
    moneyness: Optional[float] = None  # strike/spot ratio


@dataclass
class VolatilitySurface:
    """3D volatility surface data."""
    symbol: str
    timestamp: datetime
    current_price: float
    
    # Surface data points
    surface_points: List[VolatilitySurfacePoint]
    
    # Expirations included
    expirations: List[datetime]
    
    # Strike range
    min_strike: float
    max_strike: float
    
    # Surface characteristics
    surface_curvature: float  # Measure of surface convexity


@dataclass
class VolatilityStrategy:
    """Trading strategy suggestion based on volatility conditions."""
    strategy_type: StrategyType
    confidence: float  # 0-100
    
    # Strategy details
    strategy_name: str
    description: str
    reasoning: List[str]
    
    # Specific suggestions
    suggested_actions: List[str]
    risk_level: str  # "low", "medium", "high"
    
    # Supporting metrics
    iv_rank: float
    iv_percentile: float
    iv_hv_ratio: float


@dataclass
class VolatilityAlert:
    """Alert for significant volatility changes."""
    alert_id: str
    symbol: str
    timestamp: datetime
    alert_type: str  # "iv_spike", "iv_crush", "skew_change", "rank_threshold"
    
    # Alert details
    severity: str  # "low", "medium", "high", "critical"
    message: str
    
    # Metrics triggering alert
    current_value: float
    previous_value: float
    change_percent: float
    threshold: float
    
    # Context
    iv_rank: float
    iv_percentile: float


@dataclass
class WatchlistVolatilityAnalysis:
    """Bulk volatility analysis for a watchlist."""
    watchlist_name: str
    timestamp: datetime
    symbols: List[str]
    
    # Individual symbol analyses
    symbol_metrics: Dict[str, VolatilityMetrics]
    
    # Aggregate statistics
    average_iv_rank: float
    average_iv_percentile: float
    high_iv_symbols: List[str]  # IV Rank > 70
    low_iv_symbols: List[str]  # IV Rank < 30
    
    # Opportunities
    premium_selling_candidates: List[Tuple[str, float]]  # (symbol, iv_rank)
    premium_buying_candidates: List[Tuple[str, float]]  # (symbol, iv_rank)
    
    # Alerts summary
    active_alerts: List[VolatilityAlert]


@dataclass
class VolatilityCompassReport:
    """Comprehensive volatility analysis report."""
    symbol: str
    timestamp: datetime
    
    # Core metrics
    metrics: VolatilityMetrics
    
    # Detailed analyses
    term_structure: VolatilityTermStructure
    skew_analysis: List[VolatilitySkew]  # Multiple expirations
    surface: VolatilitySurface
    
    # Strategy and alerts
    strategies: List[VolatilityStrategy]
    alerts: List[VolatilityAlert]
    
    # Historical context
    iv_rank_history: List[Tuple[datetime, float]]  # Last 30 days
    iv_percentile_history: List[Tuple[datetime, float]]  # Last 30 days
