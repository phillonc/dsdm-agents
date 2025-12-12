"""
Example trading strategies
"""
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
from uuid import uuid4

from .base import StrategyBase
from ..models.option import (
    OptionStrategy, OptionLeg, OptionContract,
    OptionSide, OptionType, MarketConditions
)


class SimpleStrategy(StrategyBase):
    """Simple example strategy for testing"""
    
    def __init__(self, params: Dict = None):
        super().__init__("SimpleStrategy", params or {})
        self.entry_threshold = params.get('entry_threshold', 0.02) if params else 0.02
        self.exit_profit_target = params.get('exit_profit_target', 0.20) if params else 0.20
        self.exit_stop_loss = params.get('exit_stop_loss', 0.10) if params else 0.10
    
    async def generate_signals(
        self,
        market_condition: MarketConditions,
        current_positions: Dict[str, OptionStrategy],
        available_capital: float
    ) -> List[OptionStrategy]:
        """Generate simple momentum-based signals"""
        
        signals = []
        
        # Don't generate if we have max positions
        if len(current_positions) >= 5:
            return signals
        
        # Simple logic: if IV is low, buy calls
        if market_condition.implied_volatility and market_condition.implied_volatility < 0.20:
            # Create simple long call strategy
            expiration = market_condition.timestamp.date() + timedelta(days=30)
            strike = market_condition.underlying_price * 1.05  # 5% OTM
            
            contract = OptionContract(
                symbol=market_condition.underlying_symbol,
                expiration=expiration,
                strike=strike,
                option_type=OptionType.CALL
            )
            
            leg = OptionLeg(
                contract=contract,
                side=OptionSide.BUY,
                quantity=1
            )
            
            strategy = OptionStrategy(
                strategy_id=str(uuid4()),
                name="Long Call",
                description="Simple long call on low IV",
                legs=[leg]
            )
            
            signals.append(strategy)
        
        return signals
    
    async def should_exit(
        self,
        position: OptionStrategy,
        market_condition: MarketConditions,
        available_capital: float
    ) -> Tuple[bool, str]:
        """Check exit conditions"""
        
        if not position.entry_time:
            return False, ""
        
        # Calculate current P&L (simplified)
        current_pnl = position.calculate_total_pnl()
        cost_basis = position.calculate_cost_basis()
        
        if cost_basis != 0:
            pnl_percent = current_pnl / abs(cost_basis)
            
            # Profit target
            if pnl_percent >= self.exit_profit_target:
                return True, "profit_target"
            
            # Stop loss
            if pnl_percent <= -self.exit_stop_loss:
                return True, "stop_loss"
        
        # Time-based exit (hold for max 7 days)
        holding_period = (market_condition.timestamp - position.entry_time).days
        if holding_period >= 7:
            return True, "time_exit"
        
        return False, ""


class IronCondorStrategy(StrategyBase):
    """Iron Condor options strategy"""
    
    def __init__(self, params: Dict = None):
        super().__init__("IronCondor", params or {})
        self.wing_width = params.get('wing_width', 10) if params else 10
        self.delta_threshold = params.get('delta_threshold', 0.30) if params else 0.30
    
    async def generate_signals(
        self,
        market_condition: MarketConditions,
        current_positions: Dict[str, OptionStrategy],
        available_capital: float
    ) -> List[OptionStrategy]:
        """Generate iron condor signals in high IV environment"""
        
        signals = []
        
        # Only trade in high IV environments
        if not market_condition.implied_volatility or market_condition.implied_volatility < 0.30:
            return signals
        
        if len(current_positions) >= 3:
            return signals
        
        # Construct iron condor
        expiration = market_condition.timestamp.date() + timedelta(days=45)
        underlying = market_condition.underlying_price
        
        # Short call spread
        short_call_strike = underlying * 1.10
        long_call_strike = short_call_strike + self.wing_width
        
        # Short put spread
        short_put_strike = underlying * 0.90
        long_put_strike = short_put_strike - self.wing_width
        
        legs = [
            # Call spread
            OptionLeg(
                contract=OptionContract(
                    symbol=market_condition.underlying_symbol,
                    expiration=expiration,
                    strike=short_call_strike,
                    option_type=OptionType.CALL
                ),
                side=OptionSide.SELL,
                quantity=1
            ),
            OptionLeg(
                contract=OptionContract(
                    symbol=market_condition.underlying_symbol,
                    expiration=expiration,
                    strike=long_call_strike,
                    option_type=OptionType.CALL
                ),
                side=OptionSide.BUY,
                quantity=1
            ),
            # Put spread
            OptionLeg(
                contract=OptionContract(
                    symbol=market_condition.underlying_symbol,
                    expiration=expiration,
                    strike=short_put_strike,
                    option_type=OptionType.PUT
                ),
                side=OptionSide.SELL,
                quantity=1
            ),
            OptionLeg(
                contract=OptionContract(
                    symbol=market_condition.underlying_symbol,
                    expiration=expiration,
                    strike=long_put_strike,
                    option_type=OptionType.PUT
                ),
                side=OptionSide.BUY,
                quantity=1
            )
        ]
        
        strategy = OptionStrategy(
            strategy_id=str(uuid4()),
            name="Iron Condor",
            description="High IV iron condor",
            legs=legs,
            max_loss=self.wing_width * 100,  # Max loss per spread
            max_profit=None  # Would calculate from premium collected
        )
        
        signals.append(strategy)
        
        return signals
    
    async def should_exit(
        self,
        position: OptionStrategy,
        market_condition: MarketConditions,
        available_capital: float
    ) -> Tuple[bool, str]:
        """Exit at 50% profit or 21 days or if tested"""
        
        if not position.entry_time:
            return False, ""
        
        # Calculate P&L
        current_pnl = position.calculate_total_pnl()
        cost_basis = position.calculate_cost_basis()
        
        if cost_basis != 0:
            pnl_percent = current_pnl / abs(cost_basis)
            
            # Take profit at 50%
            if pnl_percent >= 0.50:
                return True, "profit_target"
            
            # Stop if losing more than 100% of credit
            if pnl_percent <= -1.00:
                return True, "stop_loss"
        
        # Exit at 21 DTE or less
        holding_days = (market_condition.timestamp - position.entry_time).days
        if holding_days >= 24:  # 45 DTE - 21 DTE
            return True, "time_exit"
        
        return False, ""
