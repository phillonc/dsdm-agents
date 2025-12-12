"""
Integration tests for FastAPI endpoints
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from src.api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_backtest_config():
    """Sample backtest configuration"""
    return {
        "initial_capital": 100000,
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-01-31T00:00:00",
        "symbols": ["SPY"],
        "transaction_costs": {
            "commission_per_contract": 0.65,
            "slippage_percent": 0.1,
            "spread_cost_percent": 50.0
        },
        "max_position_size": 10,
        "max_positions": 5,
        "data_frequency": "1day"
    }


class TestRootEndpoints:
    """Test root endpoints"""
    
    def test_root(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestBacktestEndpoints:
    """Test backtest endpoints"""
    
    def test_create_backtest(self, client, sample_backtest_config):
        """Test creating backtest"""
        response = client.post(
            "/api/v1/backtest",
            json=sample_backtest_config
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "backtest_id" in data
        assert data["status"] in ["running", "completed"]
    
    def test_get_backtest(self, client, sample_backtest_config):
        """Test getting backtest by ID"""
        # Create backtest
        create_response = client.post(
            "/api/v1/backtest",
            json=sample_backtest_config
        )
        backtest_id = create_response.json()["backtest_id"]
        
        # Get backtest
        response = client.get(f"/api/v1/backtest/{backtest_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["backtest_id"] == backtest_id
    
    def test_get_nonexistent_backtest(self, client):
        """Test getting non-existent backtest"""
        response = client.get("/api/v1/backtest/nonexistent-id")
        assert response.status_code == 404
    
    def test_list_backtests(self, client, sample_backtest_config):
        """Test listing backtests"""
        # Create some backtests
        for _ in range(3):
            client.post("/api/v1/backtest", json=sample_backtest_config)
        
        # List backtests
        response = client.get("/api/v1/backtests")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
    
    def test_list_backtests_with_filter(self, client, sample_backtest_config):
        """Test listing backtests with status filter"""
        response = client.get("/api/v1/backtests?status=completed&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_delete_backtest(self, client, sample_backtest_config):
        """Test deleting backtest"""
        # Create backtest
        create_response = client.post(
            "/api/v1/backtest",
            json=sample_backtest_config
        )
        backtest_id = create_response.json()["backtest_id"]
        
        # Delete backtest
        response = client.delete(f"/api/v1/backtest/{backtest_id}")
        assert response.status_code == 200
        
        # Verify deleted
        get_response = client.get(f"/api/v1/backtest/{backtest_id}")
        assert get_response.status_code == 404
    
    def test_get_performance_metrics(self, client, sample_backtest_config):
        """Test getting performance metrics"""
        # Create backtest
        create_response = client.post(
            "/api/v1/backtest",
            json=sample_backtest_config
        )
        backtest_id = create_response.json()["backtest_id"]
        
        # Get performance
        response = client.get(f"/api/v1/backtest/{backtest_id}/performance")
        assert response.status_code == 200
        data = response.json()
        assert "performance" in data
        assert "summary" in data
    
    def test_get_trades(self, client, sample_backtest_config):
        """Test getting trades"""
        # Create backtest
        create_response = client.post(
            "/api/v1/backtest",
            json=sample_backtest_config
        )
        backtest_id = create_response.json()["backtest_id"]
        
        # Get trades
        response = client.get(f"/api/v1/backtest/{backtest_id}/trades")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data
        assert "total_trades" in data
    
    def test_get_equity_curve(self, client, sample_backtest_config):
        """Test getting equity curve"""
        # Create backtest
        create_response = client.post(
            "/api/v1/backtest",
            json=sample_backtest_config
        )
        backtest_id = create_response.json()["backtest_id"]
        
        # Get equity curve
        response = client.get(f"/api/v1/backtest/{backtest_id}/equity-curve")
        assert response.status_code == 200
        data = response.json()
        assert "equity_curve" in data


class TestMonteCarloEndpoints:
    """Test Monte Carlo endpoints"""
    
    def test_run_monte_carlo(self, client, sample_backtest_config):
        """Test running Monte Carlo simulation"""
        # Create backtest
        create_response = client.post(
            "/api/v1/backtest",
            json=sample_backtest_config
        )
        backtest_id = create_response.json()["backtest_id"]
        
        # Run Monte Carlo
        response = client.post(
            f"/api/v1/backtest/{backtest_id}/monte-carlo?iterations=100&method=bootstrap"
        )
        assert response.status_code == 200
        data = response.json()
        assert "simulation_id" in data
        assert data["iterations"] == 100
        assert "mean_return" in data
    
    def test_monte_carlo_different_methods(self, client, sample_backtest_config):
        """Test Monte Carlo with different methods"""
        # Create backtest
        create_response = client.post(
            "/api/v1/backtest",
            json=sample_backtest_config
        )
        backtest_id = create_response.json()["backtest_id"]
        
        methods = ["bootstrap", "resample", "parametric"]
        
        for method in methods:
            response = client.post(
                f"/api/v1/backtest/{backtest_id}/monte-carlo?iterations=50&method={method}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["iterations"] == 50


class TestOptimizationEndpoints:
    """Test optimization endpoints"""
    
    def test_walk_forward_optimization(self, client, sample_backtest_config):
        """Test walk-forward optimization"""
        # Prepare optimization request
        optimization_request = {
            **sample_backtest_config,
            "param_grid": {
                "entry_threshold": [0.01, 0.02, 0.03],
                "exit_profit_target": [0.15, 0.20, 0.25]
            }
        }
        
        response = client.post(
            "/api/v1/optimize/walk-forward?num_periods=3&train_ratio=0.7",
            json=optimization_request
        )
        
        # This might take time, so status could be running or completed
        assert response.status_code == 200
        data = response.json()
        assert "optimization_id" in data
        assert "total_periods" in data
    
    def test_get_optimization(self, client, sample_backtest_config):
        """Test getting optimization result"""
        # Run optimization
        optimization_request = {
            **sample_backtest_config,
            "param_grid": {
                "entry_threshold": [0.02]
            }
        }
        
        create_response = client.post(
            "/api/v1/optimize/walk-forward?num_periods=2",
            json=optimization_request
        )
        optimization_id = create_response.json()["optimization_id"]
        
        # Get optimization
        response = client.get(f"/api/v1/optimize/{optimization_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["optimization_id"] == optimization_id


class TestComparisonEndpoints:
    """Test comparison endpoints"""
    
    def test_compare_backtests(self, client, sample_backtest_config):
        """Test comparing multiple backtests"""
        # Create multiple backtests
        backtest_ids = []
        for _ in range(3):
            response = client.post(
                "/api/v1/backtest",
                json=sample_backtest_config
            )
            backtest_ids.append(response.json()["backtest_id"])
        
        # Compare backtests
        response = client.post(
            "/api/v1/backtest/compare",
            json=backtest_ids
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "comparison_count" in data
        assert "backtests" in data
        assert data["comparison_count"] == 3
    
    def test_compare_empty_list(self, client):
        """Test comparing with empty list"""
        response = client.post(
            "/api/v1/backtest/compare",
            json=[]
        )
        assert response.status_code == 400


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_config(self, client):
        """Test backtest with invalid configuration"""
        invalid_config = {
            "initial_capital": -1000,  # Invalid negative capital
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-31T00:00:00",
            "symbols": []
        }
        
        response = client.post("/api/v1/backtest", json=invalid_config)
        assert response.status_code in [400, 422]
    
    def test_missing_required_fields(self, client):
        """Test backtest with missing required fields"""
        incomplete_config = {
            "initial_capital": 100000
            # Missing other required fields
        }
        
        response = client.post("/api/v1/backtest", json=incomplete_config)
        assert response.status_code == 422
    
    def test_invalid_date_range(self, client):
        """Test backtest with invalid date range"""
        invalid_config = {
            "initial_capital": 100000,
            "start_date": "2024-12-31T00:00:00",
            "end_date": "2024-01-01T00:00:00",  # End before start
            "symbols": ["SPY"]
        }
        
        response = client.post("/api/v1/backtest", json=invalid_config)
        # Should either fail validation or return error in result
        assert response.status_code in [400, 422, 500] or response.json().get("status") == "failed"
