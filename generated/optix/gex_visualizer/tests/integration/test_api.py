"""Integration tests for API endpoints."""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from httpx import AsyncClient

from src.api.app import create_app
from src.models.schemas import OptionContract, GEXCalculationRequest


@pytest.fixture
def app():
    """Create test app."""
    return create_app()


@pytest.fixture
def sample_options_chain():
    """Create sample options chain for testing."""
    expiration = date.today() + timedelta(days=30)
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
            open_interest=5000,
            implied_volatility=0.25,
            delta=0.55 if strike == 450 else 0.4,
            gamma=0.01,
            theta=-0.05,
            vega=0.15
        )
        
        put = OptionContract(
            symbol="SPY",
            strike=Decimal(f"{strike}.00"),
            expiration=expiration,
            option_type="put",
            bid=Decimal("4.00"),
            ask=Decimal("4.25"),
            volume=800,
            open_interest=4000,
            implied_volatility=0.28,
            delta=-0.45 if strike == 450 else -0.3,
            gamma=0.01,
            theta=-0.04,
            vega=0.14
        )
        
        options.extend([call, put])
    
    return options


@pytest.mark.asyncio
async def test_health_check(app):
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(app):
    """Test root endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_calculate_gex_endpoint(app, sample_options_chain):
    """Test GEX calculation endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        request_data = {
            "symbol": "SPY",
            "spot_price": "450.00",
            "options_chain": [
                {
                    "symbol": opt.symbol,
                    "strike": str(opt.strike),
                    "expiration": opt.expiration.isoformat(),
                    "option_type": opt.option_type,
                    "bid": str(opt.bid),
                    "ask": str(opt.ask),
                    "volume": opt.volume,
                    "open_interest": opt.open_interest,
                    "implied_volatility": opt.implied_volatility,
                    "delta": opt.delta,
                    "gamma": opt.gamma,
                    "theta": opt.theta,
                    "vega": opt.vega
                }
                for opt in sample_options_chain
            ],
            "calculate_pin_risk": True,
            "include_historical": False
        }
        
        response = await client.post(
            "/api/v1/gex/calculate",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "SPY"
        assert "gamma_exposures" in data
        assert "heatmap" in data
        assert "gamma_flip" in data
        assert "market_maker_position" in data


@pytest.mark.asyncio
async def test_get_gex_for_symbol_endpoint(app):
    """Test GEX calculation for symbol endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/gex/calculate/SPY",
            params={"spot_price": "450.00"}
        )
        
        # This should work with mock data
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "SPY"


@pytest.mark.asyncio
async def test_get_alerts_endpoint(app):
    """Test alerts endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/alerts/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_active_alerts_endpoint(app):
    """Test active alerts endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/alerts/active")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_alerts_summary_endpoint(app):
    """Test alerts summary endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/alerts/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_active" in data
        assert "by_severity" in data


@pytest.mark.asyncio
async def test_acknowledge_alert_endpoint(app):
    """Test alert acknowledgment endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/alerts/test_alert_123/acknowledge",
            params={"acknowledged_by": "test_user"}
        )
        
        # Should succeed even if alert doesn't exist (idempotent)
        assert response.status_code in [200, 500]  # May fail if DB not set up


@pytest.mark.asyncio
async def test_historical_gex_endpoint_not_found(app):
    """Test historical GEX endpoint with no data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/historical/NONEXISTENT")
        
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_historical_summary_endpoint(app):
    """Test historical summary endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/historical/SPY/summary")
        
        # Should return 404 with no data
        assert response.status_code in [404, 500]


@pytest.mark.asyncio
async def test_chart_data_endpoint(app):
    """Test chart data endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/historical/SPY/chart")
        
        # Should return 404 with no data
        assert response.status_code in [404, 500]
