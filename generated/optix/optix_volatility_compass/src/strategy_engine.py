"""
Strategy suggestion engine based on volatility conditions.
"""
from typing import List, Dict, Optional
from datetime import datetime
from .models import (
    VolatilityStrategy, StrategyType, VolatilityMetrics,
    VolatilityCondition, VolatilitySkew, VolatilityTermStructure
)


class VolatilityStrategyEngine:
    """Engine for generating trading strategy suggestions based on volatility."""
    
    # Strategy thresholds
    HIGH_IV_RANK_THRESHOLD = 70
    LOW_IV_RANK_THRESHOLD = 30
    HIGH_IV_HV_RATIO = 1.3
    LOW_IV_HV_RATIO = 0.8
    
    def generate_strategies(
        self,
        metrics: VolatilityMetrics,
        skew: Optional[VolatilitySkew] = None,
        term_structure: Optional[VolatilityTermStructure] = None
    ) -> List[VolatilityStrategy]:
        """
        Generate trading strategy suggestions based on volatility analysis.
        
        Args:
            metrics: Core volatility metrics
            skew: Volatility skew analysis (optional)
            term_structure: Term structure analysis (optional)
            
        Returns:
            List of recommended strategies with confidence scores
        """
        strategies = []
        
        # Primary strategy based on IV level
        primary_strategy = self._generate_primary_strategy(metrics)
        if primary_strategy:
            strategies.append(primary_strategy)
        
        # Skew-based strategies
        if skew:
            skew_strategies = self._generate_skew_strategies(metrics, skew)
            strategies.extend(skew_strategies)
        
        # Term structure strategies
        if term_structure:
            term_strategies = self._generate_term_structure_strategies(
                metrics, term_structure
            )
            strategies.extend(term_strategies)
        
        # Sort by confidence
        strategies.sort(key=lambda s: s.confidence, reverse=True)
        
        return strategies
    
    def _generate_primary_strategy(
        self, 
        metrics: VolatilityMetrics
    ) -> Optional[VolatilityStrategy]:
        """Generate primary strategy based on IV rank and percentile."""
        
        iv_rank = metrics.iv_rank
        iv_percentile = metrics.iv_percentile
        iv_hv_ratio = metrics.iv_hv_ratio
        
        # High IV - Sell Premium Strategies
        if iv_rank >= self.HIGH_IV_RANK_THRESHOLD:
            confidence = min(95, 60 + (iv_rank - 70) * 1.5)
            
            reasoning = [
                f"IV Rank at {iv_rank:.1f}% indicates elevated volatility",
                f"IV Percentile at {iv_percentile:.1f}% confirms high IV environment",
                f"Current IV is {iv_hv_ratio:.2f}x historical volatility"
            ]
            
            suggested_actions = [
                "Sell naked puts on quality stocks with support levels",
                "Implement iron condors for range-bound expectations",
                "Sell covered calls to collect premium",
                "Consider short strangles in high IV stocks",
                "Use credit spreads to define risk"
            ]
            
            if iv_rank >= 85:
                suggested_actions.insert(0, "PRIORITY: Aggressive premium selling opportunity")
                risk_level = "medium"
            else:
                risk_level = "low"
            
            return VolatilityStrategy(
                strategy_type=StrategyType.SELL_PREMIUM,
                confidence=confidence,
                strategy_name="Premium Selling Strategy",
                description="Capitalize on elevated implied volatility by selling options premium",
                reasoning=reasoning,
                suggested_actions=suggested_actions,
                risk_level=risk_level,
                iv_rank=iv_rank,
                iv_percentile=iv_percentile,
                iv_hv_ratio=iv_hv_ratio
            )
        
        # Low IV - Buy Premium Strategies
        elif iv_rank <= self.LOW_IV_RANK_THRESHOLD:
            confidence = min(95, 60 + (30 - iv_rank) * 1.5)
            
            reasoning = [
                f"IV Rank at {iv_rank:.1f}% indicates suppressed volatility",
                f"IV Percentile at {iv_percentile:.1f}% confirms low IV environment",
                f"Options are relatively cheap with IV/HV ratio of {iv_hv_ratio:.2f}",
                "Potential for volatility expansion"
            ]
            
            suggested_actions = [
                "Buy long calls/puts for directional plays",
                "Implement long straddles ahead of events",
                "Use debit spreads for leveraged directional exposure",
                "Consider calendar spreads to benefit from IV expansion",
                "Buy protective puts as portfolio insurance"
            ]
            
            if iv_rank <= 15:
                suggested_actions.insert(0, "PRIORITY: Cheap options - premium buying opportunity")
                risk_level = "low"
            else:
                risk_level = "medium"
            
            return VolatilityStrategy(
                strategy_type=StrategyType.BUY_PREMIUM,
                confidence=confidence,
                strategy_name="Premium Buying Strategy",
                description="Take advantage of low implied volatility by buying options premium",
                reasoning=reasoning,
                suggested_actions=suggested_actions,
                risk_level=risk_level,
                iv_rank=iv_rank,
                iv_percentile=iv_percentile,
                iv_hv_ratio=iv_hv_ratio
            )
        
        # Neutral IV - Balanced Strategies
        else:
            confidence = 50
            
            reasoning = [
                f"IV Rank at {iv_rank:.1f}% is in neutral territory",
                "No strong directional volatility bias",
                "Consider balanced or directional strategies"
            ]
            
            suggested_actions = [
                "Focus on directional analysis rather than volatility",
                "Use defined risk strategies (spreads)",
                "Monitor for IV regime changes",
                "Consider stock positions over complex options"
            ]
            
            return VolatilityStrategy(
                strategy_type=StrategyType.NEUTRAL,
                confidence=confidence,
                strategy_name="Neutral Volatility Strategy",
                description="Volatility is in neutral range - focus on directional strategies",
                reasoning=reasoning,
                suggested_actions=suggested_actions,
                risk_level="low",
                iv_rank=iv_rank,
                iv_percentile=iv_percentile,
                iv_hv_ratio=iv_hv_ratio
            )
    
    def _generate_skew_strategies(
        self,
        metrics: VolatilityMetrics,
        skew: VolatilitySkew
    ) -> List[VolatilityStrategy]:
        """Generate strategies based on volatility skew patterns."""
        strategies = []
        
        # Normal skew with high put IV - Sell put spreads
        if skew.skew_type == "normal" and skew.put_call_skew_ratio > 1.1:
            strategies.append(VolatilityStrategy(
                strategy_type=StrategyType.SELL_PREMIUM,
                confidence=70,
                strategy_name="Put Skew Exploitation",
                description="Elevated put skew presents put-selling opportunity",
                reasoning=[
                    f"Put/Call IV ratio is {skew.put_call_skew_ratio:.2f}",
                    "Out-of-the-money puts are relatively expensive",
                    "Normal skew pattern detected"
                ],
                suggested_actions=[
                    "Sell OTM put spreads to capture elevated put premium",
                    "Consider short put verticals at technical support",
                    "Implement put credit spreads for income"
                ],
                risk_level="medium",
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile,
                iv_hv_ratio=metrics.iv_hv_ratio
            ))
        
        # Reverse skew - Call selling opportunity
        elif skew.skew_type == "reverse" and skew.put_call_skew_ratio < 0.9:
            strategies.append(VolatilityStrategy(
                strategy_type=StrategyType.SELL_PREMIUM,
                confidence=70,
                strategy_name="Call Skew Exploitation",
                description="Elevated call skew presents call-selling opportunity",
                reasoning=[
                    f"Put/Call IV ratio is {skew.put_call_skew_ratio:.2f}",
                    "Out-of-the-money calls are relatively expensive",
                    "Reverse skew pattern detected (unusual)"
                ],
                suggested_actions=[
                    "Sell OTM call spreads to capture elevated call premium",
                    "Consider covered calls at resistance levels",
                    "Implement call credit spreads"
                ],
                risk_level="medium",
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile,
                iv_hv_ratio=metrics.iv_hv_ratio
            ))
        
        # Volatility smile - Sell wings
        elif skew.skew_type == "smile":
            strategies.append(VolatilityStrategy(
                strategy_type=StrategyType.SELL_PREMIUM,
                confidence=65,
                strategy_name="Volatility Smile Strategy",
                description="Sell expensive OTM options on both sides",
                reasoning=[
                    "Both OTM puts and calls show elevated IV",
                    "Volatility smile pattern detected",
                    "Far OTM options are overpriced"
                ],
                suggested_actions=[
                    "Implement iron condors to sell both wings",
                    "Consider iron butterflies for neutral outlook",
                    "Sell wide strangles with defined risk"
                ],
                risk_level="medium",
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile,
                iv_hv_ratio=metrics.iv_hv_ratio
            ))
        
        return strategies
    
    def _generate_term_structure_strategies(
        self,
        metrics: VolatilityMetrics,
        term_structure: VolatilityTermStructure
    ) -> List[VolatilityStrategy]:
        """Generate strategies based on term structure shape."""
        strategies = []
        
        # Backwardation - Short-term IV elevated
        if term_structure.structure_shape == "backwardation":
            strategies.append(VolatilityStrategy(
                strategy_type=StrategyType.SELL_PREMIUM,
                confidence=75,
                strategy_name="Term Structure Backwardation Play",
                description="Sell elevated near-term volatility",
                reasoning=[
                    "Front month IV is elevated relative to back months",
                    f"Front month: {term_structure.front_month_iv:.1f}%, Back month: {term_structure.back_month_iv:.1f}%",
                    "Backwardation suggests near-term event or uncertainty"
                ],
                suggested_actions=[
                    "Sell front-month premium before IV crush",
                    "Implement calendar spreads (sell near, buy far)",
                    "Consider diagonal spreads to capture term structure edge",
                    "Monitor for event catalyst that may cause IV spike"
                ],
                risk_level="medium",
                iv_rank=metrics.iv_rank,
                iv_percentile=metrics.iv_percentile,
                iv_hv_ratio=metrics.iv_hv_ratio
            ))
        
        # Contango - Normal term structure
        elif term_structure.structure_shape == "contango":
            if metrics.iv_rank > 50:
                strategies.append(VolatilityStrategy(
                    strategy_type=StrategyType.NEUTRAL,
                    confidence=60,
                    strategy_name="Normal Term Structure",
                    description="Standard term structure with slightly elevated IV",
                    reasoning=[
                        "Normal contango term structure",
                        "Back month IV higher than front month",
                        "No unusual term structure distortions"
                    ],
                    suggested_actions=[
                        "Consider standard premium selling strategies",
                        "Calendar spreads may face headwinds",
                        "Focus on overall IV level rather than term structure"
                    ],
                    risk_level="low",
                    iv_rank=metrics.iv_rank,
                    iv_percentile=metrics.iv_percentile,
                    iv_hv_ratio=metrics.iv_hv_ratio
                ))
        
        return strategies
    
    def get_quick_recommendation(self, iv_rank: float) -> str:
        """
        Get a quick one-line recommendation based on IV rank.
        
        Args:
            iv_rank: Current IV Rank
            
        Returns:
            Quick recommendation string
        """
        if iv_rank >= 80:
            return "🔴 SELL PREMIUM - IV extremely high"
        elif iv_rank >= 60:
            return "🟠 Sell premium - IV elevated"
        elif iv_rank >= 40:
            return "🟡 Neutral - Consider directional strategies"
        elif iv_rank >= 20:
            return "🟢 Buy premium - IV suppressed"
        else:
            return "🟢 BUY PREMIUM - IV extremely low"
