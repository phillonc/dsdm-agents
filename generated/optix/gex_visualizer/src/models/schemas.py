"""Pydantic schemas for GEX Visualizer."""
from datetime import datetime, date
from typing import List, Optional, Dict, Literal
from decimal import Decimal
from pydantic import BaseModel, Field, computed_field


class OptionContract(BaseModel):
    """Option contract data."""
    
    symbol: str = Field(..., description="Underlying symbol")
    strike: Decimal = Field(..., description="Strike price")
    expiration: date = Field(..., description="Expiration date")
    option_type: Literal["call", "put"] = Field(..., description="Option type")
    bid: Decimal = Field(..., description="Bid price")
    ask: Decimal = Field(..., description="Ask price")
    last: Optional[Decimal] = Field(None, description="Last traded price")
    volume: int = Field(0, description="Trading volume")
    open_interest: int = Field(0, description="Open interest")
    implied_volatility: Optional[float] = Field(None, description="Implied volatility")
    delta: Optional[float] = Field(None, description="Delta")
    gamma: Optional[float] = Field(None, description="Gamma")
    theta: Optional[float] = Field(None, description="Theta")
    vega: Optional[float] = Field(None, description="Vega")
    
    @computed_field
    @property
    def mid_price(self) -> Decimal:
        """Calculate mid price."""
        return (self.bid + self.ask) / 2


class GammaExposure(BaseModel):
    """Gamma exposure calculation result."""
    
    strike: Decimal
    call_gamma: float
    put_gamma: float
    net_gamma: float
    call_gex: float = Field(..., description="Call gamma exposure in dollars")
    put_gex: float = Field(..., description="Put gamma exposure in dollars")
    net_gex: float = Field(..., description="Net gamma exposure in dollars")
    call_open_interest: int
    put_open_interest: int
    
    @computed_field
    @property
    def is_positive_gamma(self) -> bool:
        """Check if net gamma is positive."""
        return self.net_gex > 0
    
    @computed_field
    @property
    def color_code(self) -> str:
        """Get color code for visualization."""
        return "green" if self.is_positive_gamma else "red"


class GEXHeatmap(BaseModel):
    """GEX heatmap data structure."""
    
    symbol: str
    spot_price: Decimal
    timestamp: datetime
    strikes: List[Decimal]
    gex_values: List[float]
    colors: List[str]
    total_call_gex: float
    total_put_gex: float
    total_net_gex: float
    max_gex_strike: Decimal
    min_gex_strike: Decimal
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "SPY",
                "spot_price": "450.00",
                "timestamp": "2024-01-15T10:30:00Z",
                "strikes": [440, 445, 450, 455, 460],
                "gex_values": [-1e9, -5e8, 2e8, 1e9, 5e8],
                "colors": ["red", "red", "green", "green", "green"],
                "total_call_gex": 1.7e9,
                "total_put_gex": -1.5e9,
                "total_net_gex": 2e8,
                "max_gex_strike": "455.00",
                "min_gex_strike": "440.00"
            }
        }


class GammaFlipLevel(BaseModel):
    """Gamma flip level detection result."""
    
    symbol: str
    current_price: Decimal
    gamma_flip_strike: Optional[Decimal] = Field(
        None, description="Strike where gamma flips from negative to positive"
    )
    distance_to_flip: Optional[float] = Field(
        None, description="Distance to flip in dollars"
    )
    distance_pct: Optional[float] = Field(
        None, description="Distance to flip as percentage"
    )
    market_regime: Literal["positive_gamma", "negative_gamma", "near_flip"]
    timestamp: datetime
    
    @computed_field
    @property
    def is_near_flip(self) -> bool:
        """Check if price is near gamma flip level."""
        if self.distance_pct is None:
            return False
        return abs(self.distance_pct) <= 5.0


