"""Gamma flip level detection engine."""
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from src.models.schemas import GammaExposure, GammaFlipLevel


class GammaFlipDetector:
    """
    Detect gamma flip levels where dealer positioning changes from
    long gamma to short gamma (or vice versa).
    
    This is critical as it indicates a regime change in market dynamics.
    """
    
    def __init__(self, flip_threshold_pct: float = 5.0) -> None:
        """
        Initialize gamma flip detector.
        
        Args:
            flip_threshold_pct: Percentage threshold for "near flip" alerts
        """
        self.flip_threshold_pct = flip_threshold_pct
    
    def detect_flip_level(
        self,
        symbol: str,
        current_price: Decimal,
        gamma_exposures: List[GammaExposure]
    ) -> GammaFlipLevel:
        """
        Detect the gamma flip level from GEX data.
        
        The flip level is where net GEX crosses from negative to positive
        (or vice versa). This is where market maker hedging behavior changes.
        
        Args:
            symbol: Underlying symbol
            current_price: Current spot price
            gamma_exposures: List of gamma exposures by strike
            
        Returns:
            GammaFlipLevel object
        """
        if not gamma_exposures:
            return GammaFlipLevel(
                symbol=symbol,
                current_price=current_price,
                market_regime="neutral",
                timestamp=datetime.utcnow()
            )
        
        # Sort by strike
        sorted_exposures = sorted(gamma_exposures, key=lambda x: x.strike)
        
        # Find flip level
        flip_strike = self._find_flip_strike(sorted_exposures)
        
        # Determine current regime based on spot price
        current_regime = self._determine_regime(current_price, sorted_exposures)
        
        # Calculate distance to flip
        distance_to_flip = None
        distance_pct = None
        
        if flip_strike:
            distance_to_flip = float(flip_strike - current_price)
            distance_pct = (distance_to_flip / float(current_price)) * 100
        
        # Determine if near flip
        if distance_pct is not None and abs(distance_pct) <= self.flip_threshold_pct:
            regime = "near_flip"
        else:
            regime = current_regime
        
        return GammaFlipLevel(
            symbol=symbol,
            current_price=current_price,
            gamma_flip_strike=flip_strike,
            distance_to_flip=distance_to_flip,
            distance_pct=distance_pct,
            market_regime=regime,
            timestamp=datetime.utcnow()
        )
    
    def _find_flip_strike(
        self,
        sorted_exposures: List[GammaExposure]
    ) -> Optional[Decimal]:
        """
        Find the strike where GEX flips from negative to positive.
        
        Args:
            sorted_exposures: Gamma exposures sorted by strike
            
        Returns:
            Flip strike or None if no flip found
        """
        for i in range(len(sorted_exposures) - 1):
            current_gex = sorted_exposures[i].net_gex
            next_gex = sorted_exposures[i + 1].net_gex
            
            # Check for sign change (flip)
            if current_gex < 0 and next_gex >= 0:
                # Interpolate to find more precise flip level
                return self._interpolate_flip_level(
                    sorted_exposures[i],
                    sorted_exposures[i + 1]
                )
            elif current_gex >= 0 and next_gex < 0:
                # Flip from positive to negative
                return self._interpolate_flip_level(
                    sorted_exposures[i],
                    sorted_exposures[i + 1]
                )
        
        return None
    
    def _interpolate_flip_level(
        self,
        exposure1: GammaExposure,
        exposure2: GammaExposure
    ) -> Decimal:
        """
        Interpolate the exact strike where GEX crosses zero.
        
        Args:
            exposure1: First exposure point
            exposure2: Second exposure point
            
        Returns:
            Interpolated flip strike
        """
        # Linear interpolation
        gex1 = exposure1.net_gex
        gex2 = exposure2.net_gex
        strike1 = float(exposure1.strike)
        strike2 = float(exposure2.strike)
        
        if gex2 == gex1:
            # No change, return midpoint
            return Decimal(str((strike1 + strike2) / 2))
        
        # Calculate zero crossing point
        flip_strike = strike1 - gex1 * (strike2 - strike1) / (gex2 - gex1)
        
        return Decimal(str(round(flip_strike, 2)))
    
    def _determine_regime(
        self,
        current_price: Decimal,
        sorted_exposures: List[GammaExposure]
    ) -> str:
        """
        Determine current market regime based on spot price location.
        
        Args:
            current_price: Current spot price
            sorted_exposures: Gamma exposures sorted by strike
            
        Returns:
            Market regime: 'positive_gamma', 'negative_gamma', or 'neutral'
        """
        # Find the exposures around current price
        below_strikes = [e for e in sorted_exposures if e.strike <= current_price]
        above_strikes = [e for e in sorted_exposures if e.strike > current_price]
        
        if not below_strikes and not above_strikes:
            return "neutral"
        
        # Get nearest strikes
        if below_strikes:
            below_gex = below_strikes[-1].net_gex
        else:
            below_gex = 0
        
        if above_strikes:
            above_gex = above_strikes[0].net_gex
        else:
            above_gex = 0
        
        # Average GEX around current price
        avg_gex = (below_gex + above_gex) / 2
        
        if avg_gex > 0:
            return "positive_gamma"
        elif avg_gex < 0:
            return "negative_gamma"
        else:
            return "neutral"
    
    def is_approaching_flip(self, gamma_flip: GammaFlipLevel) -> bool:
        """
        Check if price is approaching a gamma flip level.
        
        Args:
            gamma_flip: GammaFlipLevel object
            
        Returns:
            True if approaching flip
        """
        return gamma_flip.is_near_flip
