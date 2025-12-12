"""
Template builder for creating predefined strategy templates
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from ..models.option import Option, OptionType, OptionPosition
from ..models.strategy import Strategy, StrategyTemplate


class TemplateBuilder:
    """
    Builder for creating predefined options strategy templates
    """
    
    @staticmethod
    def create_iron_condor(
        underlying_symbol: str,
        underlying_price: Decimal,
        expiration_date: datetime,
        put_short_strike: Decimal,
        put_long_strike: Decimal,
        call_short_strike: Decimal,
        call_long_strike: Decimal,
        quantity: int = 1,
        implied_volatility: Decimal = Decimal('0.25')
    ) -> Strategy:
        """
        Create an Iron Condor strategy
        
        Sell OTM put, buy farther OTM put, sell OTM call, buy farther OTM call
        """
        strategy = Strategy(
            name=f"Iron Condor - {underlying_symbol}",
            template=StrategyTemplate.IRON_CONDOR,
            description="Neutral strategy that profits from low volatility"
        )
        
        # Short Put
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}P{put_short_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.PUT,
            strike_price=put_short_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.SHORT,
            premium=Decimal('2.50'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Short Put")
        
        # Long Put
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}P{put_long_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.PUT,
            strike_price=put_long_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.LONG,
            premium=Decimal('1.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Long Put")
        
        # Short Call
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}C{call_short_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.CALL,
            strike_price=call_short_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.SHORT,
            premium=Decimal('2.50'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Short Call")
        
        # Long Call
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}C{call_long_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.CALL,
            strike_price=call_long_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.LONG,
            premium=Decimal('1.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Long Call")
        
        return strategy
    
    @staticmethod
    def create_butterfly(
        underlying_symbol: str,
        underlying_price: Decimal,
        expiration_date: datetime,
        lower_strike: Decimal,
        middle_strike: Decimal,
        upper_strike: Decimal,
        option_type: OptionType = OptionType.CALL,
        quantity: int = 1,
        implied_volatility: Decimal = Decimal('0.25')
    ) -> Strategy:
        """
        Create a Butterfly spread strategy
        
        Buy 1 ITM, sell 2 ATM, buy 1 OTM
        """
        strategy = Strategy(
            name=f"Butterfly - {underlying_symbol}",
            template=StrategyTemplate.BUTTERFLY,
            description="Neutral strategy for minimal movement"
        )
        
        # Long lower strike
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}{option_type.value[0]}{lower_strike}",
            underlying_symbol=underlying_symbol,
            option_type=option_type,
            strike_price=lower_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.LONG,
            premium=Decimal('5.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Long Lower Strike")
        
        # Short 2x middle strike
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}{option_type.value[0]}{middle_strike}",
            underlying_symbol=underlying_symbol,
            option_type=option_type,
            strike_price=middle_strike,
            expiration_date=expiration_date,
            quantity=quantity * 2,
            position=OptionPosition.SHORT,
            premium=Decimal('3.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Short 2x Middle Strike")
        
        # Long upper strike
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}{option_type.value[0]}{upper_strike}",
            underlying_symbol=underlying_symbol,
            option_type=option_type,
            strike_price=upper_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.LONG,
            premium=Decimal('1.50'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Long Upper Strike")
        
        return strategy
    
    @staticmethod
    def create_straddle(
        underlying_symbol: str,
        underlying_price: Decimal,
        expiration_date: datetime,
        strike_price: Decimal,
        position: OptionPosition = OptionPosition.LONG,
        quantity: int = 1,
        implied_volatility: Decimal = Decimal('0.25')
    ) -> Strategy:
        """
        Create a Straddle strategy
        
        Buy/sell both call and put at the same strike
        """
        strategy = Strategy(
            name=f"{'Long' if position == OptionPosition.LONG else 'Short'} Straddle - {underlying_symbol}",
            template=StrategyTemplate.STRADDLE,
            description="Volatility strategy for large movement in either direction"
        )
        
        # Call
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}C{strike_price}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.CALL,
            strike_price=strike_price,
            expiration_date=expiration_date,
            quantity=quantity,
            position=position,
            premium=Decimal('3.50'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Call Leg")
        
        # Put
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}P{strike_price}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.PUT,
            strike_price=strike_price,
            expiration_date=expiration_date,
            quantity=quantity,
            position=position,
            premium=Decimal('3.50'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Put Leg")
        
        return strategy
    
    @staticmethod
    def create_strangle(
        underlying_symbol: str,
        underlying_price: Decimal,
        expiration_date: datetime,
        put_strike: Decimal,
        call_strike: Decimal,
        position: OptionPosition = OptionPosition.LONG,
        quantity: int = 1,
        implied_volatility: Decimal = Decimal('0.25')
    ) -> Strategy:
        """
        Create a Strangle strategy
        
        Buy/sell OTM call and OTM put
        """
        strategy = Strategy(
            name=f"{'Long' if position == OptionPosition.LONG else 'Short'} Strangle - {underlying_symbol}",
            template=StrategyTemplate.STRANGLE,
            description="Volatility strategy with lower cost than straddle"
        )
        
        # Call
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}C{call_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.CALL,
            strike_price=call_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=position,
            premium=Decimal('2.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Call Leg")
        
        # Put
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}P{put_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.PUT,
            strike_price=put_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=position,
            premium=Decimal('2.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Put Leg")
        
        return strategy
    
    @staticmethod
    def create_bull_call_spread(
        underlying_symbol: str,
        underlying_price: Decimal,
        expiration_date: datetime,
        long_strike: Decimal,
        short_strike: Decimal,
        quantity: int = 1,
        implied_volatility: Decimal = Decimal('0.25')
    ) -> Strategy:
        """
        Create a Bull Call Spread strategy
        
        Buy lower strike call, sell higher strike call
        """
        strategy = Strategy(
            name=f"Bull Call Spread - {underlying_symbol}",
            template=StrategyTemplate.BULL_CALL_SPREAD,
            description="Bullish strategy with limited risk and reward"
        )
        
        # Long Call (lower strike)
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}C{long_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.CALL,
            strike_price=long_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.LONG,
            premium=Decimal('4.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Long Call")
        
        # Short Call (higher strike)
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}C{short_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.CALL,
            strike_price=short_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.SHORT,
            premium=Decimal('2.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Short Call")
        
        return strategy
    
    @staticmethod
    def create_bear_put_spread(
        underlying_symbol: str,
        underlying_price: Decimal,
        expiration_date: datetime,
        long_strike: Decimal,
        short_strike: Decimal,
        quantity: int = 1,
        implied_volatility: Decimal = Decimal('0.25')
    ) -> Strategy:
        """
        Create a Bear Put Spread strategy
        
        Buy higher strike put, sell lower strike put
        """
        strategy = Strategy(
            name=f"Bear Put Spread - {underlying_symbol}",
            template=StrategyTemplate.BEAR_PUT_SPREAD,
            description="Bearish strategy with limited risk and reward"
        )
        
        # Long Put (higher strike)
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}P{long_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.PUT,
            strike_price=long_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.LONG,
            premium=Decimal('4.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Long Put")
        
        # Short Put (lower strike)
        strategy.add_leg(Option(
            symbol=f"{underlying_symbol}P{short_strike}",
            underlying_symbol=underlying_symbol,
            option_type=OptionType.PUT,
            strike_price=short_strike,
            expiration_date=expiration_date,
            quantity=quantity,
            position=OptionPosition.SHORT,
            premium=Decimal('2.00'),
            underlying_price=underlying_price,
            implied_volatility=implied_volatility
        ), "Short Put")
        
        return strategy
    
    @staticmethod
    def get_template_list() -> dict:
        """
        Get a list of all available templates with descriptions
        
        Returns:
            Dictionary of template names and descriptions
        """
        return {
            'IRON_CONDOR': 'Sell OTM put spread and OTM call spread for credit (neutral)',
            'BUTTERFLY': 'Buy 1 ITM, sell 2 ATM, buy 1 OTM (neutral, low volatility)',
            'STRADDLE': 'Buy/sell both call and put at same strike (volatility play)',
            'STRANGLE': 'Buy/sell OTM call and OTM put (volatility play, lower cost)',
            'BULL_CALL_SPREAD': 'Buy lower strike call, sell higher strike call (bullish)',
            'BEAR_PUT_SPREAD': 'Buy higher strike put, sell lower strike put (bearish)',
            'COVERED_CALL': 'Own stock and sell call (income generation)',
            'PROTECTIVE_PUT': 'Own stock and buy put (downside protection)',
            'COLLAR': 'Covered call + protective put (limited risk and reward)',
            'IRON_BUTTERFLY': 'Similar to iron condor with same short strikes',
            'CALENDAR_SPREAD': 'Buy/sell same strike different expirations',
            'DIAGONAL_SPREAD': 'Different strikes and expirations'
        }
