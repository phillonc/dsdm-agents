"""
Unit tests for alert engine.
"""
import pytest
from datetime import datetime, timedelta

from src.alert_engine import VolatilityAlertEngine
from src.models import VolatilityMetrics, VolatilityCondition


class TestVolatilityAlertEngine:
    """Tests for Volatility Alert Engine."""
    
    def setup_method(self):
        self.engine = VolatilityAlertEngine()
    
    def create_test_metrics(self, iv=30.0, iv_rank=50, iv_percentile=50, iv_hv_ratio=1.0):
        """Helper to create test metrics."""
        return VolatilityMetrics(
            symbol="AAPL",
            timestamp=datetime.now(),
            current_iv=iv,
            iv_rank=iv_rank,
            iv_percentile=iv_percentile,
            historical_volatility_30d=25.0,
            historical_volatility_60d=26.0,
            historical_volatility_90d=27.0,
            iv_hv_ratio=iv_hv_ratio,
            condition=VolatilityCondition.NORMAL,
            average_iv_30d=28.0,
            average_iv_60d=29.0,
            min_iv_52w=20.0,
            max_iv_52w=45.0
        )
    
    def test_check_iv_spike(self):
        """Test IV spike detection."""
        alert = self.engine._check_iv_spike("AAPL", current_iv=36.0, previous_iv=30.0)
        
        assert alert is not None
        assert alert.alert_type == "iv_spike"
        assert alert.change_percent == 20.0
        assert alert.severity in ["low", "medium", "high", "critical"]
    
    def test_check_iv_spike_no_alert(self):
        """Test that small IV increase doesn't trigger alert."""
        alert = self.engine._check_iv_spike("AAPL", current_iv=31.0, previous_iv=30.0)
        
        assert alert is None
    
    def test_check_iv_spike_large_increase(self):
        """Test large IV spike gets high severity."""
        alert = self.engine._check_iv_spike("AAPL", current_iv=50.0, previous_iv=30.0)
        
        assert alert is not None
        assert alert.severity in ["high", "critical"]
        assert alert.change_percent > 50
    
    def test_check_iv_crush(self):
        """Test IV crush detection."""
        alert = self.engine._check_iv_crush("AAPL", current_iv=24.0, previous_iv=30.0)
        
        assert alert is not None
        assert alert.alert_type == "iv_crush"
        assert alert.change_percent == 20.0
    
    def test_check_iv_crush_no_alert(self):
        """Test that small IV decrease doesn't trigger alert."""
        alert = self.engine._check_iv_crush("AAPL", current_iv=29.0, previous_iv=30.0)
        
        assert alert is None
    
    def test_check_iv_rank_high_threshold(self):
        """Test high IV rank threshold alert."""
        metrics = self.create_test_metrics(iv_rank=85, iv_percentile=90)
        
        alerts = self.engine._check_iv_rank_thresholds("AAPL", metrics)
        
        assert len(alerts) > 0
        assert alerts[0].alert_type == "rank_threshold"
        assert "selling" in alerts[0].message.lower()
    
    def test_check_iv_rank_low_threshold(self):
        """Test low IV rank threshold alert."""
        metrics = self.create_test_metrics(iv_rank=15, iv_percentile=18)
        
        alerts = self.engine._check_iv_rank_thresholds("AAPL", metrics)
        
        assert len(alerts) > 0
        assert alerts[0].alert_type == "rank_threshold"
        assert "buying" in alerts[0].message.lower()
    
    def test_check_iv_rank_no_alert(self):
        """Test that mid-range IV rank doesn't trigger alert."""
        metrics = self.create_test_metrics(iv_rank=50, iv_percentile=50)
        
        alerts = self.engine._check_iv_rank_thresholds("AAPL", metrics)
        
        assert len(alerts) == 0
    
    def test_check_iv_hv_divergence(self):
        """Test IV/HV divergence alert."""
        metrics = self.create_test_metrics(iv_hv_ratio=1.6)
        
        alert = self.engine._check_iv_hv_divergence("AAPL", metrics)
        
        assert alert is not None
        assert alert.alert_type == "iv_hv_divergence"
        assert "overpriced" in alert.message.lower()
    
    def test_check_iv_hv_divergence_no_alert(self):
        """Test that normal IV/HV ratio doesn't trigger alert."""
        metrics = self.create_test_metrics(iv_hv_ratio=1.2)
        
        alert = self.engine._check_iv_hv_divergence("AAPL", metrics)
        
        assert alert is None
    
    def test_check_historical_extreme_near_high(self):
        """Test alert for IV near 52-week high."""
        metrics = self.create_test_metrics(iv=44.0)  # max_iv_52w is 45.0
        
        alerts = self.engine._check_historical_extremes("AAPL", metrics)
        
        assert len(alerts) > 0
        assert "52-week high" in alerts[0].message
    
    def test_check_historical_extreme_near_low(self):
        """Test alert for IV near 52-week low."""
        metrics = self.create_test_metrics(iv=20.5)  # min_iv_52w is 20.0
        
        alerts = self.engine._check_historical_extremes("AAPL", metrics)
        
        assert len(alerts) > 0
        assert "52-week low" in alerts[0].message
    
    def test_check_historical_extreme_no_alert(self):
        """Test no alert for IV in middle range."""
        metrics = self.create_test_metrics(iv=30.0)
        
        alerts = self.engine._check_historical_extremes("AAPL", metrics)
        
        assert len(alerts) == 0
    
    def test_check_alerts_comprehensive(self):
        """Test comprehensive alert checking."""
        metrics = self.create_test_metrics(iv=36.0, iv_rank=85, iv_hv_ratio=1.6)
        
        alerts = self.engine.check_alerts(
            symbol="AAPL",
            current_metrics=metrics,
            previous_iv=30.0
        )
        
        # Should trigger multiple alerts
        assert len(alerts) > 0
        alert_types = [a.alert_type for a in alerts]
        assert "iv_spike" in alert_types
        assert "rank_threshold" in alert_types
    
    def test_alert_history_storage(self):
        """Test that alerts are stored in history."""
        metrics = self.create_test_metrics(iv=36.0, iv_rank=85)
        
        alerts = self.engine.check_alerts(
            symbol="AAPL",
            current_metrics=metrics,
            previous_iv=30.0
        )
        
        assert "AAPL" in self.engine.alert_history
        assert len(self.engine.alert_history["AAPL"]) > 0
    
    def test_get_alert_summary(self):
        """Test alert summary generation."""
        metrics = self.create_test_metrics(iv=36.0, iv_rank=85)
        
        # Generate some alerts
        self.engine.check_alerts(
            symbol="AAPL",
            current_metrics=metrics,
            previous_iv=30.0
        )
        
        summary = self.engine.get_alert_summary("AAPL", hours=24)
        
        assert 'total_alerts' in summary
        assert 'by_severity' in summary
        assert 'by_type' in summary
        assert 'recent_alerts' in summary
        assert summary['total_alerts'] > 0
    
    def test_get_alert_summary_no_alerts(self):
        """Test alert summary for symbol with no alerts."""
        summary = self.engine.get_alert_summary("XYZ", hours=24)
        
        assert summary['total_alerts'] == 0
        assert summary['by_severity'] == {}
        assert summary['by_type'] == {}
    
    def test_clear_old_alerts(self):
        """Test clearing old alerts."""
        metrics = self.create_test_metrics(iv=36.0, iv_rank=85)
        
        # Add alert
        self.engine.check_alerts(
            symbol="AAPL",
            current_metrics=metrics,
            previous_iv=30.0
        )
        
        initial_count = len(self.engine.alert_history["AAPL"])
        
        # Clear old alerts (should keep recent ones)
        self.engine.clear_old_alerts("AAPL", days=30)
        
        # Recent alerts should still be there
        assert len(self.engine.alert_history["AAPL"]) == initial_count
        
        # Clear with 0 days should remove all
        self.engine.clear_old_alerts("AAPL", days=0)
        assert len(self.engine.alert_history["AAPL"]) == 0
    
    def test_update_thresholds(self):
        """Test updating alert thresholds."""
        original_spike_threshold = self.engine.thresholds['iv_spike_percent']
        
        self.engine.update_thresholds({
            'iv_spike_percent': 30.0,
            'iv_rank_high': 75.0
        })
        
        assert self.engine.thresholds['iv_spike_percent'] == 30.0
        assert self.engine.thresholds['iv_rank_high'] == 75.0
        assert self.engine.thresholds['iv_spike_percent'] != original_spike_threshold
    
    def test_calculate_severity_levels(self):
        """Test severity calculation."""
        assert self.engine._calculate_severity(15, 20, 40, 60) == "low"
        assert self.engine._calculate_severity(35, 20, 40, 60) == "medium"
        assert self.engine._calculate_severity(55, 20, 40, 60) == "high"
        assert self.engine._calculate_severity(75, 20, 40, 60) == "critical"
    
    def test_alert_has_required_fields(self):
        """Test that alerts contain all required fields."""
        metrics = self.create_test_metrics(iv=36.0)
        
        alerts = self.engine.check_alerts(
            symbol="AAPL",
            current_metrics=metrics,
            previous_iv=30.0
        )
        
        if alerts:
            alert = alerts[0]
            assert hasattr(alert, 'alert_id')
            assert hasattr(alert, 'symbol')
            assert hasattr(alert, 'timestamp')
            assert hasattr(alert, 'alert_type')
            assert hasattr(alert, 'severity')
            assert hasattr(alert, 'message')
            assert hasattr(alert, 'current_value')
            assert hasattr(alert, 'previous_value')
            assert hasattr(alert, 'change_percent')
            assert hasattr(alert, 'threshold')
            assert len(alert.alert_id) > 0
            assert alert.symbol == "AAPL"
