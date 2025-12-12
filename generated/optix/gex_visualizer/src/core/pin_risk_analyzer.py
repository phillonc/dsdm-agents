"""Pin risk analysis for options near expiration."""
from typing import List, Dict
from decimal import Decimal
from datetime import datetime, date

from src.models.schemas import OptionContract, GammaExposure, PinRiskAnalysis
from config.settings import settings


class PinRiskAnalyzer:
    """
    Analyze pin risk - the tendency for the underlying to gravitate toward
    strikes with high open interest near expiration.
    
    This occurs because market makers hedging large positions can influence
    the underlying price.
    """
    
    def __init__(self, pin_risk_days: int = 5) -> None:
        """
        Initialize pin risk analyzer.
        
        Args:
            pin_risk_days: Days to expiration threshold for pin risk analysis
        """
        self.pin_risk_days = pin_risk_days
    
    def analyze_pin_risk(
        self,
        symbol: str,
        spot_price: Decimal,
        options_chain: List[OptionContract],
        gamma_exposures: List[GammaExposure]
    ) -> PinRiskAnalysis | None:
        """
        Analyze pin risk for options near expiration.
        
        Args:
            symbol: Underlying symbol
            spot_price: Current spot price
            options_chain: List of option contracts
            gamma_exposures: List of gamma exposures
            
        Returns:
            PinRiskAnalysis object or None if no near-term expiration
        """
        # Find nearest expiration
        expirations = sorted(set(opt.expiration for opt in options_chain))
        
        if not expirations:
            return None
        
        nearest_expiration = expirations[0]
        days_to_expiration = (nearest_expiration - date.today()).days
        
        # Only analyze if within threshold
        if days_to_expiration > self.pin_risk_days or days_to_expiration < 0:
            return None
        
        # Filter options for nearest expiration
        near_expiry_options = [
            opt for opt in options_chain
            if opt.expiration == nearest_expiration
        ]
        
        # Calculate metrics
        high_oi_strikes = self._find_high_oi_strikes(near_expiry_options)
        pin_risk_strikes = self._calculate_pin_risk_strikes(
            near_expiry_options,
            spot_price,
            gamma_exposures
        )
        max_pain_strike = self._calculate_max_pain(near_expiry_options, spot_price)
        pin_risk_score = self._calculate_pin_risk_score(
            spot_price,
            high_oi_strikes,
            days_to_expiration
        )
        
        return PinRiskAnalysis(
            symbol=symbol,
            expiration=nearest_expiration,
            days_to_expiration=days_to_expiration,
            spot_price=spot_price,
            high_oi_strikes=high_oi_strikes,
            pin_risk_strikes=pin_risk_strikes,
            max_pain_strike=max_pain_strike,
            pin_risk_score=pin_risk_score,
            analysis_timestamp=datetime.utcnow()
        )
    
    def _find_high_oi_strikes(
        self,
        options: List[OptionContract],
        top_n: int = 5
    ) -> List[Decimal]:
        """
        Find strikes with highest open interest.
        
        Args:
            options: List of option contracts
            top_n: Number of top strikes to return
            
        Returns:
            List of strikes with highest OI
        """
        # Sum OI by strike
        strike_oi: Dict[Decimal, int] = {}
        
        for opt in options:
            if opt.strike not in strike_oi:
                strike_oi[opt.strike] = 0
            strike_oi[opt.strike] += opt.open_interest
        
        # Sort by OI
        sorted_strikes = sorted(
            strike_oi.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [strike for strike, _ in sorted_strikes[:top_n]]
    
    def _calculate_pin_risk_strikes(
        self,
        options: List[OptionContract],
        spot_price: Decimal,
        gamma_exposures: List[GammaExposure]
    ) -> List[Decimal]:
        """
        Calculate strikes with significant pin risk.
        
        Pin risk is higher at strikes with:
        1. High open interest
        2. High gamma exposure
        3. Close to current spot price
        
        Args:
            options: List of option contracts
            spot_price: Current spot price
            gamma_exposures: List of gamma exposures
            
        Returns:
            List of strikes with pin risk
        """
        # Calculate pin risk score for each strike
        pin_scores: Dict[Decimal, float] = {}
        
        for gex in gamma_exposures:
            strike = gex.strike
            
            # Factor 1: Total open interest
            total_oi = gex.call_open_interest + gex.put_open_interest
            
            # Factor 2: Gamma exposure magnitude
            gamma_magnitude = abs(gex.net_gex)
            
            # Factor 3: Distance to spot (inverse relationship)
            distance = abs(float(strike - spot_price))
            distance_factor = 1 / (1 + distance)
            
            # Combined pin risk score
            pin_score = (total_oi / 1000) * gamma_magnitude * distance_factor
            pin_scores[strike] = pin_score
        
        # Return top strikes with pin risk
        sorted_pins = sorted(
            pin_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return strikes within 10% of spot price with significant pin risk
        threshold = sorted_pins[0][1] * 0.3 if sorted_pins else 0
        
        pin_strikes = [
            strike for strike, score in sorted_pins
            if score >= threshold and abs(float(strike - spot_price)) / float(spot_price) <= 0.1
        ]
        
        return pin_strikes[:5]  # Top 5
    
    def _calculate_max_pain(
        self,
        options: List[OptionContract],
        spot_price: Decimal
    ) -> Decimal:
        """
        Calculate max pain strike - the strike where option holders lose most.
        
        Args:
            options: List of option contracts
            spot_price: Current spot price
            
        Returns:
            Max pain strike
        """
        # Group by strike
        strikes: Dict[Decimal, Dict[str, int]] = {}
        
        for opt in options:
            if opt.strike not in strikes:
                strikes[opt.strike] = {"call_oi": 0, "put_oi": 0}
            
            if opt.option_type == "call":
                strikes[opt.strike]["call_oi"] = opt.open_interest
            else:
                strikes[opt.strike]["put_oi"] = opt.open_interest
        
        # Calculate pain for each strike
        pain_by_strike: Dict[Decimal, float] = {}
        
        for strike in strikes.keys():
            total_pain = 0.0
            
            # Calculate pain at this strike
            for s, oi in strikes.items():
                strike_val = float(strike)
                s_val = float(s)
                
                # Call pain: max(0, strike - s) * call_oi
                if strike_val > s_val:
                    total_pain += (strike_val - s_val) * oi["call_oi"]
                
                # Put pain: max(0, s - strike) * put_oi
                if s_val > strike_val:
                    total_pain += (s_val - strike_val) * oi["put_oi"]
            
            pain_by_strike[strike] = total_pain
        
        # Max pain is strike with minimum total pain
        if not pain_by_strike:
            return spot_price
        
        max_pain_strike = min(pain_by_strike.items(), key=lambda x: x[1])[0]
        
        return max_pain_strike
    
    def _calculate_pin_risk_score(
        self,
        spot_price: Decimal,
        high_oi_strikes: List[Decimal],
        days_to_expiration: int
    ) -> float:
        """
        Calculate overall pin risk score (0-1).
        
        Args:
            spot_price: Current spot price
            high_oi_strikes: Strikes with high OI
            days_to_expiration: Days until expiration
            
        Returns:
            Pin risk score between 0 and 1
        """
        if not high_oi_strikes or days_to_expiration > self.pin_risk_days:
            return 0.0
        
        # Factor 1: Proximity to high OI strike
        min_distance = min(
            abs(float(strike - spot_price)) / float(spot_price)
            for strike in high_oi_strikes
        )
        
        proximity_score = max(0, 1 - min_distance * 10)  # Within 10%
        
        # Factor 2: Time decay (higher risk closer to expiration)
        time_score = 1 - (days_to_expiration / self.pin_risk_days)
        
        # Combined score
        pin_risk_score = (proximity_score * 0.6 + time_score * 0.4)
        
        return min(1.0, max(0.0, pin_risk_score))
