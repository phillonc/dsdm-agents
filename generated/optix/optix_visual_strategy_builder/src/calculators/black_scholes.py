"""
Black-Scholes option pricing model implementation
"""
import math
from decimal import Decimal
from typing import Tuple
from scipy import stats

from ..models.option import Option, OptionType


class BlackScholesCalculator:
    """
    Implements the Black-Scholes option pricing model
    """
    
    @staticmethod
    def calculate_option_price(
        spot_price: Decimal,
        strike_price: Decimal,
        time_to_expiration: Decimal,
        risk_free_rate: Decimal,
        volatility: Decimal,
        option_type: OptionType,
        dividend_yield: Decimal = Decimal('0')
    ) -> Decimal:
        """
        Calculate option price using Black-Scholes model
        
        Args:
            spot_price: Current price of underlying
            strike_price: Strike price of option
            time_to_expiration: Time to expiration in years
            risk_free_rate: Risk-free interest rate
            volatility: Implied volatility
            option_type: CALL or PUT
            dividend_yield: Dividend yield
            
        Returns:
            Option price
        """
        if time_to_expiration <= 0:
            # Option has expired, return intrinsic value
            if option_type == OptionType.CALL:
                return max(Decimal('0'), spot_price - strike_price)
            else:
                return max(Decimal('0'), strike_price - spot_price)
        
        # Convert to float for calculations
        S = float(spot_price)
        K = float(strike_price)
        T = float(time_to_expiration)
        r = float(risk_free_rate)
        sigma = float(volatility)
        q = float(dividend_yield)
        
        # Calculate d1 and d2
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        # Calculate option price
        if option_type == OptionType.CALL:
            price = (S * math.exp(-q * T) * stats.norm.cdf(d1) - 
                    K * math.exp(-r * T) * stats.norm.cdf(d2))
        else:  # PUT
            price = (K * math.exp(-r * T) * stats.norm.cdf(-d2) - 
                    S * math.exp(-q * T) * stats.norm.cdf(-d1))
        
        return Decimal(str(max(0, price)))
    
    @staticmethod
    def calculate_d1_d2(
        spot_price: Decimal,
        strike_price: Decimal,
        time_to_expiration: Decimal,
        risk_free_rate: Decimal,
        volatility: Decimal,
        dividend_yield: Decimal = Decimal('0')
    ) -> Tuple[float, float]:
        """
        Calculate d1 and d2 values for Black-Scholes
        """
        if time_to_expiration <= 0:
            return 0.0, 0.0
        
        S = float(spot_price)
        K = float(strike_price)
        T = float(time_to_expiration)
        r = float(risk_free_rate)
        sigma = float(volatility)
        q = float(dividend_yield)
        
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        return d1, d2
    
    @staticmethod
    def calculate_implied_volatility(
        option_price: Decimal,
        spot_price: Decimal,
        strike_price: Decimal,
        time_to_expiration: Decimal,
        risk_free_rate: Decimal,
        option_type: OptionType,
        dividend_yield: Decimal = Decimal('0'),
        max_iterations: int = 100,
        tolerance: Decimal = Decimal('0.0001')
    ) -> Decimal:
        """
        Calculate implied volatility using Newton-Raphson method
        
        Returns:
            Implied volatility
        """
        if time_to_expiration <= 0:
            return Decimal('0')
        
        # Initial guess
        volatility = Decimal('0.3')
        
        for _ in range(max_iterations):
            # Calculate price with current volatility
            calculated_price = BlackScholesCalculator.calculate_option_price(
                spot_price, strike_price, time_to_expiration,
                risk_free_rate, volatility, option_type, dividend_yield
            )
            
            # Calculate vega
            d1, _ = BlackScholesCalculator.calculate_d1_d2(
                spot_price, strike_price, time_to_expiration,
                risk_free_rate, volatility, dividend_yield
            )
            
            vega = (float(spot_price) * stats.norm.pdf(d1) * 
                   math.sqrt(float(time_to_expiration)) * math.exp(-float(dividend_yield) * float(time_to_expiration)))
            
            # Check convergence
            price_diff = calculated_price - option_price
            if abs(price_diff) < tolerance:
                return volatility
            
            # Update volatility using Newton-Raphson
            if vega > 0:
                volatility -= Decimal(str(float(price_diff) / vega))
                volatility = max(Decimal('0.01'), min(Decimal('5.0'), volatility))
        
        # Return last calculated volatility if not converged
        return volatility
    
    @classmethod
    def price_option(cls, option: Option) -> Decimal:
        """
        Price an option using its attributes
        """
        if option.underlying_price is None:
            raise ValueError("Underlying price required for pricing")
        
        if option.implied_volatility is None:
            raise ValueError("Implied volatility required for pricing")
        
        return cls.calculate_option_price(
            spot_price=option.underlying_price,
            strike_price=option.strike_price,
            time_to_expiration=option.time_to_expiration,
            risk_free_rate=option.interest_rate,
            volatility=option.implied_volatility,
            option_type=option.option_type,
            dividend_yield=option.dividend_yield
        )
