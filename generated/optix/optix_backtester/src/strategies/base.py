"""
Base strategy interface
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional
from ..models.option import OptionStrategy, MarketConditions


class StrategyBase(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(self, name: str, params: Optional[Dict] = None):
        self.name = name
        self.params = params or {}
    
    @abstractmethod
    async def generate_signals(
        self,
        market_condition: MarketConditions,
        current_positions: Dict[str, OptionStrategy],
        available_capital: float
    ) -> List[OptionStrategy]:
        """
        Generate trading signals
        
        Args:
            market_condition: Current market state
            current_positions: Currently open positions
            available_capital: Available trading capital
            
        Returns:
            List of strategy signals to execute
        """
        pass
    
    @abstractmethod
    async def should_exit(
        self,
        position: OptionStrategy,
        market_condition: MarketConditions,
        available_capital: float
    ) -> Tuple[bool, str]:
        """
        Check if position should be exited
        
        Args:
            position: Current position
            market_condition: Current market state
            available_capital: Available capital
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        pass
    
    def validate_signal(
        self,
        signal: OptionStrategy,
        current_positions: Dict[str, OptionStrategy],
        max_positions: int
    ) -> bool:
        """
        Validate if signal should be executed
        
        Args:
            signal: Strategy signal
            current_positions: Current positions
            max_positions: Maximum allowed positions
            
        Returns:
            True if signal is valid
        """
        # Check position limits
        if len(current_positions) >= max_positions:
            return False
        
        # Check if already have position in same strategy
        if signal.strategy_id in current_positions:
            return False
        
        return True
