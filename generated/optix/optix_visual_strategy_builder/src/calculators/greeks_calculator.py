"""
Greeks calculator for options
"""
import math
from decimal import Decimal
from typing import List
from scipy import stats

from ..models.option import Option, OptionType, OptionPosition
from ..models.greeks import Greeks, AggregatedGreeks
from ..models.strategy import Strategy
from .black_scholes import BlackScholesCalculator


class GreeksCalculator:
    """
    Calculate Greeks (Delta, Gamma, Theta, Vega, Rho) for options
    """
    
    @staticmethod
    def calculate_delta(
        spot_price: Decimal,
        strike_price: Decimal,
        time_to_expiration: Decimal,
        risk_free_rate: Decimal,
        volatility: Decimal,
        option_type: OptionType,
        dividend_yield: Decimal = Decimal('0')
    ) -> Decimal:
        """
        Calculate Delta - rate of change of option price with respect to underlying price
        """
        if time_to_expiration <= 0:
            # At expiration
            if option_type == OptionType.CALL:
                return Decimal('1') if spot_price > strike_price else Decimal('0')
            else:
                return Decimal('-1') if spot_price < strike_price else Decimal('0')
        
        d1, _ = BlackScholesCalculator.calculate_d1_d2(
            spot_price, strike_price, time_to_expiration,
            risk_free_rate, volatility, dividend_yield
        )
        
        q = float(dividend_yield)
        T = float(time_to_expiration)
        
        if option_type == OptionType.CALL:
            delta = math.exp(-q * T) * stats.norm.cdf(d1)
        else:  # PUT
            delta = math.exp(-q * T) * (stats.norm.cdf(d1) - 1)
        
        return Decimal(str(delta))
    
    @staticmethod
    def calculate_gamma(
        spot_price: Decimal,
        strike_price: Decimal,
        time_to_expiration: Decimal,
        risk_free_rate: Decimal,
        volatility: Decimal,
        dividend_yield: Decimal = Decimal('0')
    ) -> Decimal:
        """
        Calculate Gamma - rate of change of Delta with respect to underlying price
        """
        if time_to_expiration <= 0:
            return Decimal('0')
        
        d1, _ = BlackScholesCalculator.calculate_d1_d2(
            spot_price, strike_price, time_to_expiration,
            risk_free_rate, volatility, dividend_yield
        )
        
        S = float(spot_price)
        T = float(time_to_expiration)
        sigma = float(volatility)
        q = float(dividend_yield)
        
        gamma = (math.exp(-q * T) * stats.norm.pdf(d1)) / (S * sigma * math.sqrt(T))
        
        return Decimal(str(gamma))
    
    @staticmethod
    def calculate_theta(
        spot_price: Decimal,
        strike_price: Decimal,
        time_to_expiration: Decimal,
        risk_free_rate: Decimal,
        volatility: Decimal,
        option_type: OptionType,
        dividend_yield: Decimal = Decimal('0')
    ) -> Decimal:
        """
        Calculate Theta - rate of change of option price with respect to time (time decay)
        Returns daily theta (divided by 365)
        """
        if time_to_expiration <= 0:
            return Decimal('0')
        
        d1, d2 = BlackScholesCalculator.calculate_d1_d2(
            spot_price, strike_price, time_to_expiration,
            risk_free_rate, volatility, dividend_yield
        )
        
        S = float(spot_price)
        K = float(strike_price)
        T = float(time_to_expiration)
        r = float(risk_free_rate)
        sigma = float(volatility)
        q = float(dividend_yield)
        
        if option_type == OptionType.CALL:
            theta = (-(S * stats.norm.pdf(d1) * sigma * math.exp(-q * T)) / (2 * math.sqrt(T)) - 
                    r * K * math.exp(-r * T) * stats.norm.cdf(d2) + 
                    q * S * math.exp(-q * T) * stats.norm.cdf(d1))
        else:  # PUT
            theta = (-(S * stats.norm.pdf(d1) * sigma * math.exp(-q * T)) / (2 * math.sqrt(T)) + 
                    r * K * math.exp(-r * T) * stats.norm.cdf(-d2) - 
                    q * S * math.exp(-q * T) * stats.norm.cdf(-d1))
        
        # Convert to daily theta
        daily_theta = theta / 365.0
        
        return Decimal(str(daily_theta))
    
    @staticmethod
    def calculate_vega(
        spot_price: Decimal,
        strike_price: Decimal,
        time_to_expiration: Decimal,
        risk_free_rate: Decimal,
        volatility: Decimal,
        dividend_yield: Decimal = Decimal('0')
    ) -> Decimal:
        """
        Calculate Vega - rate of change of option price with respect to volatility
        Returns vega per 1% change in volatility
        """
        if time_to_expiration <= 0:
            return Decimal('0')
        
        d1, _ = BlackScholesCalculator.calculate_d1_d2(
            spot_price, strike_price, time_to_expiration,
            risk_free_rate, volatility, dividend_yield
        )
        
        S = float(spot_price)
        T = float(time_to_expiration)
        q = float(dividend_yield)
        
        vega = S * math.exp(-q * T) * stats.norm.pdf(d1) * math.sqrt(T)
        
        # Vega per 1% change in volatility
        vega = vega / 100.0
        
        return Decimal(str(vega))
    
    @staticmethod
    def calculate_rho(
        spot_price: Decimal,
        strike_price: Decimal,
        time_to_expiration: Decimal,
        risk_free_rate: Decimal,
        volatility: Decimal,
        option_type: OptionType,
        dividend_yield: Decimal = Decimal('0')
    ) -> Decimal:
        """
        Calculate Rho - rate of change of option price with respect to interest rate
        Returns rho per 1% change in interest rate
        """
        if time_to_expiration <= 0:
            return Decimal('0')
        
        _, d2 = BlackScholesCalculator.calculate_d1_d2(
            spot_price, strike_price, time_to_expiration,
            risk_free_rate, volatility, dividend_yield
        )
        
        K = float(strike_price)
        T = float(time_to_expiration)
        r = float(risk_free_rate)
        
        if option_type == OptionType.CALL:
            rho = K * T * math.exp(-r * T) * stats.norm.cdf(d2)
        else:  # PUT
            rho = -K * T * math.exp(-r * T) * stats.norm.cdf(-d2)
        
        # Rho per 1% change in interest rate
        rho = rho / 100.0
        
        return Decimal(str(rho))
    
    @classmethod
    def calculate_option_greeks(cls, option: Option) -> Greeks:
        """
        Calculate all Greeks for an option
        """
        if option.underlying_price is None:
            raise ValueError("Underlying price required for Greeks calculation")
        
        if option.implied_volatility is None:
            raise ValueError("Implied volatility required for Greeks calculation")
        
        delta = cls.calculate_delta(
            option.underlying_price, option.strike_price,
            option.time_to_expiration, option.interest_rate,
            option.implied_volatility, option.option_type,
            option.dividend_yield
        )
        
        gamma = cls.calculate_gamma(
            option.underlying_price, option.strike_price,
            option.time_to_expiration, option.interest_rate,
            option.implied_volatility, option.dividend_yield
        )
        
        theta = cls.calculate_theta(
            option.underlying_price, option.strike_price,
            option.time_to_expiration, option.interest_rate,
            option.implied_volatility, option.option_type,
            option.dividend_yield
        )
        
        vega = cls.calculate_vega(
            option.underlying_price, option.strike_price,
            option.time_to_expiration, option.interest_rate,
            option.implied_volatility, option.dividend_yield
        )
        
        rho = cls.calculate_rho(
            option.underlying_price, option.strike_price,
            option.time_to_expiration, option.interest_rate,
            option.implied_volatility, option.option_type,
            option.dividend_yield
        )
        
        # Adjust for position (short vs long)
        multiplier = Decimal('1') if option.position == OptionPosition.LONG else Decimal('-1')
        
        # Scale by quantity and contract multiplier (100 shares)
        contract_multiplier = Decimal('100') * option.quantity
        
        greeks = Greeks(
            delta=delta * multiplier * contract_multiplier,
            gamma=gamma * multiplier * contract_multiplier,
            theta=theta * multiplier * contract_multiplier,
            vega=vega * multiplier * contract_multiplier,
            rho=rho * multiplier * contract_multiplier
        )
        
        # Update option with calculated Greeks
        option.delta = greeks.delta / contract_multiplier
        option.gamma = greeks.gamma / contract_multiplier
        option.theta = greeks.theta / contract_multiplier
        option.vega = greeks.vega / contract_multiplier
        option.rho = greeks.rho / contract_multiplier
        
        return greeks
    
    @classmethod
    def calculate_strategy_greeks(cls, strategy: Strategy) -> AggregatedGreeks:
        """
        Calculate aggregated Greeks for an entire strategy
        """
        greeks_list: List[Greeks] = []
        
        for leg in strategy.legs:
            option_greeks = cls.calculate_option_greeks(leg.option)
            greeks_list.append(option_greeks)
        
        return AggregatedGreeks.from_greeks_list(greeks_list)
