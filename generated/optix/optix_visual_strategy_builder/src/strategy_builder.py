"""
Strategy Builder - Core interface for building and managing strategies.

This module provides the main interface for the drag-and-drop strategy builder.
"""

from typing import List, Dict, Optional, Any
from datetime import date, datetime
from .models import (
    OptionsStrategy, OptionLeg, OptionType, PositionType, 
    StrategyType, Greeks
)
from .strategy_templates import StrategyTemplates
from .pnl_calculator import PayoffCalculator, RealTimePnLTracker
from .scenario_analyzer import ScenarioEngine


class StrategyBuilder:
    """Main interface for building and managing options strategies."""
    
    def __init__(self):
        """Initialize the strategy builder."""
        self.strategies: Dict[str, OptionsStrategy] = {}
        self.pnl_trackers: Dict[str, RealTimePnLTracker] = {}
    
    def create_strategy(
        self,
        name: str,
        underlying_symbol: str,
        strategy_type: StrategyType = StrategyType.CUSTOM
    ) -> OptionsStrategy:
        """
        Create a new strategy.
        
        Args:
            name: Strategy name
            underlying_symbol: Underlying asset symbol
            strategy_type: Type of strategy
            
        Returns:
            Created strategy
        """
        strategy = OptionsStrategy(
            name=name,
            underlying_symbol=underlying_symbol,
            strategy_type=strategy_type
        )
        self.strategies[strategy.id] = strategy
        return strategy
    
    def create_from_template(
        self,
        template_type: StrategyType,
        underlying_symbol: str,
        current_price: float,
        expiration: date,
        **kwargs
    ) -> OptionsStrategy:
        """
        Create a strategy from a template.
        
        Args:
            template_type: Type of strategy template
            underlying_symbol: Underlying asset symbol
            current_price: Current price of underlying
            expiration: Expiration date
            **kwargs: Additional template-specific parameters
            
        Returns:
            Created strategy
        """
        if template_type == StrategyType.IRON_CONDOR:
            strategy = StrategyTemplates.create_iron_condor(
                underlying_symbol=underlying_symbol,
                current_price=current_price,
                expiration=expiration,
                wing_width=kwargs.get('wing_width', 5.0),
                body_width=kwargs.get('body_width', 10.0),
                quantity=kwargs.get('quantity', 1)
            )
        elif template_type == StrategyType.BUTTERFLY:
            strategy = StrategyTemplates.create_butterfly(
                underlying_symbol=underlying_symbol,
                current_price=current_price,
                expiration=expiration,
                wing_width=kwargs.get('wing_width', 5.0),
                quantity=kwargs.get('quantity', 1),
                option_type=kwargs.get('option_type', OptionType.CALL)
            )
        elif template_type == StrategyType.STRADDLE:
            strategy = StrategyTemplates.create_straddle(
                underlying_symbol=underlying_symbol,
                strike=kwargs.get('strike', current_price),
                expiration=expiration,
                quantity=kwargs.get('quantity', 1),
                position_type=kwargs.get('position_type', PositionType.LONG)
            )
        elif template_type == StrategyType.STRANGLE:
            strategy = StrategyTemplates.create_strangle(
                underlying_symbol=underlying_symbol,
                current_price=current_price,
                expiration=expiration,
                strike_distance=kwargs.get('strike_distance', 5.0),
                quantity=kwargs.get('quantity', 1),
                position_type=kwargs.get('position_type', PositionType.LONG)
            )
        elif template_type == StrategyType.VERTICAL_SPREAD:
            strategy = StrategyTemplates.create_vertical_spread(
                underlying_symbol=underlying_symbol,
                current_price=current_price,
                expiration=expiration,
                spread_width=kwargs.get('spread_width', 5.0),
                quantity=kwargs.get('quantity', 1),
                option_type=kwargs.get('option_type', OptionType.CALL),
                is_debit=kwargs.get('is_debit', True)
            )
        elif template_type == StrategyType.COVERED_CALL:
            strategy = StrategyTemplates.create_covered_call(
                underlying_symbol=underlying_symbol,
                current_price=current_price,
                expiration=expiration,
                call_strike=kwargs.get('call_strike', current_price + 5),
                quantity=kwargs.get('quantity', 1)
            )
        elif template_type == StrategyType.PROTECTIVE_PUT:
            strategy = StrategyTemplates.create_protective_put(
                underlying_symbol=underlying_symbol,
                current_price=current_price,
                expiration=expiration,
                put_strike=kwargs.get('put_strike', current_price - 5),
                quantity=kwargs.get('quantity', 1)
            )
        else:
            raise ValueError(f"Unsupported template type: {template_type}")
        
        self.strategies[strategy.id] = strategy
        return strategy
    
    def add_leg_to_strategy(
        self,
        strategy_id: str,
        option_type: OptionType,
        position_type: PositionType,
        strike: float,
        expiration: date,
        quantity: int,
        premium: float,
        implied_volatility: float = 0.25,
        greeks: Optional[Greeks] = None
    ) -> OptionLeg:
        """
        Add a leg to an existing strategy (drag-and-drop interface support).
        
        Args:
            strategy_id: ID of the strategy
            option_type: CALL or PUT
            position_type: LONG or SHORT
            strike: Strike price
            expiration: Expiration date
            quantity: Number of contracts
            premium: Option premium
            implied_volatility: Implied volatility
            greeks: Greeks object (optional)
            
        Returns:
            Created option leg
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        
        if greeks is None:
            greeks = Greeks()
        
        leg = OptionLeg(
            option_type=option_type,
            position_type=position_type,
            strike=strike,
            expiration=expiration,
            quantity=quantity,
            premium=premium,
            underlying_symbol=strategy.underlying_symbol,
            implied_volatility=implied_volatility,
            greeks=greeks
        )
        
        strategy.add_leg(leg)
        return leg
    
    def remove_leg_from_strategy(self, strategy_id: str, leg_id: str) -> bool:
        """
        Remove a leg from a strategy.
        
        Args:
            strategy_id: ID of the strategy
            leg_id: ID of the leg to remove
            
        Returns:
            True if removed, False otherwise
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        return self.strategies[strategy_id].remove_leg(leg_id)
    
    def get_strategy(self, strategy_id: str) -> Optional[OptionsStrategy]:
        """Get a strategy by ID."""
        return self.strategies.get(strategy_id)
    
    def list_strategies(self) -> List[OptionsStrategy]:
        """List all strategies."""
        return list(self.strategies.values())
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """
        Delete a strategy.
        
        Args:
            strategy_id: ID of the strategy to delete
            
        Returns:
            True if deleted, False otherwise
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            if strategy_id in self.pnl_trackers:
                del self.pnl_trackers[strategy_id]
            return True
        return False
    
    def calculate_payoff_diagram(
        self,
        strategy_id: str,
        current_price: Optional[float] = None,
        price_range: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate payoff diagram for a strategy.
        
        Args:
            strategy_id: ID of the strategy
            current_price: Current underlying price
            price_range: Custom price range (optional)
            
        Returns:
            Payoff diagram data
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        return PayoffCalculator.calculate_payoff_diagram(
            strategy=strategy,
            price_range=price_range,
            current_price=current_price
        )
    
    def start_pnl_tracking(self, strategy_id: str) -> None:
        """
        Start real-time P&L tracking for a strategy.
        
        Args:
            strategy_id: ID of the strategy
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        self.pnl_trackers[strategy_id] = RealTimePnLTracker(strategy)
    
    def update_pnl(
        self,
        strategy_id: str,
        current_price: float,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update P&L for a strategy.
        
        Args:
            strategy_id: ID of the strategy
            current_price: Current underlying price
            timestamp: Optional timestamp
            
        Returns:
            P&L snapshot
        """
        if strategy_id not in self.pnl_trackers:
            self.start_pnl_tracking(strategy_id)
        
        return self.pnl_trackers[strategy_id].update_pnl(current_price, timestamp)
    
    def get_pnl_history(self, strategy_id: str) -> List[Dict[str, Any]]:
        """
        Get P&L history for a strategy.
        
        Args:
            strategy_id: ID of the strategy
            
        Returns:
            P&L history
        """
        if strategy_id not in self.pnl_trackers:
            return []
        
        return self.pnl_trackers[strategy_id].get_pnl_history()
    
    def analyze_scenario(
        self,
        strategy_id: str,
        current_price: float,
        scenario_type: str,
        **params
    ) -> Dict[str, Any]:
        """
        Run scenario analysis on a strategy.
        
        Args:
            strategy_id: ID of the strategy
            current_price: Current underlying price
            scenario_type: Type of scenario ('price', 'volatility', 'time', 'combined', 'stress')
            **params: Scenario-specific parameters
            
        Returns:
            Scenario analysis results
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        
        if scenario_type == 'price':
            return {
                'type': 'price',
                'results': ScenarioEngine.analyze_price_change(
                    strategy=strategy,
                    current_price=current_price,
                    price_changes=params.get('price_changes', [-10, -5, 0, 5, 10])
                )
            }
        elif scenario_type == 'volatility':
            return {
                'type': 'volatility',
                'results': ScenarioEngine.analyze_volatility_change(
                    strategy=strategy,
                    volatility_changes=params.get('volatility_changes', [-10, -5, 0, 5, 10])
                )
            }
        elif scenario_type == 'time':
            return {
                'type': 'time',
                'results': ScenarioEngine.analyze_time_decay(
                    strategy=strategy,
                    days_forward=params.get('days_forward', [1, 7, 14, 30])
                )
            }
        elif scenario_type == 'combined':
            return {
                'type': 'combined',
                'result': ScenarioEngine.analyze_combined_scenario(
                    strategy=strategy,
                    current_price=current_price,
                    price_change_pct=params.get('price_change_pct', 0),
                    volatility_change_pct=params.get('volatility_change_pct', 0),
                    days_forward=params.get('days_forward', 0)
                )
            }
        elif scenario_type == 'stress':
            return {
                'type': 'stress',
                'results': ScenarioEngine.stress_test(
                    strategy=strategy,
                    current_price=current_price
                )
            }
        elif scenario_type == 'sensitivity':
            return {
                'type': 'sensitivity',
                'results': ScenarioEngine.sensitivity_analysis(
                    strategy=strategy,
                    current_price=current_price
                )
            }
        else:
            raise ValueError(f"Unsupported scenario type: {scenario_type}")
    
    def get_risk_metrics(
        self,
        strategy_id: str,
        current_price: float
    ) -> Dict[str, Any]:
        """
        Get comprehensive risk metrics for a strategy.
        
        Args:
            strategy_id: ID of the strategy
            current_price: Current underlying price
            
        Returns:
            Risk metrics
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy = self.strategies[strategy_id]
        price_range = PayoffCalculator.generate_price_range(current_price)
        
        return {
            'strategy_id': strategy_id,
            'strategy_name': strategy.name,
            'greeks': strategy.get_aggregated_greeks().to_dict(),
            'risk_reward': PayoffCalculator.calculate_risk_reward_ratio(strategy, price_range),
            'probability_analysis': PayoffCalculator.calculate_probability_of_profit(
                strategy=strategy,
                current_price=current_price,
                expected_volatility=0.25,
                days_to_expiration=30
            )
        }
    
    def export_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """
        Export strategy to dictionary format.
        
        Args:
            strategy_id: ID of the strategy
            
        Returns:
            Strategy dictionary
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        return self.strategies[strategy_id].to_dict()
    
    def import_strategy(self, strategy_dict: Dict[str, Any]) -> OptionsStrategy:
        """
        Import strategy from dictionary format.
        
        Args:
            strategy_dict: Strategy dictionary
            
        Returns:
            Imported strategy
        """
        # Create strategy
        strategy = OptionsStrategy(
            name=strategy_dict['name'],
            underlying_symbol=strategy_dict['underlying_symbol'],
            strategy_type=StrategyType(strategy_dict['strategy_type']),
            notes=strategy_dict.get('notes', '')
        )
        
        # Add legs
        for leg_dict in strategy_dict.get('legs', []):
            leg = OptionLeg(
                option_type=OptionType(leg_dict['option_type']),
                position_type=PositionType(leg_dict['position_type']),
                strike=leg_dict['strike'],
                expiration=date.fromisoformat(leg_dict['expiration']),
                quantity=leg_dict['quantity'],
                premium=leg_dict['premium'],
                underlying_symbol=leg_dict['underlying_symbol'],
                implied_volatility=leg_dict['implied_volatility'],
                greeks=Greeks(**leg_dict['greeks'])
            )
            strategy.add_leg(leg)
        
        self.strategies[strategy.id] = strategy
        return strategy
