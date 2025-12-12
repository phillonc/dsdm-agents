"""Unit tests for pin risk analyzer."""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.core.pin_risk_analyzer import PinRiskAnalyzer
from src.models.schemas import OptionContract, GammaExposure


class TestPinRiskAnalyzer:
    """Test cases for PinRiskAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return PinRiskAnalyzer(pin_risk_days=5)
    
    @pytest.fixture
    def near_expiry_options(self):
        """Create options near expiration."""
        expiration = date.today() + timedelta(days=3)
        options = []
        
        for strike in [440, 445, 450, 455, 460]:
            call = OptionContract(
                symbol="SPY",
                strike=Decimal(f"{strike}.00"),
                expiration=expiration,
                option_type="call",
                bid=Decimal("5.00"),
                ask=Decimal("5.25"),
                volume=1000,
                open_interest=10000 if strike == 450 else 5000,
                implied_volatility=0.25,
                gamma=0.015 if strike == 450 else 0.01
            )
            
            put = OptionContract(
                symbol="SPY",
                strike=Decimal(f"{strike}.00"),
                expiration=expiration,
                option_type="put",
                bid=Decimal("4.00"),
                ask=Decimal("4.25"),
                volume=800,
                open_interest=12000 if strike == 450 else 4000,
                implied_volatility=0.28,
                gamma=0.015 if strike == 450 else 0.01
            )
            
            options.extend([call, put])
        
        return options
    
    @pytest.fixture
    def gamma_exposures(self):
        """Create gamma exposures."""
        return [
            GammaExposure(
                strike=Decimal(f"{strike}.00"),
                call_gamma=0.015 if strike == 450 else 0.01,
                put_gamma=0.015 if strike == 450 else 0.01,
                net_gamma=0.0,
                call_gex=2e9 if strike == 450 else 1e9,
                put_gex=-2.4e9 if strike == 450 else -0.8e9,
                net_gex=-0.4e9 if strike == 450 else 0.2e9,
                call_open_interest=10000 if strike == 450 else 5000,
                put_open_interest=12000 if strike == 450 else 4000
            )
            for strike in [440, 445, 450, 455, 460]
        ]
    
    def test_analyze_pin_risk_near_expiry(
        self,
        analyzer,
        near_expiry_options,
        gamma_exposures
    ):
        """Test pin risk analysis for near expiration."""
        result = analyzer.analyze_pin_risk(
            symbol="SPY",
            spot_price=Decimal("450.00"),
            options_chain=near_expiry_options,
            gamma_exposures=gamma_exposures
        )
        
        assert result is not None
        assert result.symbol == "SPY"
        assert result.days_to_expiration == 3
        assert len(result.high_oi_strikes) > 0
        assert result.max_pain_strike is not None
        assert 0 <= result.pin_risk_score <= 1
    
    def test_analyze_pin_risk_far_expiry(
        self,
        analyzer,
        gamma_exposures
    ):
        """Test pin risk analysis for far expiration."""
        far_expiry = date.today() + timedelta(days=30)
        options = [
            OptionContract(
                symbol="SPY",
                strike=Decimal("450.00"),
                expiration=far_expiry,
                option_type="call",
                bid=Decimal("5.00"),
                ask=Decimal("5.25"),
                volume=1000,
                open_interest=5000,
                implied_volatility=0.25,
                gamma=0.01
            )
        ]
        
        result = analyzer.analyze_pin_risk(
            symbol="SPY",
            spot_price=Decimal("450.00"),
            options_chain=options,
            gamma_exposures=gamma_exposures
        )
        
        assert result is None  # Too far from expiration
    
    def test_analyze_pin_risk_no_options(self, analyzer):
        """Test pin risk analysis with no options."""
        result = analyzer.analyze_pin_risk(
            symbol="SPY",
            spot_price=Decimal("450.00"),
            options_chain=[],
            gamma_exposures=[]
        )
        
        assert result is None
    
    def test_find_high_oi_strikes(self, analyzer, near_expiry_options):
        """Test finding high OI strikes."""
        high_oi = analyzer._find_high_oi_strikes(near_expiry_options, top_n=3)
        
        assert len(high_oi) == 3
        assert Decimal("450.00") in high_oi  # Highest OI
    
    def test_calculate_max_pain(self, analyzer, near_expiry_options):
        """Test max pain calculation."""
        max_pain = analyzer._calculate_max_pain(
            options=near_expiry_options,
            spot_price=Decimal("450.00")
        )
        
        assert max_pain is not None
        assert isinstance(max_pain, Decimal)
    
    def test_calculate_pin_risk_score_high(self, analyzer):
        """Test pin risk score calculation for high risk."""
        score = analyzer._calculate_pin_risk_score(
            spot_price=Decimal("450.00"),
            high_oi_strikes=[Decimal("450.00"), Decimal("451.00")],
            days_to_expiration=1
        )
        
        assert score > 0.5  # High risk close to expiration
    
    def test_calculate_pin_risk_score_low(self, analyzer):
        """Test pin risk score calculation for low risk."""
        score = analyzer._calculate_pin_risk_score(
            spot_price=Decimal("450.00"),
            high_oi_strikes=[Decimal("400.00"), Decimal("500.00")],
            days_to_expiration=5
        )
        
        assert score < 0.5  # Low risk far from strikes
    
    def test_has_high_pin_risk(self):
        """Test high pin risk property."""
        from src.models.schemas import PinRiskAnalysis
        from datetime import datetime
        
        analysis = PinRiskAnalysis(
            symbol="SPY",
            expiration=date.today() + timedelta(days=2),
            days_to_expiration=2,
            spot_price=Decimal("450.00"),
            high_oi_strikes=[Decimal("450.00")],
            pin_risk_strikes=[Decimal("450.00")],
            max_pain_strike=Decimal("450.00"),
            pin_risk_score=0.8,
            analysis_timestamp=datetime.utcnow()
        )
        
        assert analysis.has_high_pin_risk
