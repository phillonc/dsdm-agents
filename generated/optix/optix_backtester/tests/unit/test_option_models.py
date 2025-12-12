"""
Unit tests for option models
"""
import pytest
from datetime import datetime, date, timedelta

from src.models.option import (
    OptionType, OptionSide, OptionContract, OptionQuote,
    OptionLeg, OptionStrategy, MarketConditions
)


class TestOptionContract:
    """Test OptionContract model"""
    
    def test_contract_creation(self):
        """Test creating option contract"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        assert contract.symbol == "SPY"
        assert contract.strike == 450.0
        assert contract.option_type == OptionType.CALL
        assert contract.contract_symbol != ""
    
    def test_contract_symbol_generation(self):
        """Test automatic contract symbol generation"""
        contract = OptionContract(
            symbol="AAPL",
            expiration=date(2024, 6, 21),
            strike=180.5,
            option_type=OptionType.PUT
        )
        
        # Should generate OCC-style symbol
        assert "AAPL" in contract.contract_symbol
        assert "240621" in contract.contract_symbol
        assert "P" in contract.contract_symbol
    
    def test_invalid_strike(self):
        """Test validation of negative strike"""
        with pytest.raises(ValueError):
            OptionContract(
                symbol="SPY",
                expiration=date(2024, 12, 31),
                strike=-100.0,
                option_type=OptionType.CALL
            )


class TestOptionQuote:
    """Test OptionQuote model"""
    
    def test_quote_creation(self):
        """Test creating option quote"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        quote = OptionQuote(
            contract=contract,
            timestamp=datetime.now(),
            bid=5.50,
            ask=5.60,
            last=5.55,
            volume=1000,
            implied_volatility=0.25
        )
        
        assert quote.bid == 5.50
        assert quote.ask == 5.60
        assert quote.implied_volatility == 0.25
    
    def test_mid_price_calculation(self):
        """Test mid price calculation"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        quote = OptionQuote(
            contract=contract,
            timestamp=datetime.now(),
            bid=5.00,
            ask=6.00
        )
        
        assert quote.mid_price == 5.50
    
    def test_spread_calculation(self):
        """Test bid-ask spread calculation"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        quote = OptionQuote(
            contract=contract,
            timestamp=datetime.now(),
            bid=5.00,
            ask=5.50
        )
        
        assert quote.spread == 0.50
        assert quote.spread_percent == pytest.approx(9.52, rel=0.1)


class TestOptionLeg:
    """Test OptionLeg model"""
    
    def test_leg_creation(self):
        """Test creating option leg"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        leg = OptionLeg(
            contract=contract,
            side=OptionSide.BUY,
            quantity=10,
            entry_price=5.50
        )
        
        assert leg.quantity == 10
        assert leg.entry_price == 5.50
        assert leg.side == OptionSide.BUY
    
    def test_position_multiplier(self):
        """Test position multiplier calculation"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        buy_leg = OptionLeg(
            contract=contract,
            side=OptionSide.BUY,
            quantity=1
        )
        
        sell_leg = OptionLeg(
            contract=contract,
            side=OptionSide.SELL,
            quantity=1
        )
        
        assert buy_leg.position_multiplier == 1
        assert sell_leg.position_multiplier == -1
    
    def test_pnl_calculation_buy(self):
        """Test P&L calculation for buy leg"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        leg = OptionLeg(
            contract=contract,
            side=OptionSide.BUY,
            quantity=2,
            entry_price=5.00,
            exit_price=7.00
        )
        
        pnl = leg.calculate_pnl()
        # (7.00 - 5.00) * 2 * 100 = 400
        assert pnl == 400.0
    
    def test_pnl_calculation_sell(self):
        """Test P&L calculation for sell leg"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        leg = OptionLeg(
            contract=contract,
            side=OptionSide.SELL,
            quantity=2,
            entry_price=5.00,
            exit_price=3.00
        )
        
        pnl = leg.calculate_pnl()
        # (3.00 - 5.00) * -1 * 2 * 100 = 400
        assert pnl == 400.0


class TestOptionStrategy:
    """Test OptionStrategy model"""
    
    def test_strategy_creation(self):
        """Test creating option strategy"""
        contract = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        leg = OptionLeg(
            contract=contract,
            side=OptionSide.BUY,
            quantity=1
        )
        
        strategy = OptionStrategy(
            strategy_id="test-123",
            name="Long Call",
            legs=[leg]
        )
        
        assert strategy.name == "Long Call"
        assert len(strategy.legs) == 1
        assert strategy.is_open
    
    def test_total_contracts(self):
        """Test total contracts calculation"""
        contract1 = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        contract2 = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=440.0,
            option_type=OptionType.CALL
        )
        
        strategy = OptionStrategy(
            strategy_id="test-123",
            name="Call Spread",
            legs=[
                OptionLeg(contract=contract1, side=OptionSide.BUY, quantity=5),
                OptionLeg(contract=contract2, side=OptionSide.SELL, quantity=5)
            ]
        )
        
        assert strategy.total_contracts == 10
    
    def test_total_pnl_calculation(self):
        """Test total P&L calculation"""
        contract1 = OptionContract(
            symbol="SPY",
            expiration=date(2024, 12, 31),
            strike=450.0,
            option_type=OptionType.CALL
        )
        
        strategy = OptionStrategy(
            strategy_id="test-123",
            name="Long Call",
            legs=[
                OptionLeg(
                    contract=contract1,
                    side=OptionSide.BUY,
                    quantity=1,
                    entry_price=5.00,
                    exit_price=7.00
                )
            ]
        )
        
        pnl = strategy.calculate_total_pnl()
        assert pnl == 200.0  # (7-5) * 1 * 100


class TestMarketConditions:
    """Test MarketConditions model"""
    
    def test_conditions_creation(self):
        """Test creating market conditions"""
        conditions = MarketConditions(
            timestamp=datetime.now(),
            underlying_price=450.0,
            underlying_symbol="SPY",
            implied_volatility=0.25,
            historical_volatility=0.20
        )
        
        assert conditions.underlying_price == 450.0
        assert conditions.implied_volatility == 0.25
    
    def test_volatility_regime_classification(self):
        """Test volatility regime classification"""
        low_vol = MarketConditions(
            timestamp=datetime.now(),
            underlying_price=450.0,
            underlying_symbol="SPY",
            implied_volatility=0.10
        )
        
        medium_vol = MarketConditions(
            timestamp=datetime.now(),
            underlying_price=450.0,
            underlying_symbol="SPY",
            implied_volatility=0.20
        )
        
        high_vol = MarketConditions(
            timestamp=datetime.now(),
            underlying_price=450.0,
            underlying_symbol="SPY",
            implied_volatility=0.35
        )
        
        assert low_vol.volatility_regime == "low"
        assert medium_vol.volatility_regime == "medium"
        assert high_vol.volatility_regime == "high"
