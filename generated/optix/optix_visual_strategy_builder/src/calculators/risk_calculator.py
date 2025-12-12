"""
Risk analysis calculator for options strategies
"""
from decimal import Decimal
from typing import Dict, List
from datetime import datetime, timedelta

from ..models.strategy import Strategy
from ..models.option import Option
from .pnl_calculator import PnLCalculator
from .greeks_calculator import GreeksCalculator


class RiskCalculator:
    """
    Calculate various risk metrics for options strategies
    """
    
    @staticmethod
    def calculate_value_at_risk(
        strategy: Strategy,
        confidence_level: Decimal = Decimal('0.95'),
        time_horizon_days: int = 1,
        volatility: Decimal = None
    ) -> Dict[str, Decimal]:
        """
        Calculate Value at Risk (VaR) for the strategy
        
        Args:
            strategy: The options strategy
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            time_horizon_days: Time horizon in days
            volatility: Annualized volatility (if None, use from options)
            
        Returns:
            Dictionary with VaR metrics
        """
        # Get current value
        current_value = abs(strategy.total_cost)
        
        # Get volatility from strategy if not provided
        if volatility is None and strategy.legs:
            first_option = strategy.legs[0].option
            if first_option.implied_volatility:
                volatility = first_option.implied_volatility
            else:
                volatility = Decimal('0.20')  # Default 20%
        
        # Calculate daily volatility
        daily_volatility = volatility / Decimal('365').sqrt()
        
        # Z-score for confidence level (1.645 for 95%, 1.96 for 97.5%, 2.33 for 99%)
        z_scores = {
            Decimal('0.90'): Decimal('1.28'),
            Decimal('0.95'): Decimal('1.645'),
            Decimal('0.975'): Decimal('1.96'),
            Decimal('0.99'): Decimal('2.33')
        }
        z_score = z_scores.get(confidence_level, Decimal('1.645'))
        
        # Calculate VaR
        time_factor = Decimal(str(time_horizon_days)).sqrt()
        var = current_value * daily_volatility * z_score * time_factor
        
        return {
            'value_at_risk': var,
            'confidence_level': confidence_level,
            'time_horizon_days': time_horizon_days,
            'current_value': current_value,
            'var_percentage': (var / current_value * Decimal('100')) if current_value > 0 else Decimal('0')
        }
    
    @staticmethod
    def calculate_probability_of_profit(
        strategy: Strategy,
        num_simulations: int = 1000
    ) -> Dict[str, any]:
        """
        Estimate probability of profit at expiration using Monte Carlo simulation
        
        Args:
            strategy: The options strategy
            num_simulations: Number of simulations to run
            
        Returns:
            Dictionary with probability metrics
        """
        import numpy as np
        
        # Get underlying price and volatility
        if not strategy.legs:
            return {'probability_of_profit': Decimal('0')}
        
        first_option = strategy.legs[0].option
        if first_option.underlying_price is None or first_option.implied_volatility is None:
            return {'probability_of_profit': Decimal('0')}
        
        S0 = float(first_option.underlying_price)
        sigma = float(first_option.implied_volatility)
        T = float(first_option.time_to_expiration)
        r = float(first_option.interest_rate)
        
        # Run Monte Carlo simulation
        np.random.seed(42)
        Z = np.random.standard_normal(num_simulations)
        ST = S0 * np.exp((r - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * Z)
        
        # Calculate P&L at each simulated price
        profitable_outcomes = 0
        pnl_values = []
        
        for price in ST:
            pnl = PnLCalculator.calculate_strategy_pnl(
                strategy,
                Decimal(str(price)),
                at_expiration=True
            )
            pnl_values.append(float(pnl))
            if pnl > 0:
                profitable_outcomes += 1
        
        pop = Decimal(str(profitable_outcomes / num_simulations))
        
        return {
            'probability_of_profit': pop,
            'probability_of_profit_pct': pop * Decimal('100'),
            'num_simulations': num_simulations,
            'expected_value': Decimal(str(np.mean(pnl_values))),
            'standard_deviation': Decimal(str(np.std(pnl_values)))
        }
    
    @staticmethod
    def analyze_scenario(
        strategy: Strategy,
        scenario_price: Decimal,
        scenario_date: datetime = None,
        volatility_change: Decimal = Decimal('0')
    ) -> Dict[str, any]:
        """
        Analyze what-if scenario for the strategy
        
        Args:
            strategy: The options strategy
            scenario_price: Underlying price in the scenario
            scenario_date: Date for the scenario (if None, use current date)
            volatility_change: Change in implied volatility (e.g., 0.05 for +5%)
            
        Returns:
            Dictionary with scenario analysis results
        """
        if scenario_date is None:
            scenario_date = datetime.utcnow()
        
        # Calculate current P&L
        current_pnl = PnLCalculator.calculate_strategy_pnl(
            strategy, scenario_price, at_expiration=False
        )
        
        # Calculate P&L at expiration
        expiration_pnl = PnLCalculator.calculate_strategy_pnl(
            strategy, scenario_price, at_expiration=True
        )
        
        # Calculate Greeks at scenario price
        # Update option prices for scenario
        for leg in strategy.legs:
            leg.option.underlying_price = scenario_price
            if volatility_change != 0:
                leg.option.implied_volatility += volatility_change
        
        greeks = GreeksCalculator.calculate_strategy_greeks(strategy)
        
        # Calculate time decay impact
        days_passed = (scenario_date - datetime.utcnow()).days
        theta_impact = greeks.total_theta * Decimal(str(days_passed))
        
        return {
            'scenario_price': scenario_price,
            'scenario_date': scenario_date.isoformat(),
            'current_pnl': current_pnl,
            'expiration_pnl': expiration_pnl,
            'greeks': greeks.to_dict(),
            'theta_impact': theta_impact,
            'volatility_change': volatility_change,
            'days_passed': days_passed
        }
    
    @staticmethod
    def calculate_margin_requirement(strategy: Strategy) -> Dict[str, Decimal]:
        """
        Estimate margin requirement for the strategy
        
        Note: This is a simplified calculation. Actual margin requirements
        vary by broker and account type.
        
        Returns:
            Dictionary with margin estimates
        """
        total_margin = Decimal('0')
        naked_options = []
        spread_credits = Decimal('0')
        
        for leg in strategy.legs:
            option = leg.option
            
            if option.position.value == 'SHORT':
                # Short options require margin
                if option.underlying_price:
                    # Simplified margin: 20% of underlying + option premium - OTM amount
                    base_margin = option.underlying_price * Decimal('0.20') * option.quantity * Decimal('100')
                    premium_collected = abs(option.total_premium)
                    otm_amount = max(Decimal('0'), 
                                    option.strike_price - option.underlying_price 
                                    if option.option_type.value == 'PUT' 
                                    else option.underlying_price - option.strike_price)
                    otm_reduction = otm_amount * option.quantity * Decimal('100')
                    
                    leg_margin = max(base_margin + premium_collected - otm_reduction, 
                                    premium_collected)
                    total_margin += leg_margin
                    naked_options.append(leg.leg_id)
        
        # Check for spreads (which may reduce margin)
        # This is simplified - real calculation would detect vertical spreads, etc.
        if strategy.is_credit_strategy:
            spread_credits = abs(strategy.total_cost)
        
        return {
            'estimated_margin': total_margin,
            'strategy_cost': strategy.total_cost,
            'total_capital_required': total_margin + abs(min(strategy.total_cost, Decimal('0'))),
            'has_naked_options': len(naked_options) > 0,
            'naked_option_legs': naked_options,
            'notes': 'Simplified margin calculation. Consult broker for actual requirements.'
        }
    
    @staticmethod
    def calculate_risk_metrics(strategy: Strategy) -> Dict[str, any]:
        """
        Calculate comprehensive risk metrics for the strategy
        
        Returns:
            Dictionary with all risk metrics
        """
        risk_reward = PnLCalculator.calculate_risk_reward_ratio(strategy)
        var_metrics = RiskCalculator.calculate_value_at_risk(strategy)
        pop_metrics = RiskCalculator.calculate_probability_of_profit(strategy)
        margin = RiskCalculator.calculate_margin_requirement(strategy)
        greeks = GreeksCalculator.calculate_strategy_greeks(strategy)
        
        return {
            'risk_reward': {k: float(v) if isinstance(v, Decimal) else v 
                          for k, v in risk_reward.items()},
            'value_at_risk': {k: float(v) if isinstance(v, Decimal) else v 
                            for k, v in var_metrics.items()},
            'probability_metrics': {k: float(v) if isinstance(v, Decimal) else v 
                                  for k, v in pop_metrics.items()},
            'margin_requirement': {k: float(v) if isinstance(v, Decimal) else v 
                                 for k, v in margin.items() if k != 'naked_option_legs'},
            'greeks': greeks.to_dict()
        }
