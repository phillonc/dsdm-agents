"""
What-if scenario analysis for options strategies.

This module provides tools for analyzing how strategies perform under
different market conditions.
"""

from typing import List, Dict, Optional
from datetime import date, timedelta
import copy
from .models import OptionsStrategy, ScenarioAnalysis, Greeks, OptionLeg


class ScenarioEngine:
    """Engine for running what-if scenario analyses."""
    
    @staticmethod
    def analyze_price_change(
        strategy: OptionsStrategy,
        current_price: float,
        price_changes: List[float]
    ) -> List[Dict[str, any]]:
        """
        Analyze strategy performance at different price levels.
        
        Args:
            strategy: The options strategy
            current_price: Current underlying price
            price_changes: List of percentage changes (e.g., [-10, -5, 0, 5, 10])
            
        Returns:
            List of scenario results
        """
        results = []
        
        for change_pct in price_changes:
            new_price = current_price * (1 + change_pct / 100)
            pnl = strategy.calculate_pnl(new_price)
            pnl_change = pnl - strategy.calculate_pnl(current_price)
            
            scenario = {
                'price_change_percent': change_pct,
                'new_price': round(new_price, 2),
                'pnl': round(pnl, 2),
                'pnl_change': round(pnl_change, 2),
                'return_percent': round((pnl / abs(strategy.get_total_cost())) * 100, 2) if strategy.get_total_cost() != 0 else 0
            }
            results.append(scenario)
        
        return results
    
    @staticmethod
    def analyze_volatility_change(
        strategy: OptionsStrategy,
        volatility_changes: List[float]
    ) -> List[Dict[str, any]]:
        """
        Analyze strategy sensitivity to volatility changes.
        
        Args:
            strategy: The options strategy
            volatility_changes: List of percentage changes in IV
            
        Returns:
            List of scenario results
        """
        results = []
        current_vega = strategy.get_aggregated_greeks().vega
        
        for vol_change_pct in volatility_changes:
            # Estimate P&L impact from vega
            # Vega represents P&L change per 1% change in IV
            vol_impact = current_vega * vol_change_pct
            
            scenario = {
                'volatility_change_percent': vol_change_pct,
                'estimated_pnl_impact': round(vol_impact, 2),
                'total_vega': round(current_vega, 4),
                'description': f"{'Increase' if vol_change_pct > 0 else 'Decrease'} in IV by {abs(vol_change_pct)}%"
            }
            results.append(scenario)
        
        return results
    
    @staticmethod
    def analyze_time_decay(
        strategy: OptionsStrategy,
        days_forward: List[int]
    ) -> List[Dict[str, any]]:
        """
        Analyze strategy performance over time (theta decay).
        
        Args:
            strategy: The options strategy
            days_forward: List of days forward to analyze
            
        Returns:
            List of scenario results
        """
        results = []
        current_theta = strategy.get_aggregated_greeks().theta
        
        for days in days_forward:
            # Theta represents P&L change per day
            # Note: This is a simplified linear approximation
            theta_impact = current_theta * days
            
            scenario = {
                'days_forward': days,
                'estimated_pnl_impact': round(theta_impact, 2),
                'total_theta': round(current_theta, 4),
                'description': f"P&L after {days} day{'s' if days != 1 else ''}"
            }
            results.append(scenario)
        
        return results
    
    @staticmethod
    def analyze_combined_scenario(
        strategy: OptionsStrategy,
        current_price: float,
        price_change_pct: float,
        volatility_change_pct: float,
        days_forward: int
    ) -> Dict[str, any]:
        """
        Analyze a combined scenario with multiple factors.
        
        Args:
            strategy: The options strategy
            current_price: Current underlying price
            price_change_pct: Percentage change in price
            volatility_change_pct: Percentage change in IV
            days_forward: Number of days forward
            
        Returns:
            Combined scenario results
        """
        greeks = strategy.get_aggregated_greeks()
        
        # Calculate new price
        new_price = current_price * (1 + price_change_pct / 100)
        
        # Calculate P&L from price change
        price_pnl = strategy.calculate_pnl(new_price)
        
        # Estimate vega impact
        vega_impact = greeks.vega * volatility_change_pct
        
        # Estimate theta impact
        theta_impact = greeks.theta * days_forward
        
        # Combined estimated P&L
        estimated_total_pnl = price_pnl + vega_impact + theta_impact
        
        return {
            'price_change_percent': price_change_pct,
            'new_price': round(new_price, 2),
            'volatility_change_percent': volatility_change_pct,
            'days_forward': days_forward,
            'price_pnl': round(price_pnl, 2),
            'vega_impact': round(vega_impact, 2),
            'theta_impact': round(theta_impact, 2),
            'estimated_total_pnl': round(estimated_total_pnl, 2),
            'greeks_used': greeks.to_dict()
        }
    
    @staticmethod
    def stress_test(
        strategy: OptionsStrategy,
        current_price: float
    ) -> Dict[str, any]:
        """
        Run stress tests on the strategy.
        
        Args:
            strategy: The options strategy
            current_price: Current underlying price
            
        Returns:
            Stress test results
        """
        scenarios = {
            'market_crash': {
                'price_change': -20,
                'volatility_change': 50,
                'description': 'Severe market downturn'
            },
            'market_rally': {
                'price_change': 20,
                'volatility_change': -30,
                'description': 'Strong market rally'
            },
            'volatility_spike': {
                'price_change': 0,
                'volatility_change': 100,
                'description': 'Volatility explosion'
            },
            'volatility_crush': {
                'price_change': 0,
                'volatility_change': -50,
                'description': 'Volatility collapse'
            }
        }
        
        results = {}
        for scenario_name, params in scenarios.items():
            result = ScenarioEngine.analyze_combined_scenario(
                strategy=strategy,
                current_price=current_price,
                price_change_pct=params['price_change'],
                volatility_change_pct=params['volatility_change'],
                days_forward=0
            )
            result['description'] = params['description']
            results[scenario_name] = result
        
        return results
    
    @staticmethod
    def sensitivity_analysis(
        strategy: OptionsStrategy,
        current_price: float
    ) -> Dict[str, any]:
        """
        Comprehensive sensitivity analysis across all Greeks.
        
        Args:
            strategy: The options strategy
            current_price: Current underlying price
            
        Returns:
            Sensitivity analysis results
        """
        greeks = strategy.get_aggregated_greeks()
        
        # Price sensitivity (delta)
        price_changes = [-5, -2, -1, 1, 2, 5]
        delta_scenarios = []
        for change_pct in price_changes:
            new_price = current_price * (1 + change_pct / 100)
            price_move = new_price - current_price
            estimated_pnl = greeks.delta * price_move * 100  # 100 shares per contract
            delta_scenarios.append({
                'price_change_percent': change_pct,
                'estimated_pnl': round(estimated_pnl, 2)
            })
        
        # Volatility sensitivity (vega)
        vol_changes = [-10, -5, -2, 2, 5, 10]
        vega_scenarios = []
        for vol_change in vol_changes:
            vega_impact = greeks.vega * vol_change
            vega_scenarios.append({
                'volatility_change_percent': vol_change,
                'estimated_pnl': round(vega_impact, 2)
            })
        
        # Time sensitivity (theta)
        days = [1, 7, 14, 30]
        theta_scenarios = []
        for day in days:
            theta_impact = greeks.theta * day
            theta_scenarios.append({
                'days_forward': day,
                'estimated_pnl': round(theta_impact, 2)
            })
        
        return {
            'current_greeks': greeks.to_dict(),
            'delta_sensitivity': delta_scenarios,
            'vega_sensitivity': vega_scenarios,
            'theta_sensitivity': theta_scenarios,
            'interpretation': {
                'delta': 'Shows P&L change for price movements',
                'vega': 'Shows P&L change for volatility movements',
                'theta': 'Shows P&L change over time',
                'gamma': f"Gamma {greeks.gamma:.4f} - Delta will change by this amount per $1 move",
                'rho': f"Rho {greeks.rho:.4f} - P&L change per 1% interest rate change"
            }
        }


