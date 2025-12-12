"""
Main API interface for Visual Strategy Builder
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from ..models.option import OptionType, OptionPosition
from ..models.strategy import StrategyTemplate
from ..builders.strategy_builder import StrategyBuilder
from ..builders.template_builder import TemplateBuilder
from ..visualization.payoff_visualizer import PayoffVisualizer
from ..visualization.greeks_visualizer import GreeksVisualizer
from ..calculators.risk_calculator import RiskCalculator


class StrategyAPI:
    """
    High-level API for the Visual Strategy Builder
    Provides a simplified interface for all functionality
    """
    
    def __init__(self):
        self.builder = StrategyBuilder()
        self.template_builder = TemplateBuilder()
    
    # Strategy Management
    
    def create_custom_strategy(self, name: str, description: str = None) -> Dict:
        """
        Create a new custom strategy
        
        Args:
            name: Strategy name
            description: Strategy description
            
        Returns:
            Strategy summary
        """
        strategy = self.builder.create_strategy(name, StrategyTemplate.CUSTOM, description)
        return self.builder.get_strategy_summary()
    
    def create_from_template(
        self,
        template_name: str,
        underlying_symbol: str,
        underlying_price: float,
        expiration_date: str,
        **kwargs
    ) -> Dict:
        """
        Create a strategy from a predefined template
        
        Args:
            template_name: Name of template (e.g., 'IRON_CONDOR')
            underlying_symbol: Symbol of underlying asset
            underlying_price: Current underlying price
            expiration_date: Expiration date (ISO format)
            **kwargs: Template-specific parameters
            
        Returns:
            Strategy summary with metrics
        """
        exp_date = datetime.fromisoformat(expiration_date)
        price = Decimal(str(underlying_price))
        
        template_map = {
            'IRON_CONDOR': lambda: self.template_builder.create_iron_condor(
                underlying_symbol, price, exp_date,
                kwargs.get('put_short_strike', price * Decimal('0.95')),
                kwargs.get('put_long_strike', price * Decimal('0.90')),
                kwargs.get('call_short_strike', price * Decimal('1.05')),
                kwargs.get('call_long_strike', price * Decimal('1.10'))
            ),
            'BUTTERFLY': lambda: self.template_builder.create_butterfly(
                underlying_symbol, price, exp_date,
                kwargs.get('lower_strike', price * Decimal('0.95')),
                kwargs.get('middle_strike', price),
                kwargs.get('upper_strike', price * Decimal('1.05'))
            ),
            'STRADDLE': lambda: self.template_builder.create_straddle(
                underlying_symbol, price, exp_date, price
            ),
            'STRANGLE': lambda: self.template_builder.create_strangle(
                underlying_symbol, price, exp_date,
                kwargs.get('put_strike', price * Decimal('0.95')),
                kwargs.get('call_strike', price * Decimal('1.05'))
            ),
            'BULL_CALL_SPREAD': lambda: self.template_builder.create_bull_call_spread(
                underlying_symbol, price, exp_date,
                kwargs.get('long_strike', price * Decimal('0.98')),
                kwargs.get('short_strike', price * Decimal('1.02'))
            ),
            'BEAR_PUT_SPREAD': lambda: self.template_builder.create_bear_put_spread(
                underlying_symbol, price, exp_date,
                kwargs.get('long_strike', price * Decimal('1.02')),
                kwargs.get('short_strike', price * Decimal('0.98'))
            )
        }
        
        if template_name not in template_map:
            return {'error': f'Unknown template: {template_name}'}
        
        self.builder.strategy = template_map[template_name]()
        return self.get_strategy_analysis()
    
    def add_option_leg(
        self,
        symbol: str,
        underlying_symbol: str,
        option_type: str,
        strike_price: float,
        expiration_date: str,
        quantity: int,
        position: str,
        premium: float,
        underlying_price: float = None,
        implied_volatility: float = None
    ) -> Dict:
        """
        Add an option leg to the current strategy
        
        Args:
            symbol: Option symbol
            underlying_symbol: Underlying symbol
            option_type: 'CALL' or 'PUT'
            strike_price: Strike price
            expiration_date: Expiration date (ISO format)
            quantity: Number of contracts
            position: 'LONG' or 'SHORT'
            premium: Option premium per share
            underlying_price: Current underlying price
            implied_volatility: Implied volatility (decimal, e.g., 0.25 for 25%)
            
        Returns:
            Updated strategy summary
        """
        leg = self.builder.add_option(
            symbol=symbol,
            underlying_symbol=underlying_symbol,
            option_type=OptionType[option_type],
            strike_price=Decimal(str(strike_price)),
            expiration_date=datetime.fromisoformat(expiration_date),
            quantity=quantity,
            position=OptionPosition[position],
            premium=Decimal(str(premium)),
            underlying_price=Decimal(str(underlying_price)) if underlying_price else None,
            implied_volatility=Decimal(str(implied_volatility)) if implied_volatility else None
        )
        
        return {
            'leg_id': leg.leg_id,
            'strategy_summary': self.builder.get_strategy_summary()
        }
    
    def remove_option_leg(self, leg_id: str) -> Dict:
        """
        Remove an option leg from the strategy
        
        Args:
            leg_id: ID of the leg to remove
            
        Returns:
            Updated strategy summary
        """
        removed = self.builder.remove_option(leg_id)
        return {
            'removed': removed,
            'strategy_summary': self.builder.get_strategy_summary()
        }
    
    def update_option_leg(
        self,
        leg_id: str,
        quantity: int = None,
        premium: float = None,
        underlying_price: float = None,
        implied_volatility: float = None
    ) -> Dict:
        """
        Update an existing option leg
        
        Args:
            leg_id: ID of the leg to update
            quantity: New quantity
            premium: New premium
            underlying_price: New underlying price
            implied_volatility: New implied volatility
            
        Returns:
            Updated strategy summary
        """
        updated = self.builder.update_option(
            leg_id=leg_id,
            quantity=quantity,
            premium=Decimal(str(premium)) if premium else None,
            underlying_price=Decimal(str(underlying_price)) if underlying_price else None,
            implied_volatility=Decimal(str(implied_volatility)) if implied_volatility else None
        )
        
        return {
            'updated': updated,
            'strategy_summary': self.builder.get_strategy_summary()
        }
    
    # Analysis and Visualization
    
    def get_strategy_analysis(self) -> Dict:
        """
        Get comprehensive analysis of the current strategy
        
        Returns:
            Complete strategy analysis including metrics, Greeks, P&L, risk
        """
        return self.builder.calculate_strategy_metrics()
    
    def get_payoff_diagram(
        self,
        min_price: float = None,
        max_price: float = None,
        num_points: int = 200
    ) -> Dict:
        """
        Get payoff diagram data for visualization
        
        Args:
            min_price: Minimum price for diagram
            max_price: Maximum price for diagram
            num_points: Number of data points
            
        Returns:
            Payoff diagram data
        """
        if self.builder.strategy is None:
            return {'error': 'No active strategy'}
        
        price_range = None
        if min_price and max_price:
            price_range = (Decimal(str(min_price)), Decimal(str(max_price)))
        
        return PayoffVisualizer.generate_payoff_data(
            self.builder.strategy,
            price_range,
            num_points
        )
    
    def get_greeks_analysis(self) -> Dict:
        """
        Get Greeks analysis for the strategy
        
        Returns:
            Greeks summary and interpretations
        """
        if self.builder.strategy is None:
            return {'error': 'No active strategy'}
        
        return GreeksVisualizer.generate_greeks_summary(self.builder.strategy)
    
    def get_greeks_profile(
        self,
        min_price: float = None,
        max_price: float = None,
        num_points: int = 100
    ) -> Dict:
        """
        Get Greeks profile across price range
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            num_points: Number of points
            
        Returns:
            Greeks profile data
        """
        if self.builder.strategy is None:
            return {'error': 'No active strategy'}
        
        price_range = None
        if min_price and max_price:
            price_range = (Decimal(str(min_price)), Decimal(str(max_price)))
        
        return GreeksVisualizer.generate_greeks_profile(
            self.builder.strategy,
            price_range,
            num_points
        )
    
    def get_risk_metrics(self) -> Dict:
        """
        Get comprehensive risk metrics
        
        Returns:
            Risk metrics including VaR, probability of profit, margin
        """
        if self.builder.strategy is None:
            return {'error': 'No active strategy'}
        
        return RiskCalculator.calculate_risk_metrics(self.builder.strategy)
    
    def run_scenario_analysis(
        self,
        scenario_price: float,
        volatility_change: float = 0.0,
        days_passed: int = 0
    ) -> Dict:
        """
        Run what-if scenario analysis
        
        Args:
            scenario_price: Underlying price in scenario
            volatility_change: Change in IV (e.g., 0.05 for +5%)
            days_passed: Number of days passed
            
        Returns:
            Scenario analysis results
        """
        if self.builder.strategy is None:
            return {'error': 'No active strategy'}
        
        scenario_date = datetime.utcnow()
        if days_passed > 0:
            from datetime import timedelta
            scenario_date += timedelta(days=days_passed)
        
        return RiskCalculator.analyze_scenario(
            self.builder.strategy,
            Decimal(str(scenario_price)),
            scenario_date,
            Decimal(str(volatility_change))
        )
    
    def get_individual_leg_payoffs(self) -> List[Dict]:
        """
        Get payoff diagrams for individual legs
        
        Returns:
            List of leg payoff data
        """
        if self.builder.strategy is None:
            return []
        
        return PayoffVisualizer.generate_individual_leg_payoffs(self.builder.strategy)
    
    def get_time_decay_analysis(
        self,
        underlying_price: float,
        days_points: List[int] = None
    ) -> Dict:
        """
        Get time decay analysis
        
        Args:
            underlying_price: Current underlying price
            days_points: List of days to analyze
            
        Returns:
            Time decay data
        """
        if self.builder.strategy is None:
            return {'error': 'No active strategy'}
        
        return PayoffVisualizer.generate_time_decay_analysis(
            self.builder.strategy,
            Decimal(str(underlying_price)),
            days_points
        )
    
    def get_volatility_analysis(
        self,
        underlying_price: float,
        iv_changes: List[float] = None
    ) -> Dict:
        """
        Get implied volatility impact analysis
        
        Args:
            underlying_price: Current underlying price
            iv_changes: List of IV changes to analyze
            
        Returns:
            Volatility impact data
        """
        if self.builder.strategy is None:
            return {'error': 'No active strategy'}
        
        iv_list = [Decimal(str(iv)) for iv in iv_changes] if iv_changes else None
        
        return PayoffVisualizer.generate_volatility_analysis(
            self.builder.strategy,
            Decimal(str(underlying_price)),
            iv_list
        )
    
    # Utility Methods
    
    def get_available_templates(self) -> Dict:
        """
        Get list of available strategy templates
        
        Returns:
            Dictionary of template names and descriptions
        """
        return self.template_builder.get_template_list()
    
    def export_strategy(self) -> Dict:
        """
        Export current strategy to JSON-serializable format
        
        Returns:
            Strategy export data
        """
        return self.builder.export_strategy()
    
    def import_strategy(self, export_data: Dict) -> Dict:
        """
        Import a strategy from export data
        
        Args:
            export_data: Strategy export data
            
        Returns:
            Imported strategy summary
        """
        self.builder.import_strategy(export_data)
        return self.builder.get_strategy_summary()
    
    def clone_strategy(self, new_name: str = None) -> Dict:
        """
        Clone the current strategy
        
        Args:
            new_name: Name for the cloned strategy
            
        Returns:
            Cloned strategy summary
        """
        cloned = self.builder.clone_strategy(new_name)
        self.builder.strategy = cloned
        return self.builder.get_strategy_summary()
    
    def get_modification_history(self) -> List[Dict]:
        """
        Get strategy modification history
        
        Returns:
            List of historical actions
        """
        return self.builder.get_history()
