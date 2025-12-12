"""
Greeks calculation models and aggregation
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional


@dataclass
class Greeks:
    """
    Represents the Greeks for an option position
    """
    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal
    rho: Decimal
    
    def scale(self, quantity: int) -> 'Greeks':
        """Scale Greeks by quantity"""
        return Greeks(
            delta=self.delta * quantity,
            gamma=self.gamma * quantity,
            theta=self.theta * quantity,
            vega=self.vega * quantity,
            rho=self.rho * quantity
        )
    
    def to_dict(self) -> dict:
        """Convert Greeks to dictionary"""
        return {
            'delta': float(self.delta),
            'gamma': float(self.gamma),
            'theta': float(self.theta),
            'vega': float(self.vega),
            'rho': float(self.rho)
        }


@dataclass
class AggregatedGreeks:
    """
    Aggregated Greeks for a complete strategy
    """
    total_delta: Decimal
    total_gamma: Decimal
    total_theta: Decimal
    total_vega: Decimal
    total_rho: Decimal
    
    # Per-contract Greeks (divided by 100)
    delta_per_contract: Optional[Decimal] = None
    gamma_per_contract: Optional[Decimal] = None
    theta_per_contract: Optional[Decimal] = None
    vega_per_contract: Optional[Decimal] = None
    rho_per_contract: Optional[Decimal] = None
    
    def __post_init__(self):
        """Calculate per-contract Greeks"""
        self.delta_per_contract = self.total_delta / Decimal('100')
        self.gamma_per_contract = self.total_gamma / Decimal('100')
        self.theta_per_contract = self.total_theta / Decimal('100')
        self.vega_per_contract = self.total_vega / Decimal('100')
        self.rho_per_contract = self.total_rho / Decimal('100')
    
    @classmethod
    def from_greeks_list(cls, greeks_list: List[Greeks]) -> 'AggregatedGreeks':
        """Aggregate a list of Greeks"""
        total_delta = sum((g.delta for g in greeks_list), Decimal('0'))
        total_gamma = sum((g.gamma for g in greeks_list), Decimal('0'))
        total_theta = sum((g.theta for g in greeks_list), Decimal('0'))
        total_vega = sum((g.vega for g in greeks_list), Decimal('0'))
        total_rho = sum((g.rho for g in greeks_list), Decimal('0'))
        
        return cls(
            total_delta=total_delta,
            total_gamma=total_gamma,
            total_theta=total_theta,
            total_vega=total_vega,
            total_rho=total_rho
        )
    
    def get_risk_profile(self) -> dict:
        """
        Analyze the risk profile based on Greeks
        """
        profile = {
            'directional_bias': self._analyze_delta(),
            'gamma_exposure': self._analyze_gamma(),
            'time_decay': self._analyze_theta(),
            'volatility_exposure': self._analyze_vega(),
            'interest_rate_sensitivity': self._analyze_rho()
        }
        return profile
    
    def _analyze_delta(self) -> str:
        """Analyze delta exposure"""
        if self.total_delta > Decimal('10'):
            return "Bullish"
        elif self.total_delta < Decimal('-10'):
            return "Bearish"
        else:
            return "Neutral"
    
    def _analyze_gamma(self) -> str:
        """Analyze gamma exposure"""
        if abs(self.total_gamma) > Decimal('0.1'):
            return "High" if self.total_gamma > 0 else "High Negative"
        return "Low"
    
    def _analyze_theta(self) -> str:
        """Analyze theta (time decay)"""
        if self.total_theta < Decimal('-10'):
            return "High Decay"
        elif self.total_theta > Decimal('10'):
            return "Positive Decay"
        else:
            return "Low Decay"
    
    def _analyze_vega(self) -> str:
        """Analyze vega (volatility) exposure"""
        if self.total_vega > Decimal('10'):
            return "Long Volatility"
        elif self.total_vega < Decimal('-10'):
            return "Short Volatility"
        else:
            return "Volatility Neutral"
    
    def _analyze_rho(self) -> str:
        """Analyze rho (interest rate) sensitivity"""
        if abs(self.total_rho) > Decimal('5'):
            return "High" if self.total_rho > 0 else "High Negative"
        return "Low"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'total_delta': float(self.total_delta),
            'total_gamma': float(self.total_gamma),
            'total_theta': float(self.total_theta),
            'total_vega': float(self.total_vega),
            'total_rho': float(self.total_rho),
            'delta_per_contract': float(self.delta_per_contract),
            'gamma_per_contract': float(self.gamma_per_contract),
            'theta_per_contract': float(self.theta_per_contract),
            'vega_per_contract': float(self.vega_per_contract),
            'rho_per_contract': float(self.rho_per_contract),
            'risk_profile': self.get_risk_profile()
        }
