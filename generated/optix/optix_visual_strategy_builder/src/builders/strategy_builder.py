"""
Main strategy builder for creating and managing options strategies
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
import uuid

from ..models.option import Option, OptionType, OptionPosition
from ..models.strategy import Strategy, StrategyTemplate, StrategyLeg
from ..calculators.greeks_calculator import GreeksCalculator
from ..calculators.pnl_calculator import PnLCalculator
from ..calculators.risk_calculator import RiskCalculator


class StrategyBuilder:
    """
    Builder for creating and modifying options strategies with drag-and-drop functionality
    """
    
    def __init__(self):
        self.strategy: Optional[Strategy] = None
        self._history: List[Dict] = []
    
    def create_strategy(
        self,
        name: str,
        template: StrategyTemplate = StrategyTemplate.CUSTOM,
        description: Optional[str] = None
    ) -> Strategy:
        """
        Create a new strategy
        
        Args:
            name: Strategy name
            template: Strategy template type
            description: Strategy description
            
        Returns:
            Created strategy
        """
        self.strategy = Strategy(
            name=name,
            template=template,
            description=description
        )
        self._add_to_history('create_strategy', {'name': name, 'template': template.value})
        return self.strategy
    
    def add_option(
        self,
        symbol: str,
        underlying_symbol: str,
        option_type: OptionType,
        strike_price: Decimal,
        expiration_date: datetime,
        quantity: int,
        position: OptionPosition,
        premium: Decimal,
        underlying_price: Optional[Decimal] = None,
        implied_volatility: Optional[Decimal] = None,
        notes: Optional[str] = None
    ) -> StrategyLeg:
        """
        Add an option leg to the strategy (drag-and-drop simulation)
        
        Args:
            symbol: Option symbol
            underlying_symbol: Underlying asset symbol
            option_type: CALL or PUT
            strike_price: Strike price
            expiration_date: Expiration date
            quantity: Number of contracts
            position: LONG or SHORT
            premium: Option premium per share
            underlying_price: Current underlying price
            implied_volatility: Implied volatility
            notes: Optional notes about the leg
            
        Returns:
            Created strategy leg
        """
        if self.strategy is None:
            raise ValueError("No active strategy. Create a strategy first.")
        
        option = Option(
            symbol=symbol,
            underlying_symbol=underlying_symbol,
            option_type=option_type,
            strike_price=strike_price,
            expiration_date=expiration_date,
            quantity=quantity,
            position=position,
            premium=premium,
            underlying_price=underlying_price,
            implied_volatility=implied_volatility,
            id=str(uuid.uuid4())
        )
        
        leg = self.strategy.add_leg(option, notes)
        self._add_to_history('add_option', {
            'leg_id': leg.leg_id,
            'symbol': symbol,
            'strike': float(strike_price),
            'type': option_type.value
        })
        
        return leg
    
    def remove_option(self, leg_id: str) -> bool:
        """
        Remove an option leg from the strategy (drag-and-drop removal)
        
        Args:
            leg_id: ID of the leg to remove
            
        Returns:
            True if removed, False if not found
        """
        if self.strategy is None:
            raise ValueError("No active strategy")
        
        removed = self.strategy.remove_leg(leg_id)
        if removed:
            self._add_to_history('remove_option', {'leg_id': leg_id})
        return removed
    
    def update_option(
        self,
        leg_id: str,
        quantity: Optional[int] = None,
        premium: Optional[Decimal] = None,
        underlying_price: Optional[Decimal] = None,
        implied_volatility: Optional[Decimal] = None
    ) -> bool:
        """
        Update an existing option leg
        
        Args:
            leg_id: ID of the leg to update
            quantity: New quantity (optional)
            premium: New premium (optional)
            underlying_price: New underlying price (optional)
            implied_volatility: New IV (optional)
            
        Returns:
            True if updated, False if not found
        """
        if self.strategy is None:
            raise ValueError("No active strategy")
        
        leg = self.strategy.get_leg(leg_id)
        if leg is None:
            return False
        
        updates = {}
        if quantity is not None:
            leg.option.quantity = quantity
            updates['quantity'] = quantity
        if premium is not None:
            leg.option.premium = premium
            updates['premium'] = float(premium)
        if underlying_price is not None:
            leg.option.underlying_price = underlying_price
            updates['underlying_price'] = float(underlying_price)
        if implied_volatility is not None:
            leg.option.implied_volatility = implied_volatility
            updates['implied_volatility'] = float(implied_volatility)
        
        if updates:
            self._add_to_history('update_option', {'leg_id': leg_id, **updates})
        
        return True
    
    def calculate_strategy_metrics(self) -> Dict:
        """
        Calculate comprehensive metrics for the current strategy
        
        Returns:
            Dictionary with all strategy metrics
        """
        if self.strategy is None:
            raise ValueError("No active strategy")
        
        # Validate strategy
        is_valid, validation_errors = self.strategy.validate()
        if not is_valid:
            return {
                'is_valid': False,
                'errors': validation_errors
            }
        
        # Calculate Greeks
        greeks = GreeksCalculator.calculate_strategy_greeks(self.strategy)
        
        # Calculate P&L metrics
        risk_reward = PnLCalculator.calculate_risk_reward_ratio(self.strategy)
        
        # Get payoff diagram
        payoff = PnLCalculator.calculate_payoff_diagram(
            self.strategy,
            at_expiration=True
        )
        
        # Calculate risk metrics
        risk_metrics = RiskCalculator.calculate_risk_metrics(self.strategy)
        
        return {
            'is_valid': True,
            'strategy': self.strategy.to_dict(),
            'greeks': greeks.to_dict(),
            'risk_reward': {k: float(v) if isinstance(v, Decimal) else v 
                          for k, v in risk_reward.items()},
            'payoff_diagram': payoff,
            'risk_metrics': risk_metrics
        }
    
    def get_strategy_summary(self) -> Dict:
        """
        Get a summary of the current strategy
        
        Returns:
            Strategy summary dictionary
        """
        if self.strategy is None:
            return {'error': 'No active strategy'}
        
        return {
            'strategy_id': self.strategy.strategy_id,
            'name': self.strategy.name,
            'template': self.strategy.template.value,
            'num_legs': len(self.strategy.legs),
            'total_cost': float(self.strategy.total_cost),
            'is_debit': self.strategy.is_debit_strategy,
            'is_credit': self.strategy.is_credit_strategy,
            'underlying_symbols': self.strategy.get_underlying_symbols(),
            'expiration_dates': [d.isoformat() for d in self.strategy.get_expiration_dates()],
            'created_at': self.strategy.created_at.isoformat(),
            'updated_at': self.strategy.updated_at.isoformat()
        }
    
    def clone_strategy(self, new_name: Optional[str] = None) -> Strategy:
        """
        Clone the current strategy
        
        Args:
            new_name: Name for the cloned strategy
            
        Returns:
            Cloned strategy
        """
        if self.strategy is None:
            raise ValueError("No active strategy to clone")
        
        name = new_name or f"{self.strategy.name} (Copy)"
        
        cloned = Strategy(
            name=name,
            template=self.strategy.template,
            description=self.strategy.description,
            tags=self.strategy.tags.copy()
        )
        
        for leg in self.strategy.legs:
            option = leg.option
            new_option = Option(
                symbol=option.symbol,
                underlying_symbol=option.underlying_symbol,
                option_type=option.option_type,
                strike_price=option.strike_price,
                expiration_date=option.expiration_date,
                quantity=option.quantity,
                position=option.position,
                premium=option.premium,
                underlying_price=option.underlying_price,
                implied_volatility=option.implied_volatility,
                interest_rate=option.interest_rate,
                dividend_yield=option.dividend_yield
            )
            cloned.add_leg(new_option, leg.notes)
        
        return cloned
    
    def get_history(self) -> List[Dict]:
        """
        Get the modification history
        
        Returns:
            List of historical actions
        """
        return self._history.copy()
    
    def clear_history(self):
        """Clear the modification history"""
        self._history.clear()
    
    def _add_to_history(self, action: str, details: Dict):
        """Add an action to the history"""
        self._history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'details': details
        })
    
    def export_strategy(self) -> Dict:
        """
        Export strategy to a serializable format
        
        Returns:
            Strategy export dictionary
        """
        if self.strategy is None:
            raise ValueError("No active strategy to export")
        
        return {
            'export_version': '1.0',
            'exported_at': datetime.utcnow().isoformat(),
            'strategy': self.strategy.to_dict(),
            'history': self._history
        }
    
    def import_strategy(self, export_data: Dict) -> Strategy:
        """
        Import a strategy from export data
        
        Args:
            export_data: Strategy export dictionary
            
        Returns:
            Imported strategy
        """
        strategy_data = export_data.get('strategy', {})
        
        self.strategy = Strategy(
            name=strategy_data.get('name', 'Imported Strategy'),
            template=StrategyTemplate[strategy_data.get('template', 'CUSTOM')],
            description=strategy_data.get('description'),
            tags=strategy_data.get('tags', [])
        )
        
        # Import legs
        for leg_data in strategy_data.get('legs', []):
            option_data = leg_data.get('option', {})
            
            option = Option(
                symbol=option_data['symbol'],
                underlying_symbol=option_data['underlying_symbol'],
                option_type=OptionType[option_data['option_type']],
                strike_price=Decimal(str(option_data['strike_price'])),
                expiration_date=datetime.fromisoformat(option_data['expiration_date']),
                quantity=option_data['quantity'],
                position=OptionPosition[option_data['position']],
                premium=Decimal(str(option_data['premium'])),
                underlying_price=Decimal(str(option_data['underlying_price'])) if option_data.get('underlying_price') else None,
                implied_volatility=Decimal(str(option_data['implied_volatility'])) if option_data.get('implied_volatility') else None
            )
            
            self.strategy.add_leg(option, leg_data.get('notes'))
        
        return self.strategy