class PinRiskAnalysis(BaseModel):
    """Pin risk analysis for options near expiration."""
    
    symbol: str
    expiration: date
    days_to_expiration: int
    spot_price: Decimal
    high_oi_strikes: List[Decimal] = Field(
        ..., description="Strikes with high open interest"
    )
    pin_risk_strikes: List[Decimal] = Field(
        ..., description="Strikes with significant pin risk"
    )
    max_pain_strike: Decimal = Field(
        ..., description="Strike with maximum pain for option holders"
    )
    pin_risk_score: float = Field(
        ..., ge=0, le=1, description="Pin risk score (0-1)"
    )
    analysis_timestamp: datetime
    
    @computed_field
    @property
    def has_high_pin_risk(self) -> bool:
        """Check if there's high pin risk."""
        return self.pin_risk_score > 0.7 and self.days_to_expiration <= 5


class MarketMakerPosition(BaseModel):
    """Market maker positioning indicators."""
    
    symbol: str
    dealer_gamma_exposure: float = Field(
        ..., description="Total dealer gamma exposure"
    )
    dealer_position: Literal["long_gamma", "short_gamma", "neutral"]
    gamma_notional: float = Field(
        ..., description="Notional gamma exposure in dollars"
    )
    vanna_exposure: float = Field(
        ..., description="Vanna exposure (dDelta/dVol)"
    )
    charm_exposure: float = Field(
        ..., description="Charm exposure (dDelta/dTime)"
    )
    hedging_pressure: Literal["buy", "sell", "neutral"] = Field(
        ..., description="Expected hedging pressure direction"
    )
    timestamp: datetime
    
    @computed_field
    @property
    def is_destabilizing(self) -> bool:
        """Check if dealer positioning is destabilizing (short gamma)."""
        return self.dealer_position == "short_gamma"


class GEXAlert(BaseModel):
    """GEX alert notification."""
    
    alert_id: str
    alert_type: Literal[
        "gamma_flip_proximity",
        "high_gex_concentration",
        "pin_risk_warning",
        "regime_change"
    ]
    severity: Literal["low", "medium", "high", "critical"]
    symbol: str
    message: str
    details: Dict
    triggered_at: datetime
    acknowledged: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "alert_123",
                "alert_type": "gamma_flip_proximity",
                "severity": "high",
                "symbol": "SPY",
                "message": "Price within 3% of gamma flip level",
                "details": {
                    "current_price": "450.00",
                    "flip_level": "463.50",
                    "distance_pct": 3.0
                },
                "triggered_at": "2024-01-15T10:30:00Z",
                "acknowledged": False
            }
        }


class HistoricalGEX(BaseModel):
    """Historical GEX data point."""
    
    symbol: str
    timestamp: datetime
    spot_price: Decimal
    total_gex: float
    call_gex: float
    put_gex: float
    gamma_flip_level: Optional[Decimal]
    market_regime: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "SPY",
                "timestamp": "2024-01-15T10:30:00Z",
                "spot_price": "450.00",
                "total_gex": 2.5e9,
                "call_gex": 4e9,
                "put_gex": -1.5e9,
                "gamma_flip_level": "445.00",
                "market_regime": "positive_gamma"
            }
        }


class GEXCalculationRequest(BaseModel):
    """Request for GEX calculation."""
    
    symbol: str = Field(..., description="Underlying symbol")
    spot_price: Decimal = Field(..., description="Current spot price")
    options_chain: List[OptionContract] = Field(
        ..., description="List of option contracts"
    )
    calculate_pin_risk: bool = Field(
        True, description="Include pin risk analysis"
    )
    include_historical: bool = Field(
        False, description="Include historical comparison"
    )


class GEXCalculationResponse(BaseModel):
    """Response from GEX calculation."""
    
    symbol: str
    spot_price: Decimal
    calculation_timestamp: datetime
    gamma_exposures: List[GammaExposure]
    heatmap: GEXHeatmap
    gamma_flip: GammaFlipLevel
    market_maker_position: MarketMakerPosition
    pin_risk: Optional[PinRiskAnalysis] = None
    alerts: List[GEXAlert]
    historical_context: Optional[Dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "SPY",
                "spot_price": "450.00",
                "calculation_timestamp": "2024-01-15T10:30:00Z",
                "gamma_exposures": [],
                "heatmap": {},
                "gamma_flip": {},
                "market_maker_position": {},
                "alerts": []
            }
        }
