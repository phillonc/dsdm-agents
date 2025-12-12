"""Unit tests for gamma flip detector."""
import pytest
from decimal import Decimal
from datetime import datetime

from src.core.gamma_flip_detector import GammaFlipDetector
from src.models.schemas import GammaExposure, GammaFlipLevel


class TestGammaFlipDetector:
    """Test cases for GammaFlipDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return GammaFlipDetector(flip_threshold_pct=5.0)
    
    @pytest.fixture
    def gamma_exposures_with_flip(self):
        """Create gamma exposures with a flip level."""
        return [
            GammaExposure(
                strike=Decimal("440.00"),
                call_gamma=0.01,
                put_gamma=0.01,
                net_gamma=0.0,
                call_gex=0.5e9,
                put_gex=-1.5e9,
                net_gex=-1.0e9,
                call_open_interest=5000,
                put_open_interest=6000
            ),
            GammaExposure(
                strike=Decimal("445.00"),
                call_gamma=0.01,
                put_gamma=0.01,
                net_gamma=0.0,
                call_gex=1.0e9,
                put_gex=-0.8e9,
                net_gex=0.2e9,
                call_open_interest=5500,
                put_open_interest=4000
            ),
            GammaExposure(
                strike=Decimal("450.00"),
                call_gamma=0.015,
                put_gamma=0.008,
                net_gamma=0.007,
                call_gex=2.0e9,
                put_gex=-0.5e9,
                net_gex=1.5e9,
                call_open_interest=8000,
                put_open_interest=3000
            )
        ]
    
    def test_detect_flip_level_with_flip(
        self,
        detector,
        gamma_exposures_with_flip
    ):
        """Test flip detection when flip exists."""
        result = detector.detect_flip_level(
            symbol="SPY",
            current_price=Decimal("450.00"),
            gamma_exposures=gamma_exposures_with_flip
        )
        
        assert isinstance(result, GammaFlipLevel)
        assert result.symbol == "SPY"
        assert result.gamma_flip_strike is not None
        assert result.distance_to_flip is not None
    
    def test_detect_flip_level_no_flip(self, detector):
        """Test flip detection when no flip exists."""
        # All positive gamma
        exposures = [
            GammaExposure(
                strike=Decimal(f"{440 + i * 5}.00"),
                call_gamma=0.01,
                put_gamma=0.005,
                net_gamma=0.005,
                call_gex=1e9,
                put_gex=-0.5e9,
                net_gex=0.5e9,
                call_open_interest=5000,
                put_open_interest=3000
            )
            for i in range(5)
        ]
        
        result = detector.detect_flip_level(
            symbol="SPY",
            current_price=Decimal("450.00"),
            gamma_exposures=exposures
        )
        
        assert result.gamma_flip_strike is None
    
    def test_detect_flip_level_empty_exposures(self, detector):
        """Test flip detection with empty exposures."""
        result = detector.detect_flip_level(
            symbol="SPY",
            current_price=Decimal("450.00"),
            gamma_exposures=[]
        )
        
        assert result.market_regime == "neutral"
        assert result.gamma_flip_strike is None
    
    def test_is_near_flip_true(self, detector):
        """Test near flip detection when close."""
        flip = GammaFlipLevel(
            symbol="SPY",
            current_price=Decimal("450.00"),
            gamma_flip_strike=Decimal("455.00"),
            distance_to_flip=5.0,
            distance_pct=1.11,  # Within 5%
            market_regime="near_flip",
            timestamp=datetime.utcnow()
        )
        
        assert detector.is_approaching_flip(flip)
    
    def test_is_near_flip_false(self, detector):
        """Test near flip detection when far."""
        flip = GammaFlipLevel(
            symbol="SPY",
            current_price=Decimal("450.00"),
            gamma_flip_strike=Decimal("480.00"),
            distance_to_flip=30.0,
            distance_pct=6.67,  # Beyond 5%
            market_regime="positive_gamma",
            timestamp=datetime.utcnow()
        )
        
        assert not detector.is_approaching_flip(flip)
    
    def test_interpolate_flip_level(self, detector):
        """Test flip level interpolation."""
        exp1 = GammaExposure(
            strike=Decimal("445.00"),
            call_gamma=0.01,
            put_gamma=0.01,
            net_gamma=0.0,
            call_gex=0.5e9,
            put_gex=-1.0e9,
            net_gex=-0.5e9,
            call_open_interest=5000,
            put_open_interest=6000
        )
        
        exp2 = GammaExposure(
            strike=Decimal("450.00"),
            call_gamma=0.01,
            put_gamma=0.005,
            net_gamma=0.005,
            call_gex=1.5e9,
            put_gex=-0.5e9,
            net_gex=1.0e9,
            call_open_interest=7000,
            put_open_interest=3000
        )
        
        flip_strike = detector._interpolate_flip_level(exp1, exp2)
        
        assert flip_strike >= Decimal("445.00")
        assert flip_strike <= Decimal("450.00")
    
    def test_determine_regime_positive_gamma(self, detector):
        """Test regime determination for positive gamma."""
        exposures = [
            GammaExposure(
                strike=Decimal("445.00"),
                call_gamma=0.01,
                put_gamma=0.005,
                net_gamma=0.005,
                call_gex=1e9,
                put_gex=-0.5e9,
                net_gex=0.5e9,
                call_open_interest=5000,
                put_open_interest=3000
            ),
            GammaExposure(
                strike=Decimal("455.00"),
                call_gamma=0.01,
                put_gamma=0.005,
                net_gamma=0.005,
                call_gex=1e9,
                put_gex=-0.5e9,
                net_gex=0.5e9,
                call_open_interest=5000,
                put_open_interest=3000
            )
        ]
        
        regime = detector._determine_regime(
            current_price=Decimal("450.00"),
            sorted_exposures=exposures
        )
        
        assert regime == "positive_gamma"
    
    def test_determine_regime_negative_gamma(self, detector):
        """Test regime determination for negative gamma."""
        exposures = [
            GammaExposure(
                strike=Decimal("445.00"),
                call_gamma=0.01,
                put_gamma=0.015,
                net_gamma=-0.005,
                call_gex=0.5e9,
                put_gex=-1e9,
                net_gex=-0.5e9,
                call_open_interest=3000,
                put_open_interest=5000
            ),
            GammaExposure(
                strike=Decimal("455.00"),
                call_gamma=0.01,
                put_gamma=0.015,
                net_gamma=-0.005,
                call_gex=0.5e9,
                put_gex=-1e9,
                net_gex=-0.5e9,
                call_open_interest=3000,
                put_open_interest=5000
            )
        ]
        
        regime = detector._determine_regime(
            current_price=Decimal("450.00"),
            sorted_exposures=exposures
        )
        
        assert regime == "negative_gamma"
