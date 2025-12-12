"""Main GEX service orchestrating all calculations."""
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from src.models.schemas import (
    OptionContract,
    GEXCalculationRequest,
    GEXCalculationResponse,
    GammaExposure,
)
from src.core import (
    GEXCalculator,
    GammaFlipDetector,
    PinRiskAnalyzer,
    MarketMakerAnalyzer,
    AlertEngine,
)
from src.services.storage_service import StorageService
from config.settings import settings


class GEXService:
    """
    Main service for GEX calculations and analysis.
    """
    
    def __init__(self, storage_service: StorageService) -> None:
        """
        Initialize GEX service.
        
        Args:
            storage_service: Storage service for persistence
        """
        self.storage = storage_service
        self.calculator = GEXCalculator()
        self.flip_detector = GammaFlipDetector(
            flip_threshold_pct=settings.gamma_flip_threshold_pct
        )
        self.pin_analyzer = PinRiskAnalyzer(
            pin_risk_days=settings.pin_risk_days_to_expiry
        )
        self.mm_analyzer = MarketMakerAnalyzer()
        self.alert_engine = AlertEngine()
    
    async def calculate_gex(
        self,
        request: GEXCalculationRequest
    ) -> GEXCalculationResponse:
        """
        Calculate GEX and generate complete analysis.
        
        Args:
            request: GEX calculation request
            
        Returns:
            Complete GEX calculation response
        """
        # Calculate gamma exposures for all strikes
        gamma_exposures = self.calculator.calculate_gex_for_chain(
            options_chain=request.options_chain,
            spot_price=request.spot_price
        )
        
        # Create heatmap visualization data
        heatmap = self.calculator.create_heatmap(
            symbol=request.symbol,
            spot_price=request.spot_price,
            gamma_exposures=gamma_exposures
        )
        
        # Detect gamma flip level
        gamma_flip = self.flip_detector.detect_flip_level(
            symbol=request.symbol,
            current_price=request.spot_price,
            gamma_exposures=gamma_exposures
        )
        
        # Analyze market maker positioning
        market_maker_position = self.mm_analyzer.analyze_positioning(
            symbol=request.symbol,
            spot_price=request.spot_price,
            gamma_exposures=gamma_exposures,
            options_chain=request.options_chain
        )
        
        # Analyze pin risk if requested
        pin_risk = None
        if request.calculate_pin_risk:
            pin_risk = self.pin_analyzer.analyze_pin_risk(
                symbol=request.symbol,
                spot_price=request.spot_price,
                options_chain=request.options_chain,
                gamma_exposures=gamma_exposures
            )
        
        # Get previous regime for comparison
        previous_regime = await self._get_previous_regime(request.symbol)
        
        # Generate alerts
        alerts = self.alert_engine.generate_alerts(
            symbol=request.symbol,
            gamma_flip=gamma_flip,
            heatmap=heatmap,
            market_maker_position=market_maker_position,
            pin_risk=pin_risk,
            previous_regime=previous_regime
        )
        
        # Get historical context if requested
        historical_context = None
        if request.include_historical:
            historical_context = await self._get_historical_context(
                request.symbol,
                heatmap.total_net_gex
            )
        
        # Store snapshot
        await self.storage.store_gex_snapshot(
            symbol=request.symbol,
            spot_price=request.spot_price,
            heatmap=heatmap,
            gamma_flip=gamma_flip,
            market_maker_position=market_maker_position,
            pin_risk=pin_risk
        )
        
        # Store alerts
        for alert in alerts:
            await self.storage.store_alert(alert)
        
        # Store historical data
        await self.storage.store_historical_gex(
            symbol=request.symbol,
            spot_price=request.spot_price,
            heatmap=heatmap,
            gamma_flip=gamma_flip
        )
        
        return GEXCalculationResponse(
            symbol=request.symbol,
            spot_price=request.spot_price,
            calculation_timestamp=datetime.utcnow(),
            gamma_exposures=gamma_exposures,
            heatmap=heatmap,
            gamma_flip=gamma_flip,
            market_maker_position=market_maker_position,
            pin_risk=pin_risk,
            alerts=alerts,
            historical_context=historical_context
        )
    
    async def _get_previous_regime(self, symbol: str) -> Optional[str]:
        """
        Get the previous market regime for comparison.
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            Previous regime or None
        """
        last_snapshot = await self.storage.get_latest_snapshot(symbol)
        
        if last_snapshot:
            return last_snapshot.market_regime
        
        return None
    
    async def _get_historical_context(
        self,
        symbol: str,
        current_gex: float
    ) -> dict:
        """
        Get historical context for current GEX values.
        
        Args:
            symbol: Underlying symbol
            current_gex: Current net GEX
            
        Returns:
            Historical context dictionary
        """
        historical_data = await self.storage.get_historical_gex(
            symbol=symbol,
            days=30  # Last 30 days
        )
        
        if not historical_data:
            return {
                "has_data": False,
                "message": "No historical data available"
            }
        
        # Calculate statistics
        gex_values = [h.total_gex for h in historical_data]
        
        avg_gex = sum(gex_values) / len(gex_values)
        max_gex = max(gex_values)
        min_gex = min(gex_values)
        
        # Calculate percentile
        sorted_gex = sorted(gex_values)
        percentile_rank = sum(1 for v in sorted_gex if v <= current_gex) / len(sorted_gex) * 100
        
        return {
            "has_data": True,
            "period_days": 30,
            "current_gex": current_gex,
            "avg_gex": avg_gex,
            "max_gex": max_gex,
            "min_gex": min_gex,
            "percentile": percentile_rank,
            "vs_average": ((current_gex - avg_gex) / abs(avg_gex) * 100) if avg_gex != 0 else 0,
            "interpretation": self._interpret_percentile(percentile_rank)
        }
    
    def _interpret_percentile(self, percentile: float) -> str:
        """
        Interpret GEX percentile ranking.
        
        Args:
            percentile: Percentile rank (0-100)
            
        Returns:
            Interpretation string
        """
        if percentile >= 95:
            return "Extremely high GEX - rare occurrence"
        elif percentile >= 80:
            return "Very high GEX - elevated above normal"
        elif percentile >= 60:
            return "Above average GEX"
        elif percentile >= 40:
            return "Normal GEX levels"
        elif percentile >= 20:
            return "Below average GEX"
        elif percentile >= 5:
            return "Very low GEX - elevated risk"
        else:
            return "Extremely low GEX - rare occurrence"
