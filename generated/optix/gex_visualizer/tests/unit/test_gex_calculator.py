"""Unit tests for GEX calculator."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.core.gex_calculator import GEXCalculator
from src.models.schemas import OptionContract, GammaExposure


class TestGEXCalculator:
    """Test cases for GEXCalculator."""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return GEXCalculator()
    
    @pytest.fixture
    def sample_call_option(self):
        """Create sample call option."""
        return OptionContract(
            symbol="SPY",
            strike=Decimal("450.00"),
            expiration=date.today() + timedelta(days=30),
            option_type="call",
            bid=Decimal("5.50"),
            ask=Decimal("5.75"),
            volume=1000,
            open_interest=5000,
            implied_volatility=0.25,
            delta=0.55,
            gamma=0.01,
            theta=-0.05,
            vega=0.15
        )
    
    @pytest.fixture
    def sample_put_option(self):
        """Create sample put option."""
        return OptionContract(
            symbol="SPY",
            strike=Decimal("450.00"),
            expiration=date.today() + timedelta(days=30),
            option_type="put",
            bid=Decimal("4.50"),
            ask=Decimal("4.75"),
            volume=800,
            open_interest=4000,
            implied_volatility=0.28,
            delta=-0.45,
            gamma=0.01,
            theta=-0.04,
            vega=0.14
        )
    
    def test_calculate_gamma(self, calculator):
        """Test gamma calculation."""
        gamma = calculator.calculate_gamma(
            spot=450.0,
            strike=450.0,
            time_to_expiry=0.1,  # ~25 days
            volatility=0.25,
            risk_free_rate=0.05,
            option_type="call"
        )
        
        assert gamma > 0
        assert gamma < 1  # Gamma should be small value
    
    def test_calculate_gamma_expired(self, calculator):
        """Test gamma calculation for expired option."""
        gamma = calculator.calculate_gamma(
            spot=450.0,
            strike=450.0,
            time_to_expiry=0.0,
            volatility=0.25,
            risk_free_rate=0.05,
            option_type="call"
        )
        
        assert gamma == 0.0
    
    def test_calculate_time_to_expiry(self, calculator):
        """Test time to expiry calculation."""
        future_date = date.today() + timedelta(days=252)
        tte = calculator.calculate_time_to_expiry(future_date)
        
        assert tte == pytest.approx(1.0, rel=0.01)  # ~1 year
    
    def test_calculate_time_to_expiry_expired(self, calculator):
        """Test time to expiry for past date."""
        past_date = date.today() - timedelta(days=10)
        tte = calculator.calculate_time_to_expiry(past_date)
        
        assert tte == 0.0
    
    def test_calculate_gex_for_strike_call_only(
        self,
        calculator,
        sample_call_option
    ):
        """Test GEX calculation with call only."""
        spot_price = Decimal("450.00")
        
        gex = calculator.calculate_gex_for_strike(
            call_contract=sample_call_option,
            put_contract=None,
            spot_price=spot_price
        )
        
        assert isinstance(gex, GammaExposure)
        assert gex.strike == Decimal("450.00")
        assert gex.call_gex != 0
        assert gex.put_gex == 0
        assert gex.call_open_interest == 5000
    
    def test_calculate_gex_for_strike_put_only(
        self,
        calculator,
        sample_put_option
    ):
        """Test GEX calculation with put only."""
        spot_price = Decimal("450.00")
        
        gex = calculator.calculate_gex_for_strike(
            call_contract=None,
            put_contract=sample_put_option,
            spot_price=spot_price
        )
        
        assert isinstance(gex, GammaExposure)
        assert gex.strike == Decimal("450.00")
        assert gex.call_gex == 0
        assert gex.put_gex != 0
        assert gex.put_open_interest == 4000
    
    def test_calculate_gex_for_strike_both(
        self,
        calculator,
        sample_call_option,
        sample_put_option
    ):
        """Test GEX calculation with both call and put."""
        spot_price = Decimal("450.00")
        
        gex = calculator.calculate_gex_for_strike(
            call_contract=sample_call_option,
            put_contract=sample_put_option,
            spot_price=spot_price
        )
        
        assert isinstance(gex, GammaExposure)
        assert gex.call_gex != 0
        assert gex.put_gex != 0
        assert gex.net_gex == gex.call_gex + gex.put_gex
    
    def test_calculate_gex_for_strike_no_contracts(self, calculator):
        """Test GEX calculation with no contracts."""
        with pytest.raises(ValueError):
            calculator.calculate_gex_for_strike(
                call_contract=None,
                put_contract=None,
                spot_price=Decimal("450.00")
            )
    
    def test_calculate_gex_for_chain(
        self,
        calculator,
        sample_call_option,
        sample_put_option
    ):
        """Test GEX calculation for options chain."""
        options_chain = [sample_call_option, sample_put_option]
        spot_price = Decimal("450.00")
        
        results = calculator.calculate_gex_for_chain(
            options_chain=options_chain,
            spot_price=spot_price
        )
        
        assert len(results) == 1  # One strike
        assert results[0].strike == Decimal("450.00")
    
    def test_calculate_gex_for_chain_multiple_strikes(self, calculator):
        """Test GEX calculation with multiple strikes."""
        options_chain = []
        
        for strike_offset in [-10, -5, 0, 5, 10]:
            strike = Decimal("450.00") + Decimal(str(strike_offset))
            
            call = OptionContract(
                symbol="SPY",
                strike=strike,
                expiration=date.today() + timedelta(days=30),
                option_type="call",
                bid=Decimal("5.00"),
                ask=Decimal("5.25"),
                volume=1000,
                open_interest=5000,
                implied_volatility=0.25,
                gamma=0.01
            )
            
            put = OptionContract(
                symbol="SPY",
                strike=strike,
                expiration=date.today() + timedelta(days=30),
                option_type="put",
                bid=Decimal("4.00"),
                ask=Decimal("4.25"),
                volume=800,
                open_interest=4000,
                implied_volatility=0.28,
                gamma=0.01
            )
            
            options_chain.extend([call, put])
        
        results = calculator.calculate_gex_for_chain(
            options_chain=options_chain,
            spot_price=Decimal("450.00")
        )
        
        assert len(results) == 5  # Five strikes
        assert all(isinstance(r, GammaExposure) for r in results)
    
    def test_create_heatmap(self, calculator):
        """Test heatmap creation."""
        gamma_exposures = [
            GammaExposure(
                strike=Decimal("440.00"),
                call_gamma=0.01,
                put_gamma=0.01,
                net_gamma=0.0,
                call_gex=1e9,
                put_gex=-1.2e9,
                net_gex=-0.2e9,
                call_open_interest=5000,
                put_open_interest=6000
            ),
            GammaExposure(
                strike=Decimal("450.00"),
                call_gamma=0.015,
                put_gamma=0.008,
                net_gamma=0.007,
                call_gex=2e9,
                put_gex=-0.8e9,
                net_gex=1.2e9,
                call_open_interest=8000,
                put_open_interest=4000
            )
        ]
        
        heatmap = calculator.create_heatmap(
            symbol="SPY",
            spot_price=Decimal("450.00"),
            gamma_exposures=gamma_exposures
        )
        
        assert heatmap.symbol == "SPY"
        assert heatmap.spot_price == Decimal("450.00")
        assert len(heatmap.strikes) == 2
        assert len(heatmap.gex_values) == 2
        assert len(heatmap.colors) == 2
        assert heatmap.total_net_gex == 1.0e9
