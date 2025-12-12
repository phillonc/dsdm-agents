"""Unit tests for alert engine."""
import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta

from src.core.alert_engine import AlertEngine
from src.models.schemas import (
    GammaFlipLevel,
    GEXHeatmap,
    MarketMakerPosition,
    PinRiskAnalysis,
    GEXAlert,
)


class TestAlertEngine:
    """Test cases for AlertEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create alert engine instance."""
        return AlertEngine()
    
    @pytest.fixture
    def gamma_flip_near(self):
        """Create gamma flip near threshold."""
        return GammaFlipLevel(
            symbol="SPY",
            current_price=Decimal("450.00"),
            gamma_flip_strike=Decimal("463.50"),
            distance_to_flip=13.50,
            distance_pct=3.0,
            market_regime="near_flip",
            timestamp=datetime.utcnow()
        )
    
    @pytest.fixture
    def gamma_flip_far(self):
        """Create gamma flip far from threshold."""
        return GammaFlipLevel(
            symbol="SPY",
            current_price=Decimal("450.00"),
            gamma_flip_strike=Decimal("480.00"),
            distance_to_flip=30.00,
            distance_pct=6.67,
            market_regime="positive_gamma",
            timestamp=datetime.utcnow()
        )
    
    @pytest.fixture
    def high_gex_heatmap(self):
        """Create heatmap with high GEX."""
        return GEXHeatmap(
            symbol="SPY",
            spot_price=Decimal("450.00"),
            timestamp=datetime.utcnow(),
            strikes=[Decimal("450.00")],
            gex_values=[3e9],
            colors=["green"],
            total_call_gex=5e9,
            total_put_gex=-2e9,
            total_net_gex=3e9,
            max_gex_strike=Decimal("450.00"),
            min_gex_strike=Decimal("450.00")
        )
    
    @pytest.fixture
    def low_gex_heatmap(self):
        """Create heatmap with low GEX."""
        return GEXHeatmap(
            symbol="SPY",
            spot_price=Decimal("450.00"),
            timestamp=datetime.utcnow(),
            strikes=[Decimal("450.00")],
            gex_values=[0.5e9],
            colors=["green"],
            total_call_gex=0.8e9,
            total_put_gex=-0.3e9,
            total_net_gex=0.5e9,
            max_gex_strike=Decimal("450.00"),
            min_gex_strike=Decimal("450.00")
        )
    
    @pytest.fixture
    def high_pin_risk(self):
        """Create high pin risk analysis."""
        return PinRiskAnalysis(
            symbol="SPY",
            expiration=date.today() + timedelta(days=1),
            days_to_expiration=1,
            spot_price=Decimal("450.00"),
            high_oi_strikes=[Decimal("450.00")],
            pin_risk_strikes=[Decimal("450.00")],
            max_pain_strike=Decimal("450.00"),
            pin_risk_score=0.95,
            analysis_timestamp=datetime.utcnow()
        )
    
    @pytest.fixture
    def short_gamma_mm_position(self):
        """Create short gamma market maker position."""
        return MarketMakerPosition(
            symbol="SPY",
            dealer_gamma_exposure=-2e9,
            dealer_position="short_gamma",
            gamma_notional=2e9,
            vanna_exposure=1e6,
            charm_exposure=5e5,
            hedging_pressure="sell",
            timestamp=datetime.utcnow()
        )
    
    def test_check_gamma_flip_proximity_critical(
        self,
        engine,
        gamma_flip_near
    ):
        """Test gamma flip proximity alert - critical."""
        gamma_flip_near.distance_pct = 0.8
        
        alert = engine._check_gamma_flip_proximity("SPY", gamma_flip_near)
        
        assert alert is not None
        assert alert.alert_type == "gamma_flip_proximity"
        assert alert.severity == "critical"
    
    def test_check_gamma_flip_proximity_high(
        self,
        engine,
        gamma_flip_near
    ):
        """Test gamma flip proximity alert - high."""
        gamma_flip_near.distance_pct = 2.5
        
        alert = engine._check_gamma_flip_proximity("SPY", gamma_flip_near)
        
        assert alert is not None
        assert alert.severity == "high"
    
    def test_check_gamma_flip_proximity_no_alert(
        self,
        engine,
        gamma_flip_far
    ):
        """Test gamma flip proximity - no alert."""
        alert = engine._check_gamma_flip_proximity("SPY", gamma_flip_far)
        
        assert alert is None
    
    def test_check_gex_concentration_high(
        self,
        engine,
        high_gex_heatmap
    ):
        """Test high GEX concentration alert."""
        alert = engine._check_gex_concentration("SPY", high_gex_heatmap)
        
        assert alert is not None
        assert alert.alert_type == "high_gex_concentration"
        assert alert.severity in ["medium", "high", "critical"]
    
    def test_check_gex_concentration_low(
        self,
        engine,
        low_gex_heatmap
    ):
        """Test low GEX concentration - no alert."""
        alert = engine._check_gex_concentration("SPY", low_gex_heatmap)
        
        assert alert is None
    
    def test_check_pin_risk_high(
        self,
        engine,
        high_pin_risk
    ):
        """Test high pin risk alert."""
        alert = engine._check_pin_risk("SPY", high_pin_risk)
        
        assert alert is not None
        assert alert.alert_type == "pin_risk_warning"
        assert alert.severity in ["medium", "high", "critical"]
    
    def test_check_regime_change(self, engine):
        """Test regime change alert."""
        alert = engine._check_regime_change(
            symbol="SPY",
            previous_regime="positive_gamma",
            current_regime="negative_gamma"
        )
        
        assert alert is not None
        assert alert.alert_type == "regime_change"
    
    def test_check_regime_change_no_alert(self, engine):
        """Test regime change - no alert for minor change."""
        alert = engine._check_regime_change(
            symbol="SPY",
            previous_regime="positive_gamma",
            current_regime="positive_gamma"
        )
        
        assert alert is None
    
    def test_check_dealer_position_destabilizing(
        self,
        engine,
        short_gamma_mm_position
    ):
        """Test destabilizing dealer position alert."""
        alert = engine._check_dealer_position("SPY", short_gamma_mm_position)
        
        assert alert is not None
        assert alert.severity == "medium"
    
    def test_generate_alerts_comprehensive(
        self,
        engine,
        gamma_flip_near,
        high_gex_heatmap,
        short_gamma_mm_position,
        high_pin_risk
    ):
        """Test comprehensive alert generation."""
        alerts = engine.generate_alerts(
            symbol="SPY",
            gamma_flip=gamma_flip_near,
            heatmap=high_gex_heatmap,
            market_maker_position=short_gamma_mm_position,
            pin_risk=high_pin_risk,
            previous_regime="positive_gamma"
        )
        
        assert len(alerts) > 0
        assert all(isinstance(a, GEXAlert) for a in alerts)
    
    def test_get_regime_implication(self, engine):
        """Test regime implication messages."""
        implication = engine._get_regime_implication("positive_gamma")
        assert "dampen" in implication.lower()
        
        implication = engine._get_regime_implication("negative_gamma")
        assert "amplify" in implication.lower()
        
        implication = engine._get_regime_implication("near_flip")
        assert "inflection" in implication.lower() or "uncertainty" in implication.lower()
