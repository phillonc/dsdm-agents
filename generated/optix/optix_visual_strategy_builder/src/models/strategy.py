"""
Strategy models for the Visual Strategy Builder
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from decimal import Decimal
import uuid

from .option import Option, OptionType, OptionPosition


class StrategyTemplate(Enum):
    """Predefined strategy templates"""
    CUSTOM = "CUSTOM"
    IRON_CONDOR = "IRON_CONDOR"
    BUTTERFLY = "BUTTERFLY"
    STRADDLE = "STRADDLE"
    STRANGLE = "STRANGLE"
    BULL_CALL_SPREAD = "BULL_CALL_SPREAD"
    BEAR_PUT_SPREAD = "BEAR_PUT_SPREAD"
    CALENDAR_SPREAD = "CALENDAR_SPREAD"
    COVERED_CALL = "COVERED_CALL"
    PROTECTIVE_PUT = "PROTECTIVE_PUT"
    COLLAR = "COLLAR"
    IRON_BUTTERFLY = "IRON_BUTTERFLY"
    DIAGONAL_SPREAD = "DIAGONAL_SPREAD"


@dataclass
class StrategyLeg:
    """
    Represents a single leg in an options strategy
    """
    option: Option
    leg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert leg to dictionary"""
        return {
            'leg_id': self.leg_id,
            'option': self.option.to_dict(),
            'notes': self.notes
        }


@dataclass
class Strategy:
    """
    Represents a complete options trading strategy
    """
    name: str
    legs: List[StrategyLeg] = field(default_factory=list)
    template: StrategyTemplate = StrategyTemplate.CUSTOM
    strategy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def add_leg(self, option: Option, notes: Optional[str] = None) -> StrategyLeg:
        """Add a new leg to the strategy"""
        leg = StrategyLeg(option=option, notes=notes)
        self.legs.append(leg)
        self.updated_at = datetime.utcnow()
        return leg
    
    def remove_leg(self, leg_id: str) -> bool:
        """Remove a leg from the strategy"""
        original_length = len(self.legs)
        self.legs = [leg for leg in self.legs if leg.leg_id != leg_id]
        if len(self.legs) < original_length:
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def get_leg(self, leg_id: str) -> Optional[StrategyLeg]:
        """Get a specific leg by ID"""
        for leg in self.legs:
            if leg.leg_id == leg_id:
                return leg
        return None
    
    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost/credit of the strategy"""
        return sum((leg.option.total_premium for leg in self.legs), Decimal('0'))
    
    @property
    def is_debit_strategy(self) -> bool:
        """Check if this is a debit strategy (costs money to enter)"""
        return self.total_cost < 0
    
    @property
    def is_credit_strategy(self) -> bool:
        """Check if this is a credit strategy (receives money to enter)"""
        return self.total_cost > 0
    
    @property
    def net_quantity(self) -> int:
        """Calculate net quantity across all legs"""
        total = 0
        for leg in self.legs:
            if leg.option.position == OptionPosition.LONG:
                total += leg.option.quantity
            else:
                total -= leg.option.quantity
        return total
    
    def get_underlying_symbols(self) -> List[str]:
        """Get list of unique underlying symbols"""
        return list(set(leg.option.underlying_symbol for leg in self.legs))
    
    def get_expiration_dates(self) -> List[datetime]:
        """Get list of unique expiration dates"""
        dates = list(set(leg.option.expiration_date for leg in self.legs))
        return sorted(dates)
    
    def calculate_breakeven_points(self, underlying_price: Decimal) -> List[Decimal]:
        """
        Calculate breakeven points for the strategy
        Note: This is a simplified calculation. Complex strategies may need more sophisticated methods.
        """
        breakevens = []
        
        # For simple strategies, calculate based on total cost and strikes
        if len(self.legs) == 1:
            leg = self.legs[0]
            option = leg.option
            cost_per_share = self.total_cost / Decimal('100') / option.quantity
            
            if option.option_type == OptionType.CALL:
                if option.position == OptionPosition.LONG:
                    breakevens.append(option.strike_price - cost_per_share)
                else:
                    breakevens.append(option.strike_price + cost_per_share)
            else:  # PUT
                if option.position == OptionPosition.LONG:
                    breakevens.append(option.strike_price + cost_per_share)
                else:
                    breakevens.append(option.strike_price - cost_per_share)
        
        return breakevens
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate the strategy for consistency
        Returns: (is_valid, list of error messages)
        """
        errors = []
        
        if not self.legs:
            errors.append("Strategy must have at least one leg")
        
        # Check that all legs have same underlying
        underlying_symbols = self.get_underlying_symbols()
        if len(underlying_symbols) > 1:
            errors.append(f"Strategy has multiple underlying symbols: {underlying_symbols}")
        
        # Check for duplicate legs
        leg_signatures = []
        for leg in self.legs:
            sig = (
                leg.option.strike_price,
                leg.option.option_type,
                leg.option.position,
                leg.option.expiration_date
            )
            if sig in leg_signatures:
                errors.append(f"Duplicate leg detected: {sig}")
            leg_signatures.append(sig)
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> dict:
        """Convert strategy to dictionary"""
        is_valid, validation_errors = self.validate()
        
        return {
            'strategy_id': self.strategy_id,
            'name': self.name,
            'template': self.template.value,
            'description': self.description,
            'legs': [leg.to_dict() for leg in self.legs],
            'total_cost': float(self.total_cost),
            'is_debit_strategy': self.is_debit_strategy,
            'is_credit_strategy': self.is_credit_strategy,
            'net_quantity': self.net_quantity,
            'underlying_symbols': self.get_underlying_symbols(),
            'expiration_dates': [d.isoformat() for d in self.get_expiration_dates()],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'tags': self.tags,
            'is_valid': is_valid,
            'validation_errors': validation_errors
        }
