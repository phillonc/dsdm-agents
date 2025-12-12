"""Market maker positioning and hedging analysis."""
from typing import List
from decimal import Decimal
from datetime import datetime

from src.models.schemas import (
    GammaExposure,
    MarketMakerPosition,
    OptionContract,
)


class MarketMakerAnalyzer:
    """
    Analyze market maker positioning and expected hedging behavior.
    
    Market makers typically:
    - Sell options to clients (short gamma)
    - Hedge by buying/selling the underlying
    - Their hedging creates buying/selling pressure
    """
    
    def analyze_positioning(
        self,
        symbol: str,
        spot_price: Decimal,
        gamma_exposures: List[GammaExposure],
        options_chain: List[OptionContract]
    ) -> MarketMakerPosition:
        """
        Analyze market maker positioning and hedging implications.
        
        Args:
            symbol: Underlying symbol
            spot_price: Current spot price
            gamma_exposures: List of gamma exposures
            options_chain: List of option contracts
            
        Returns:
            MarketMakerPosition object
        """
        # Calculate total dealer gamma exposure
        dealer_gamma = self._calculate_dealer_gamma(gamma_exposures)
        
        # Determine position type
        dealer_position = self._determine_dealer_position(dealer_gamma)
        
        # Calculate gamma notional
        gamma_notional = self._calculate_gamma_notional(
            gamma_exposures,
            spot_price
        )
        
        # Calculate vanna exposure
        vanna_exposure = self._calculate_vanna_exposure(options_chain)
        
        # Calculate charm exposure
        charm_exposure = self._calculate_charm_exposure(options_chain)
        
        # Determine hedging pressure
        hedging_pressure = self._determine_hedging_pressure(
            dealer_gamma,
            spot_price,
            gamma_exposures
        )
        
        return MarketMakerPosition(
            symbol=symbol,
            dealer_gamma_exposure=dealer_gamma,
            dealer_position=dealer_position,
            gamma_notional=gamma_notional,
            vanna_exposure=vanna_exposure,
            charm_exposure=charm_exposure,
            hedging_pressure=hedging_pressure,
            timestamp=datetime.utcnow()
        )
    
    def _calculate_dealer_gamma(
        self,
        gamma_exposures: List[GammaExposure]
    ) -> float:
        """
        Calculate total dealer gamma exposure.
        
        Dealers are typically:
        - Short calls (negative gamma from market perspective)
        - Long puts (negative gamma from market perspective)
        
        Args:
            gamma_exposures: List of gamma exposures
            
        Returns:
            Total dealer gamma exposure
        """
        # Sum up net gamma across all strikes
        total_gamma = sum(gex.net_gex for gex in gamma_exposures)
        
        # Dealer position is opposite to market GEX
        return -1 * total_gamma
    
    def _determine_dealer_position(self, dealer_gamma: float) -> str:
        """
        Determine dealer positioning type.
        
        Args:
            dealer_gamma: Dealer gamma exposure
            
        Returns:
            Position type: 'long_gamma', 'short_gamma', or 'neutral'
        """
        threshold = 1e8  # $100M threshold
        
        if dealer_gamma > threshold:
            return "long_gamma"
        elif dealer_gamma < -threshold:
            return "short_gamma"
        else:
            return "neutral"
    
    def _calculate_gamma_notional(
        self,
        gamma_exposures: List[GammaExposure],
        spot_price: Decimal
    ) -> float:
        """
        Calculate notional gamma exposure in dollars.
        
        Args:
            gamma_exposures: List of gamma exposures
            spot_price: Current spot price
            
        Returns:
            Gamma notional in dollars
        """
        # Sum absolute values to get total notional
        total_notional = sum(abs(gex.net_gex) for gex in gamma_exposures)
        
        return total_notional
    
    def _calculate_vanna_exposure(
        self,
        options_chain: List[OptionContract]
    ) -> float:
        """
        Calculate vanna exposure (sensitivity of delta to volatility changes).
        
        Vanna = dDelta/dVol
        
        High vanna means volatility changes significantly impact hedging needs.
        
        Args:
            options_chain: List of option contracts
            
        Returns:
            Total vanna exposure
        """
        # Simplified vanna calculation
        # In production, would use actual vanna from options pricing model
        
        total_vanna = 0.0
        
        for contract in options_chain:
            if contract.gamma and contract.vega:
                # Approximate vanna as correlation between gamma and vega
                # Vanna ≈ Vega * Gamma / Spot
                vanna = contract.vega * contract.gamma * contract.open_interest
                total_vanna += vanna
        
        return total_vanna
    
    def _calculate_charm_exposure(
        self,
        options_chain: List[OptionContract]
    ) -> float:
        """
        Calculate charm exposure (sensitivity of delta to time decay).
        
        Charm = dDelta/dTime
        
        High charm means time decay significantly impacts hedging needs.
        
        Args:
            options_chain: List of option contracts
            
        Returns:
            Total charm exposure
        """
        # Simplified charm calculation
        # In production, would use actual charm from options pricing model
        
        total_charm = 0.0
        
        for contract in options_chain:
            if contract.gamma and contract.theta:
                # Approximate charm as correlation between gamma and theta
                charm = abs(contract.theta) * contract.gamma * contract.open_interest
                total_charm += charm
        
        return total_charm
    
    def _determine_hedging_pressure(
        self,
        dealer_gamma: float,
        spot_price: Decimal,
        gamma_exposures: List[GammaExposure]
    ) -> str:
        """
        Determine expected hedging pressure direction.
        
        When dealers are short gamma:
        - Price rises → they need to buy to hedge (amplifies move)
        - Price falls → they need to sell to hedge (amplifies move)
        
        When dealers are long gamma:
        - Price rises → they need to sell to hedge (dampens move)
        - Price falls → they need to buy to hedge (dampens move)
        
        Args:
            dealer_gamma: Dealer gamma exposure
            spot_price: Current spot price
            gamma_exposures: List of gamma exposures
            
        Returns:
            Hedging pressure: 'buy', 'sell', or 'neutral'
        """
        threshold = 5e8  # $500M threshold
        
        if abs(dealer_gamma) < threshold:
            return "neutral"
        
        # Find gamma distribution around spot
        spot_float = float(spot_price)
        nearby_strikes = [
            gex for gex in gamma_exposures
            if abs(float(gex.strike) - spot_float) / spot_float <= 0.05  # Within 5%
        ]
        
        if not nearby_strikes:
            return "neutral"
        
        # Average nearby gamma
        avg_nearby_gamma = sum(gex.net_gex for gex in nearby_strikes) / len(nearby_strikes)
        
        # Determine pressure based on position
        if dealer_gamma < 0:  # Dealer short gamma
            # Currently destabilizing - amplifies moves
            if avg_nearby_gamma < 0:
                return "sell"  # More selling pressure expected
            else:
                return "buy"  # More buying pressure expected
        else:  # Dealer long gamma
            # Currently stabilizing - dampens moves
            if avg_nearby_gamma > 0:
                return "buy"  # Buying to stabilize
            else:
                return "sell"  # Selling to stabilize
