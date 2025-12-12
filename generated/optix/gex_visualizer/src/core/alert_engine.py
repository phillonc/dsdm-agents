"""Alert generation engine for GEX events."""
import uuid
from typing import List
from datetime import datetime

from src.models.schemas import (
    GEXAlert,
    GammaFlipLevel,
    PinRiskAnalysis,
    MarketMakerPosition,
    GEXHeatmap,
)
from config.settings import settings


class AlertEngine:
    """
    Generate alerts for significant GEX events and conditions.
    """
    
    def generate_alerts(
        self,
        symbol: str,
        gamma_flip: GammaFlipLevel,
        heatmap: GEXHeatmap,
        market_maker_position: MarketMakerPosition,
        pin_risk: PinRiskAnalysis | None = None,
        previous_regime: str | None = None
    ) -> List[GEXAlert]:
        """
        Generate all relevant alerts based on current conditions.
        
        Args:
            symbol: Underlying symbol
            gamma_flip: Gamma flip level data
            heatmap: GEX heatmap data
            market_maker_position: Market maker positioning
            pin_risk: Pin risk analysis (if available)
            previous_regime: Previous market regime for comparison
            
        Returns:
            List of GEXAlert objects
        """
        alerts = []
        
        # Check for gamma flip proximity
        flip_alert = self._check_gamma_flip_proximity(symbol, gamma_flip)
        if flip_alert:
            alerts.append(flip_alert)
        
        # Check for high GEX concentration
        concentration_alert = self._check_gex_concentration(symbol, heatmap)
        if concentration_alert:
            alerts.append(concentration_alert)
        
        # Check for pin risk
        if pin_risk:
            pin_alert = self._check_pin_risk(symbol, pin_risk)
            if pin_alert:
                alerts.append(pin_alert)
        
        # Check for regime change
        if previous_regime and previous_regime != gamma_flip.market_regime:
            regime_alert = self._check_regime_change(
                symbol,
                previous_regime,
                gamma_flip.market_regime
            )
            if regime_alert:
                alerts.append(regime_alert)
        
        # Check for destabilizing dealer position
        dealer_alert = self._check_dealer_position(symbol, market_maker_position)
        if dealer_alert:
            alerts.append(dealer_alert)
        
        return alerts
    
    def _check_gamma_flip_proximity(
        self,
        symbol: str,
        gamma_flip: GammaFlipLevel
    ) -> GEXAlert | None:
        """
        Check if price is approaching gamma flip level.
        
        Args:
            symbol: Underlying symbol
            gamma_flip: Gamma flip level data
            
        Returns:
            GEXAlert or None
        """
        if not gamma_flip.gamma_flip_strike or gamma_flip.distance_pct is None:
            return None
        
        distance_pct = abs(gamma_flip.distance_pct)
        
        # Determine severity based on distance
        if distance_pct <= 1.0:
            severity = "critical"
            message = f"Price within 1% of gamma flip level at {gamma_flip.gamma_flip_strike}"
        elif distance_pct <= 3.0:
            severity = "high"
            message = f"Price within 3% of gamma flip level at {gamma_flip.gamma_flip_strike}"
        elif distance_pct <= settings.gamma_flip_threshold_pct:
            severity = "medium"
            message = f"Price within {settings.gamma_flip_threshold_pct}% of gamma flip level at {gamma_flip.gamma_flip_strike}"
        else:
            return None
        
        return GEXAlert(
            alert_id=f"flip_{uuid.uuid4().hex[:8]}",
            alert_type="gamma_flip_proximity",
            severity=severity,
            symbol=symbol,
            message=message,
            details={
                "current_price": str(gamma_flip.current_price),
                "flip_level": str(gamma_flip.gamma_flip_strike),
                "distance_pct": gamma_flip.distance_pct,
                "current_regime": gamma_flip.market_regime
            },
            triggered_at=datetime.utcnow()
        )
    
    def _check_gex_concentration(
        self,
        symbol: str,
        heatmap: GEXHeatmap
    ) -> GEXAlert | None:
        """
        Check for high GEX concentration at specific strikes.
        
        Args:
            symbol: Underlying symbol
            heatmap: GEX heatmap data
            
        Returns:
            GEXAlert or None
        """
        # Check if total GEX exceeds threshold
        total_gex_abs = abs(heatmap.total_net_gex)
        
        if total_gex_abs < settings.high_gex_threshold:
            return None
        
        # Determine severity
        if total_gex_abs > settings.high_gex_threshold * 3:
            severity = "critical"
        elif total_gex_abs > settings.high_gex_threshold * 2:
            severity = "high"
        else:
            severity = "medium"
        
        message = f"High GEX concentration detected: ${total_gex_abs/1e9:.2f}B net exposure"
        
        return GEXAlert(
            alert_id=f"conc_{uuid.uuid4().hex[:8]}",
            alert_type="high_gex_concentration",
            severity=severity,
            symbol=symbol,
            message=message,
            details={
                "total_net_gex": heatmap.total_net_gex,
                "total_call_gex": heatmap.total_call_gex,
                "total_put_gex": heatmap.total_put_gex,
                "max_gex_strike": str(heatmap.max_gex_strike),
                "spot_price": str(heatmap.spot_price)
            },
            triggered_at=datetime.utcnow()
        )
    
    def _check_pin_risk(
        self,
        symbol: str,
        pin_risk: PinRiskAnalysis
    ) -> GEXAlert | None:
        """
        Check for significant pin risk near expiration.
        
        Args:
            symbol: Underlying symbol
            pin_risk: Pin risk analysis
            
        Returns:
            GEXAlert or None
        """
        if not pin_risk.has_high_pin_risk:
            return None
        
        # Determine severity based on score and time
        if pin_risk.pin_risk_score > 0.9 and pin_risk.days_to_expiration <= 2:
            severity = "critical"
        elif pin_risk.pin_risk_score > 0.8:
            severity = "high"
        elif pin_risk.pin_risk_score > 0.7:
            severity = "medium"
        else:
            return None
        
        message = (
            f"High pin risk detected: {pin_risk.pin_risk_score:.1%} score, "
            f"{pin_risk.days_to_expiration} days to expiration"
        )
        
        return GEXAlert(
            alert_id=f"pin_{uuid.uuid4().hex[:8]}",
            alert_type="pin_risk_warning",
            severity=severity,
            symbol=symbol,
            message=message,
            details={
                "pin_risk_score": pin_risk.pin_risk_score,
                "days_to_expiration": pin_risk.days_to_expiration,
                "expiration": pin_risk.expiration.isoformat(),
                "max_pain_strike": str(pin_risk.max_pain_strike),
                "pin_risk_strikes": [str(s) for s in pin_risk.pin_risk_strikes],
                "spot_price": str(pin_risk.spot_price)
            },
            triggered_at=datetime.utcnow()
        )
    
    def _check_regime_change(
        self,
        symbol: str,
        previous_regime: str,
        current_regime: str
    ) -> GEXAlert | None:
        """
        Check for market regime change.
        
        Args:
            symbol: Underlying symbol
            previous_regime: Previous market regime
            current_regime: Current market regime
            
        Returns:
            GEXAlert or None
        """
        # Only alert on significant changes
        significant_changes = [
            ("positive_gamma", "negative_gamma"),
            ("negative_gamma", "positive_gamma"),
            ("positive_gamma", "near_flip"),
            ("negative_gamma", "near_flip"),
        ]
        
        if (previous_regime, current_regime) not in significant_changes:
            return None
        
        severity = "high" if "near_flip" in [previous_regime, current_regime] else "medium"
        
        message = f"Market regime change: {previous_regime} → {current_regime}"
        
        return GEXAlert(
            alert_id=f"regime_{uuid.uuid4().hex[:8]}",
            alert_type="regime_change",
            severity=severity,
            symbol=symbol,
            message=message,
            details={
                "previous_regime": previous_regime,
                "current_regime": current_regime,
                "implication": self._get_regime_implication(current_regime)
            },
            triggered_at=datetime.utcnow()
        )
    
    def _check_dealer_position(
        self,
        symbol: str,
        market_maker_position: MarketMakerPosition
    ) -> GEXAlert | None:
        """
        Check for destabilizing dealer positioning.
        
        Args:
            symbol: Underlying symbol
            market_maker_position: Market maker positioning data
            
        Returns:
            GEXAlert or None
        """
        if not market_maker_position.is_destabilizing:
            return None
        
        severity = "medium"
        message = "Dealers in destabilizing short gamma position - expect amplified volatility"
        
        return GEXAlert(
            alert_id=f"dealer_{uuid.uuid4().hex[:8]}",
            alert_type="regime_change",
            severity=severity,
            symbol=symbol,
            message=message,
            details={
                "dealer_position": market_maker_position.dealer_position,
                "dealer_gamma_exposure": market_maker_position.dealer_gamma_exposure,
                "hedging_pressure": market_maker_position.hedging_pressure,
                "implication": "Price moves may be amplified by dealer hedging"
            },
            triggered_at=datetime.utcnow()
        )
    
    def _get_regime_implication(self, regime: str) -> str:
        """
        Get trading implications for a regime.
        
        Args:
            regime: Market regime
            
        Returns:
            Implication description
        """
        implications = {
            "positive_gamma": "Dealers will dampen volatility by hedging against moves",
            "negative_gamma": "Dealers will amplify volatility by hedging with moves",
            "near_flip": "High uncertainty - market at inflection point",
            "neutral": "Balanced positioning with minimal dealer impact"
        }
        
        return implications.get(regime, "Unknown regime implications")
