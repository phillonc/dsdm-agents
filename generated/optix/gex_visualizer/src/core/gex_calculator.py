"""Gamma Exposure (GEX) Calculator."""
import numpy as np
from typing import List, Dict, Tuple
from decimal import Decimal
from datetime import datetime, date
from scipy.stats import norm

from src.models.schemas import (
    OptionContract,
    GammaExposure,
    GEXHeatmap,
)
from config.settings import settings


class GEXCalculator:
    """
    Calculate Gamma Exposure (GEX) for options.
    
    GEX represents the amount of gamma exposure that market makers have,
    which influences their hedging behavior and market dynamics.
    """
    
    def __init__(self) -> None:
        """Initialize GEX calculator."""
        self.spot_price_notional = 100  # Multiplier for index options
        
    def calculate_gamma(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float,
        option_type: str
    ) -> float:
        """
        Calculate option gamma using Black-Scholes formula.
        
        Args:
            spot: Current spot price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            volatility: Implied volatility
            risk_free_rate: Risk-free interest rate
            option_type: 'call' or 'put'
            
        Returns:
            Gamma value
        """
        if time_to_expiry <= 0:
            return 0.0
            
        if volatility <= 0:
            volatility = 0.01  # Minimum volatility
            
        d1 = (
            np.log(spot / strike) +
            (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry
        ) / (volatility * np.sqrt(time_to_expiry))
        
        gamma = norm.pdf(d1) / (spot * volatility * np.sqrt(time_to_expiry))
        
        return gamma
    
    def calculate_time_to_expiry(self, expiration: date) -> float:
        """
        Calculate time to expiration in years.
        
        Args:
            expiration: Expiration date
            
        Returns:
            Time to expiry in years
        """
        today = date.today()
        days_to_expiry = (expiration - today).days
        
        if days_to_expiry < 0:
            return 0.0
            
        return days_to_expiry / settings.trading_days_per_year
    
    def calculate_gex_for_strike(
        self,
        call_contract: OptionContract | None,
        put_contract: OptionContract | None,
        spot_price: Decimal
    ) -> GammaExposure:
        """
        Calculate GEX for a specific strike.
        
        Args:
            call_contract: Call option contract (if exists)
            put_contract: Put option contract (if exists)
            spot_price: Current spot price
            
        Returns:
            GammaExposure object
        """
        spot = float(spot_price)
        
        # Initialize values
        strike = None
        call_gamma = 0.0
        put_gamma = 0.0
        call_gex = 0.0
        put_gex = 0.0
        call_oi = 0
        put_oi = 0
        
        # Calculate call GEX
        if call_contract:
            strike = call_contract.strike
            call_oi = call_contract.open_interest
            
            if call_contract.gamma:
                call_gamma = call_contract.gamma
            else:
                # Calculate gamma if not provided
                tte = self.calculate_time_to_expiry(call_contract.expiration)
                iv = call_contract.implied_volatility or 0.3  # Default 30%
                call_gamma = self.calculate_gamma(
                    spot=spot,
                    strike=float(call_contract.strike),
                    time_to_expiry=tte,
                    volatility=iv,
                    risk_free_rate=settings.risk_free_rate,
                    option_type="call"
                )
            
            # GEX = Gamma * Open Interest * Spot^2 * 0.01
            # Market makers are short calls, so positive gamma for them means negative for market
            call_gex = call_gamma * call_oi * spot * spot * 0.01
        
        # Calculate put GEX
        if put_contract:
            strike = put_contract.strike
            put_oi = put_contract.open_interest
            
            if put_contract.gamma:
                put_gamma = put_contract.gamma
            else:
                # Calculate gamma if not provided
                tte = self.calculate_time_to_expiry(put_contract.expiration)
                iv = put_contract.implied_volatility or 0.3  # Default 30%
                put_gamma = self.calculate_gamma(
                    spot=spot,
                    strike=float(put_contract.strike),
                    time_to_expiry=tte,
                    volatility=iv,
                    risk_free_rate=settings.risk_free_rate,
                    option_type="put"
                )
            
            # GEX = Gamma * Open Interest * Spot^2 * 0.01
            # Market makers are long puts, so negative gamma exposure
            put_gex = -1 * put_gamma * put_oi * spot * spot * 0.01
        
        if strike is None:
            raise ValueError("Either call or put contract must be provided")
        
        net_gex = call_gex + put_gex
        
        return GammaExposure(
            strike=strike,
            call_gamma=call_gamma,
            put_gamma=put_gamma,
            net_gamma=call_gamma - put_gamma,
            call_gex=call_gex,
            put_gex=put_gex,
            net_gex=net_gex,
            call_open_interest=call_oi,
            put_open_interest=put_oi
        )
    
    def calculate_gex_for_chain(
        self,
        options_chain: List[OptionContract],
        spot_price: Decimal
    ) -> List[GammaExposure]:
        """
        Calculate GEX for entire options chain.
        
        Args:
            options_chain: List of option contracts
            spot_price: Current spot price
            
        Returns:
            List of GammaExposure objects by strike
        """
        # Group options by strike
        strikes_dict: Dict[Decimal, Dict[str, OptionContract]] = {}
        
        for contract in options_chain:
            if contract.strike not in strikes_dict:
                strikes_dict[contract.strike] = {}
            
            strikes_dict[contract.strike][contract.option_type] = contract
        
        # Calculate GEX for each strike
        gex_results = []
        
        for strike in sorted(strikes_dict.keys()):
            contracts = strikes_dict[strike]
            call_contract = contracts.get("call")
            put_contract = contracts.get("put")
            
            gex = self.calculate_gex_for_strike(
                call_contract=call_contract,
                put_contract=put_contract,
                spot_price=spot_price
            )
            
            gex_results.append(gex)
        
        return gex_results
    
    def create_heatmap(
        self,
        symbol: str,
        spot_price: Decimal,
        gamma_exposures: List[GammaExposure]
    ) -> GEXHeatmap:
        """
        Create GEX heatmap visualization data.
        
        Args:
            symbol: Underlying symbol
            spot_price: Current spot price
            gamma_exposures: List of gamma exposures by strike
            
        Returns:
            GEXHeatmap object
        """
        strikes = [gex.strike for gex in gamma_exposures]
        gex_values = [gex.net_gex for gex in gamma_exposures]
        colors = [gex.color_code for gex in gamma_exposures]
        
        total_call_gex = sum(gex.call_gex for gex in gamma_exposures)
        total_put_gex = sum(gex.put_gex for gex in gamma_exposures)
        total_net_gex = sum(gex.net_gex for gex in gamma_exposures)
        
        # Find max and min GEX strikes
        max_gex_strike = max(gamma_exposures, key=lambda x: abs(x.net_gex)).strike
        min_gex_strike = min(gamma_exposures, key=lambda x: abs(x.net_gex)).strike
        
        return GEXHeatmap(
            symbol=symbol,
            spot_price=spot_price,
            timestamp=datetime.utcnow(),
            strikes=strikes,
            gex_values=gex_values,
            colors=colors,
            total_call_gex=total_call_gex,
            total_put_gex=total_put_gex,
            total_net_gex=total_net_gex,
            max_gex_strike=max_gex_strike,
            min_gex_strike=min_gex_strike
        )
