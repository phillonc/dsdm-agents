"""
Pre-defined strategy templates for common options strategies.

This module provides factory functions to create popular options strategies.
"""

from datetime import date, timedelta
from typing import Optional
from .models import (
    OptionsStrategy, OptionLeg, OptionType, PositionType, 
    StrategyType, Greeks
)


class StrategyTemplates:
    """Factory class for creating strategy templates."""
    
    @staticmethod
    def create_iron_condor(
        underlying_symbol: str,
        current_price: float,
        expiration: date,
        wing_width: float = 5.0,
        body_width: float = 10.0,
        quantity: int = 1
    ) -> OptionsStrategy:
        """
        Create an Iron Condor strategy.
        
        Structure:
        - Sell OTM Put
        - Buy further OTM Put
        - Sell OTM Call
        - Buy further OTM Call
        
        Args:
            underlying_symbol: The underlying asset symbol
            current_price: Current price of the underlying
            expiration: Expiration date
            wing_width: Width of protective wings
            body_width: Width between short strikes
            quantity: Number of contracts
        """
        strategy = OptionsStrategy(
            name=f"Iron Condor - {underlying_symbol}",
            strategy_type=StrategyType.IRON_CONDOR,
            underlying_symbol=underlying_symbol
        )
        
        # Calculate strikes
        short_put_strike = current_price - body_width / 2
        long_put_strike = short_put_strike - wing_width
        short_call_strike = current_price + body_width / 2
        long_call_strike = short_call_strike + wing_width
        
        # Create legs with estimated premiums
        legs = [
            OptionLeg(
                option_type=OptionType.PUT,
                position_type=PositionType.LONG,
                strike=long_put_strike,
                expiration=expiration,
                quantity=quantity,
                premium=0.50,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.25,
                greeks=Greeks(delta=-0.10, gamma=0.02, theta=0.05, vega=0.08, rho=-0.02)
            ),
            OptionLeg(
                option_type=OptionType.PUT,
                position_type=PositionType.SHORT,
                strike=short_put_strike,
                expiration=expiration,
                quantity=quantity,
                premium=1.50,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.25,
                greeks=Greeks(delta=-0.25, gamma=0.05, theta=0.15, vega=0.15, rho=-0.05)
            ),
            OptionLeg(
                option_type=OptionType.CALL,
                position_type=PositionType.SHORT,
                strike=short_call_strike,
                expiration=expiration,
                quantity=quantity,
                premium=1.50,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.25,
                greeks=Greeks(delta=0.25, gamma=0.05, theta=0.15, vega=0.15, rho=0.05)
            ),
            OptionLeg(
                option_type=OptionType.CALL,
                position_type=PositionType.LONG,
                strike=long_call_strike,
                expiration=expiration,
                quantity=quantity,
                premium=0.50,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.25,
                greeks=Greeks(delta=0.10, gamma=0.02, theta=0.05, vega=0.08, rho=0.02)
            )
        ]
        
        for leg in legs:
            strategy.add_leg(leg)
        
        strategy.notes = "Iron Condor: Profits from low volatility and sideways movement."
        return strategy
    
    @staticmethod
    def create_butterfly(
        underlying_symbol: str,
        current_price: float,
        expiration: date,
        wing_width: float = 5.0,
        quantity: int = 1,
        option_type: OptionType = OptionType.CALL
    ) -> OptionsStrategy:
        """
        Create a Butterfly spread strategy.
        
        Structure:
        - Buy 1 ITM option
        - Sell 2 ATM options
        - Buy 1 OTM option
        """
        strategy = OptionsStrategy(
            name=f"Butterfly - {underlying_symbol}",
            strategy_type=StrategyType.BUTTERFLY,
            underlying_symbol=underlying_symbol
        )
        
        # Calculate strikes
        lower_strike = current_price - wing_width
        middle_strike = current_price
        upper_strike = current_price + wing_width
        
        # Create legs
        legs = [
            OptionLeg(
                option_type=option_type,
                position_type=PositionType.LONG,
                strike=lower_strike,
                expiration=expiration,
                quantity=quantity,
                premium=6.00 if option_type == OptionType.CALL else 3.00,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.25,
                greeks=Greeks(delta=0.70 if option_type == OptionType.CALL else -0.30,
                            gamma=0.03, theta=0.10, vega=0.12, rho=0.08)
            ),
            OptionLeg(
                option_type=option_type,
                position_type=PositionType.SHORT,
                strike=middle_strike,
                expiration=expiration,
                quantity=quantity * 2,
                premium=3.50 if option_type == OptionType.CALL else 3.50,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.25,
                greeks=Greeks(delta=0.50 if option_type == OptionType.CALL else -0.50,
                            gamma=0.06, theta=0.20, vega=0.18, rho=0.10)
            ),
            OptionLeg(
                option_type=option_type,
                position_type=PositionType.LONG,
                strike=upper_strike,
                expiration=expiration,
                quantity=quantity,
                premium=2.00 if option_type == OptionType.CALL else 6.00,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.25,
                greeks=Greeks(delta=0.30 if option_type == OptionType.CALL else -0.70,
                            gamma=0.03, theta=0.10, vega=0.12, rho=0.08)
            )
        ]
        
        for leg in legs:
            strategy.add_leg(leg)
        
        strategy.notes = "Butterfly: Profits from minimal price movement around the middle strike."
        return strategy
    
    @staticmethod
    def create_straddle(
        underlying_symbol: str,
        strike: float,
        expiration: date,
        quantity: int = 1,
        position_type: PositionType = PositionType.LONG
    ) -> OptionsStrategy:
        """
        Create a Straddle strategy.
        
        Structure:
        - Buy/Sell Call at strike
        - Buy/Sell Put at same strike
        """
        strategy = OptionsStrategy(
            name=f"{'Long' if position_type == PositionType.LONG else 'Short'} Straddle - {underlying_symbol}",
            strategy_type=StrategyType.STRADDLE,
            underlying_symbol=underlying_symbol
        )
        
        # Create legs
        legs = [
            OptionLeg(
                option_type=OptionType.CALL,
                position_type=position_type,
                strike=strike,
                expiration=expiration,
                quantity=quantity,
                premium=4.00,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.30,
                greeks=Greeks(delta=0.50, gamma=0.06, theta=0.20, vega=0.20, rho=0.12)
            ),
            OptionLeg(
                option_type=OptionType.PUT,
                position_type=position_type,
                strike=strike,
                expiration=expiration,
                quantity=quantity,
                premium=4.00,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.30,
                greeks=Greeks(delta=-0.50, gamma=0.06, theta=0.20, vega=0.20, rho=-0.12)
            )
        ]
        
        for leg in legs:
            strategy.add_leg(leg)
        
        if position_type == PositionType.LONG:
            strategy.notes = "Long Straddle: Profits from large price movements in either direction."
        else:
            strategy.notes = "Short Straddle: Profits from minimal price movement."
        
        return strategy
    
    @staticmethod
    def create_strangle(
        underlying_symbol: str,
        current_price: float,
        expiration: date,
        strike_distance: float = 5.0,
        quantity: int = 1,
        position_type: PositionType = PositionType.LONG
    ) -> OptionsStrategy:
        """
        Create a Strangle strategy.
        
        Structure:
        - Buy/Sell OTM Put
        - Buy/Sell OTM Call
        """
        strategy = OptionsStrategy(
            name=f"{'Long' if position_type == PositionType.LONG else 'Short'} Strangle - {underlying_symbol}",
            strategy_type=StrategyType.STRANGLE,
            underlying_symbol=underlying_symbol
        )
        
        put_strike = current_price - strike_distance
        call_strike = current_price + strike_distance
        
        # Create legs
        legs = [
            OptionLeg(
                option_type=OptionType.PUT,
                position_type=position_type,
                strike=put_strike,
                expiration=expiration,
                quantity=quantity,
                premium=2.50,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.28,
                greeks=Greeks(delta=-0.35, gamma=0.04, theta=0.15, vega=0.16, rho=-0.08)
            ),
            OptionLeg(
                option_type=OptionType.CALL,
                position_type=position_type,
                strike=call_strike,
                expiration=expiration,
                quantity=quantity,
                premium=2.50,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.28,
                greeks=Greeks(delta=0.35, gamma=0.04, theta=0.15, vega=0.16, rho=0.08)
            )
        ]
        
        for leg in legs:
            strategy.add_leg(leg)
        
        if position_type == PositionType.LONG:
            strategy.notes = "Long Strangle: Profits from large price movements with lower cost than straddle."
        else:
            strategy.notes = "Short Strangle: Profits from price staying between strikes."
        
        return strategy
    
    @staticmethod
    def create_vertical_spread(
        underlying_symbol: str,
        current_price: float,
        expiration: date,
        spread_width: float = 5.0,
        quantity: int = 1,
        option_type: OptionType = OptionType.CALL,
        is_debit: bool = True
    ) -> OptionsStrategy:
        """
        Create a Vertical Spread strategy.
        
        Debit spread (Bull Call or Bear Put):
        - Buy ITM/ATM option
        - Sell OTM option
        
        Credit spread (Bear Call or Bull Put):
        - Sell ITM/ATM option
        - Buy OTM option
        """
        if is_debit and option_type == OptionType.CALL:
            name = "Bull Call Spread"
        elif is_debit and option_type == OptionType.PUT:
            name = "Bear Put Spread"
        elif not is_debit and option_type == OptionType.CALL:
            name = "Bear Call Spread"
        else:
            name = "Bull Put Spread"
        
        strategy = OptionsStrategy(
            name=f"{name} - {underlying_symbol}",
            strategy_type=StrategyType.VERTICAL_SPREAD,
            underlying_symbol=underlying_symbol
        )
        
        if is_debit:
            long_strike = current_price if option_type == OptionType.CALL else current_price + spread_width
            short_strike = current_price + spread_width if option_type == OptionType.CALL else current_price
            long_premium = 5.00 if option_type == OptionType.CALL else 5.00
            short_premium = 2.50 if option_type == OptionType.CALL else 2.50
        else:
            short_strike = current_price if option_type == OptionType.CALL else current_price - spread_width
            long_strike = current_price + spread_width if option_type == OptionType.CALL else current_price
            short_premium = 5.00 if option_type == OptionType.CALL else 5.00
            long_premium = 2.50 if option_type == OptionType.CALL else 2.50
        
        # Create legs
        legs = [
            OptionLeg(
                option_type=option_type,
                position_type=PositionType.LONG,
                strike=long_strike,
                expiration=expiration,
                quantity=quantity,
                premium=long_premium,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.26,
                greeks=Greeks(delta=0.60 if option_type == OptionType.CALL else -0.60,
                            gamma=0.05, theta=0.18, vega=0.17, rho=0.10)
            ),
            OptionLeg(
                option_type=option_type,
                position_type=PositionType.SHORT,
                strike=short_strike,
                expiration=expiration,
                quantity=quantity,
                premium=short_premium,
                underlying_symbol=underlying_symbol,
                implied_volatility=0.26,
                greeks=Greeks(delta=0.40 if option_type == OptionType.CALL else -0.40,
                            gamma=0.04, theta=0.15, vega=0.14, rho=0.08)
            )
        ]
        
        for leg in legs:
            strategy.add_leg(leg)
        
        strategy.notes = f"{name}: Limited risk, limited reward directional strategy."
        return strategy
    
    @staticmethod
    def create_covered_call(
        underlying_symbol: str,
        current_price: float,
        expiration: date,
        call_strike: float,
        quantity: int = 1,
        stock_quantity: int = 100
    ) -> OptionsStrategy:
        """
        Create a Covered Call strategy.
        
        Structure:
        - Own 100 shares of stock per contract
        - Sell OTM Call
        
        Note: This implementation focuses on the option leg.
        """
        strategy = OptionsStrategy(
            name=f"Covered Call - {underlying_symbol}",
            strategy_type=StrategyType.COVERED_CALL,
            underlying_symbol=underlying_symbol
        )
        
        # Create call leg
        call_leg = OptionLeg(
            option_type=OptionType.CALL,
            position_type=PositionType.SHORT,
            strike=call_strike,
            expiration=expiration,
            quantity=quantity,
            premium=2.00,
            underlying_symbol=underlying_symbol,
            implied_volatility=0.24,
            greeks=Greeks(delta=0.30, gamma=0.04, theta=0.18, vega=0.13, rho=0.06)
        )
        
        strategy.add_leg(call_leg)
        strategy.notes = f"Covered Call: Assumes ownership of {stock_quantity} shares. Generates income while capping upside."
        
        return strategy
    
    @staticmethod
    def create_protective_put(
        underlying_symbol: str,
        current_price: float,
        expiration: date,
        put_strike: float,
        quantity: int = 1,
        stock_quantity: int = 100
    ) -> OptionsStrategy:
        """
        Create a Protective Put strategy.
        
        Structure:
        - Own 100 shares of stock per contract
        - Buy OTM Put for protection
        
        Note: This implementation focuses on the option leg.
        """
        strategy = OptionsStrategy(
            name=f"Protective Put - {underlying_symbol}",
            strategy_type=StrategyType.PROTECTIVE_PUT,
            underlying_symbol=underlying_symbol
        )
        
        # Create put leg
        put_leg = OptionLeg(
            option_type=OptionType.PUT,
            position_type=PositionType.LONG,
            strike=put_strike,
            expiration=expiration,
            quantity=quantity,
            premium=2.50,
            underlying_symbol=underlying_symbol,
            implied_volatility=0.27,
            greeks=Greeks(delta=-0.35, gamma=0.04, theta=0.12, vega=0.14, rho=-0.07)
        )
        
        strategy.add_leg(put_leg)
        strategy.notes = f"Protective Put: Assumes ownership of {stock_quantity} shares. Provides downside protection."
        
        return strategy