class ScenarioComparator:
    """Compare multiple strategies under the same scenarios."""
    
    @staticmethod
    def compare_strategies(
        strategies: List[OptionsStrategy],
        current_price: float,
        scenario_params: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Compare multiple strategies under the same scenario.
        
        Args:
            strategies: List of strategies to compare
            current_price: Current underlying price
            scenario_params: Scenario parameters
            
        Returns:
            Comparison results
        """
        results = []
        
        for strategy in strategies:
            scenario_result = ScenarioEngine.analyze_combined_scenario(
                strategy=strategy,
                current_price=current_price,
                price_change_pct=scenario_params.get('price_change_pct', 0),
                volatility_change_pct=scenario_params.get('volatility_change_pct', 0),
                days_forward=scenario_params.get('days_forward', 0)
            )
            
            results.append({
                'strategy_id': strategy.id,
                'strategy_name': strategy.name,
                'strategy_type': strategy.strategy_type.value,
                'scenario_result': scenario_result,
                'initial_cost': strategy.get_total_cost(),
                'num_legs': len(strategy.legs)
            })
        
        # Rank by estimated P&L
        results.sort(key=lambda x: x['scenario_result']['estimated_total_pnl'], reverse=True)
        
        return {
            'scenario_params': scenario_params,
            'num_strategies': len(strategies),
            'results': results,
            'best_performer': results[0]['strategy_name'] if results else None,
            'worst_performer': results[-1]['strategy_name'] if results else None
        }
