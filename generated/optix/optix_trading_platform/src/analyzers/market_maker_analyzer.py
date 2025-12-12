"""Market maker positioning analyzer."""
from typing import List, Dict, Optional
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from ..models import (
    OptionsTrade, MarketMakerPosition, PositionBias, OrderType
)


class MarketMakerAnalyzer:
    """Analyzes and estimates market maker positioning."""
    
    def __init__(self):
        """Initialize market maker analyzer."""
        # Store option chain data
        self._option_chains: Dict[str, List[Dict]] = defaultdict(list)
        
        # Greeks exposure by symbol
        self._greeks_exposure: Dict[str, Dict] = defaultdict(
            lambda: {
                'delta': Decimal('0'),
                'gamma': Decimal('0'),
                'vega': Decimal('0'),
                'theta': Decimal('0'),
            }
        )
        
    def calculate_position(
        self,
        symbol: str,
        trades: List[OptionsTrade],
        option_chain_data: Optional[Dict] = None,
    ) -> MarketMakerPosition:
        """
        Calculate estimated market maker position.
        
        Args:
            symbol: Underlying symbol
            trades: Recent options trades
            option_chain_data: Option chain data with OI and volume
            
        Returns:
            MarketMakerPosition object
        """
        # Aggregate volume by type
        call_volume = sum(
            t.size for t in trades
            if t.underlying_symbol == symbol and t.order_type == OrderType.CALL
        )
        put_volume = sum(
            t.size for t in trades
            if t.underlying_symbol == symbol and t.order_type == OrderType.PUT
        )
        
        # Get open interest from trades or chain data
        call_oi = 0
        put_oi = 0
        
        if option_chain_data:
            call_oi = option_chain_data.get('call_open_interest', 0)
            put_oi = option_chain_data.get('put_open_interest', 0)
        else:
            # Estimate from trade data
            for trade in trades:
                if trade.underlying_symbol == symbol and trade.open_interest:
                    if trade.order_type == OrderType.CALL:
                        call_oi = max(call_oi, trade.open_interest)
                    else:
                        put_oi = max(put_oi, trade.open_interest)
        
        # Calculate estimated Greeks
        net_delta, net_gamma, net_vega, net_theta = self._estimate_greeks(
            symbol, trades, option_chain_data
        )
        
        # Determine position bias
        position_bias = self._determine_position_bias(
            net_delta, net_gamma, call_volume, put_volume
        )
        
        # Determine hedge pressure
        hedge_pressure = self._calculate_hedge_pressure(
            net_delta, net_gamma, position_bias
        )
        
        # Calculate max pain if we have strike data
        max_pain = self._calculate_max_pain(symbol, trades, option_chain_data)
        
        # Find gamma strike
        gamma_strike = self._find_gamma_strike(symbol, trades)
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(trades, option_chain_data)
        
        return MarketMakerPosition(
            symbol=symbol,
            underlying_symbol=symbol,
            calculated_at=datetime.now(),
            net_delta=net_delta,
            net_gamma=net_gamma,
            net_vega=net_vega,
            net_theta=net_theta,
            position_bias=position_bias,
            hedge_pressure=hedge_pressure,
            call_volume=call_volume,
            put_volume=put_volume,
            call_open_interest=call_oi,
            put_open_interest=put_oi,
            max_pain_price=max_pain,
            gamma_strike=gamma_strike,
            confidence=confidence,
            data_quality_score=1.0 if option_chain_data else 0.6,
        )
    
    def _estimate_greeks(
        self,
        symbol: str,
        trades: List[OptionsTrade],
        option_chain_data: Optional[Dict],
    ) -> tuple:
        """
        Estimate net Greeks exposure for market makers.
        
        Market makers are typically short options, so we estimate their
        position as opposite of retail flow.
        """
        net_delta = Decimal('0')
        net_gamma = Decimal('0')
        net_vega = Decimal('0')
        net_theta = Decimal('0')
        
        for trade in trades:
            if trade.underlying_symbol != symbol:
                continue
            
            # Estimate Greeks based on trade characteristics
            # Simple model: assume standard Greeks for ATM options
            
            # Delta: ~0.5 for ATM, adjust for ITM/OTM
            trade_delta = self._estimate_delta(trade)
            
            # Gamma: highest for ATM, ~0.05
            trade_gamma = self._estimate_gamma(trade)
            
            # Vega: ~0.20 per contract
            trade_vega = Decimal('0.20') * Decimal(trade.size)
            
            # Theta: ~-0.05 per contract per day
            trade_theta = Decimal('-0.05') * Decimal(trade.size)
            
            # If retail is buying (opening), MM is selling (short)
            # So MM Greeks are opposite
            multiplier = Decimal('-1') if trade.is_opening else Decimal('1')
            
            net_delta += trade_delta * multiplier
            net_gamma += trade_gamma * multiplier
            net_vega += trade_vega * multiplier
            net_theta += trade_theta * multiplier
        
        return net_delta, net_gamma, net_vega, net_theta
    
    def _estimate_delta(self, trade: OptionsTrade) -> Decimal:
        """Estimate delta for a trade."""
        if not trade.underlying_price:
            # Default to 0.5 for ATM
            return Decimal('0.5') * Decimal(trade.size)
        
        moneyness = trade.moneyness
        if not moneyness:
            return Decimal('0.5') * Decimal(trade.size)
        
        # Simple approximation
        if trade.order_type == OrderType.CALL:
            if moneyness > Decimal('1.1'):  # Deep ITM
                delta = Decimal('0.8')
            elif moneyness > Decimal('1.02'):  # ITM
                delta = Decimal('0.6')
            elif moneyness > Decimal('0.98'):  # ATM
                delta = Decimal('0.5')
            elif moneyness > Decimal('0.9'):  # OTM
                delta = Decimal('0.3')
            else:  # Deep OTM
                delta = Decimal('0.1')
        else:  # PUT
            if moneyness > Decimal('1.1'):  # Deep ITM
                delta = Decimal('-0.8')
            elif moneyness > Decimal('1.02'):  # ITM
                delta = Decimal('-0.6')
            elif moneyness > Decimal('0.98'):  # ATM
                delta = Decimal('-0.5')
            elif moneyness > Decimal('0.9'):  # OTM
                delta = Decimal('-0.3')
            else:  # Deep OTM
                delta = Decimal('-0.1')
        
        return delta * Decimal(trade.size)
    
    def _estimate_gamma(self, trade: OptionsTrade) -> Decimal:
        """Estimate gamma for a trade."""
        if not trade.underlying_price or not trade.moneyness:
            return Decimal('0.05') * Decimal(trade.size)
        
        moneyness = trade.moneyness
        
        # Gamma is highest for ATM options
        if Decimal('0.98') <= moneyness <= Decimal('1.02'):
            gamma = Decimal('0.08')
        elif Decimal('0.95') <= moneyness <= Decimal('1.05'):
            gamma = Decimal('0.05')
        elif Decimal('0.90') <= moneyness <= Decimal('1.10'):
            gamma = Decimal('0.03')
        else:
            gamma = Decimal('0.01')
        
        # Gamma decreases with time
        dte = trade.days_to_expiration()
        if dte < 7:
            gamma *= Decimal('1.5')  # Higher gamma near expiration
        elif dte > 60:
            gamma *= Decimal('0.5')  # Lower gamma far from expiration
        
        return gamma * Decimal(trade.size)
    
    def _determine_position_bias(
        self,
        net_delta: Decimal,
        net_gamma: Decimal,
        call_volume: int,
        put_volume: int,
    ) -> PositionBias:
        """Determine market maker position bias."""
        # Short gamma = MM sold options, needs to hedge
        if net_gamma < Decimal('-500'):
            return PositionBias.SHORT_GAMMA
        
        # Long gamma = MM bought options
        elif net_gamma > Decimal('500'):
            return PositionBias.LONG_GAMMA
        
        # Delta hedging = actively managing delta exposure
        elif abs(net_delta) > Decimal('1000'):
            return PositionBias.DELTA_HEDGING
        
        else:
            return PositionBias.NEUTRAL
    
    def _calculate_hedge_pressure(
        self,
        net_delta: Decimal,
        net_gamma: Decimal,
        position_bias: PositionBias,
    ) -> str:
        """Calculate hedge pressure direction."""
        # Short gamma MMs need to hedge in direction of movement
        if position_bias == PositionBias.SHORT_GAMMA:
            if net_delta > Decimal('1000'):
                return "sell"  # Short delta, will sell on rallies
            elif net_delta < Decimal('-1000'):
                return "buy"  # Long delta, will buy on dips
        
        # Long gamma MMs hedge opposite
        elif position_bias == PositionBias.LONG_GAMMA:
            if net_delta > Decimal('1000'):
                return "buy"
            elif net_delta < Decimal('-1000'):
                return "sell"
        
        return "neutral"
    
    def _calculate_max_pain(
        self,
        symbol: str,
        trades: List[OptionsTrade],
        option_chain_data: Optional[Dict],
    ) -> Optional[Decimal]:
        """
        Calculate max pain price (price where most options expire worthless).
        
        This is a simplified calculation based on available data.
        """
        if not option_chain_data:
            return None
        
        # Group by strike
        strike_oi = defaultdict(lambda: {'calls': 0, 'puts': 0})
        
        for trade in trades:
            if trade.underlying_symbol == symbol and trade.open_interest:
                strike = trade.strike
                if trade.order_type == OrderType.CALL:
                    strike_oi[strike]['calls'] = max(
                        strike_oi[strike]['calls'],
                        trade.open_interest
                    )
                else:
                    strike_oi[strike]['puts'] = max(
                        strike_oi[strike]['puts'],
                        trade.open_interest
                    )
        
        if not strike_oi:
            return None
        
        # Calculate pain at each strike
        min_pain = float('inf')
        max_pain_strike = None
        
        for test_strike in strike_oi.keys():
            pain = Decimal('0')
            
            for strike, oi in strike_oi.items():
                # Call pain: calls ITM lose value for option holders
                if test_strike > strike:
                    pain += (test_strike - strike) * Decimal(oi['calls'])
                
                # Put pain: puts ITM lose value for option holders
                if test_strike < strike:
                    pain += (strike - test_strike) * Decimal(oi['puts'])
            
            if pain < min_pain:
                min_pain = pain
                max_pain_strike = test_strike
        
        return max_pain_strike
    
    def _find_gamma_strike(
        self,
        symbol: str,
        trades: List[OptionsTrade],
    ) -> Optional[Decimal]:
        """Find strike with maximum gamma exposure."""
        strike_gamma = defaultdict(Decimal)
        
        for trade in trades:
            if trade.underlying_symbol == symbol:
                gamma = self._estimate_gamma(trade)
                strike_gamma[trade.strike] += abs(gamma)
        
        if not strike_gamma:
            return None
        
        return max(strike_gamma.items(), key=lambda x: x[1])[0]
    
    def _calculate_confidence(
        self,
        trades: List[OptionsTrade],
        option_chain_data: Optional[Dict],
    ) -> float:
        """Calculate confidence in position estimate."""
        confidence = 0.5  # Base confidence
        
        # More trades = higher confidence
        if len(trades) >= 100:
            confidence += 0.2
        elif len(trades) >= 50:
            confidence += 0.1
        
        # Option chain data available
        if option_chain_data:
            confidence += 0.2
        
        # Recent data = higher confidence
        if trades and (datetime.now() - trades[-1].timestamp).total_seconds() < 300:
            confidence += 0.1
        
        return min(confidence, 1.0)
