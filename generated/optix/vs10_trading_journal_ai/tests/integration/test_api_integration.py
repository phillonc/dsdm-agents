"""
Integration tests for API endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import app, get_db
from src.models import Base, TradeDirection, SetupType


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    """Create test client with overridden database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


class TestTradeEndpoints:
    """Integration tests for trade endpoints."""
    
    def test_create_trade(self, client):
        """Test creating a trade via API."""
        trade_data = {
            "user_id": "test_user",
            "symbol": "AAPL",
            "direction": "LONG",
            "entry_date": datetime.utcnow().isoformat(),
            "entry_price": 150.50,
            "quantity": 100,
            "entry_commission": 1.50
        }
        
        response = client.post("/api/v1/trades", json=trade_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["direction"] == "LONG"
        assert data["status"] == "OPEN"
    
    def test_get_trades(self, client):
        """Test retrieving trades via API."""
        # Create a trade first
        trade_data = {
            "user_id": "test_user",
            "symbol": "TSLA",
            "direction": "LONG",
            "entry_date": datetime.utcnow().isoformat(),
            "entry_price": 200.00,
            "quantity": 50
        }
        client.post("/api/v1/trades", json=trade_data)
        
        # Get trades
        response = client.get("/api/v1/trades", params={"user_id": "test_user"})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["symbol"] == "TSLA"
    
    def test_close_trade(self, client):
        """Test closing a trade via API."""
        # Create a trade
        trade_data = {
            "user_id": "test_user",
            "symbol": "AAPL",
            "direction": "LONG",
            "entry_date": datetime.utcnow().isoformat(),
            "entry_price": 150.00,
            "quantity": 100
        }
        create_response = client.post("/api/v1/trades", json=trade_data)
        trade_id = create_response.json()["id"]
        
        # Close the trade
        close_data = {
            "exit_price": 155.00,
            "exit_date": datetime.utcnow().isoformat(),
            "exit_commission": 1.50
        }
        response = client.put(f"/api/v1/trades/{trade_id}/close", params=close_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CLOSED"
        assert data["exit_price"] == 155.00
        assert data["net_pnl"] is not None
    
    def test_filter_trades_by_symbol(self, client):
        """Test filtering trades by symbol."""
        # Create multiple trades
        for symbol in ["AAPL", "TSLA", "AAPL"]:
            trade_data = {
                "user_id": "test_user",
                "symbol": symbol,
                "direction": "LONG",
                "entry_date": datetime.utcnow().isoformat(),
                "entry_price": 150.00,
                "quantity": 100
            }
            client.post("/api/v1/trades", json=trade_data)
        
        # Filter by AAPL
        response = client.get(
            "/api/v1/trades",
            params={"user_id": "test_user", "symbol": "AAPL"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(t["symbol"] == "AAPL" for t in data)


class TestJournalEndpoints:
    """Integration tests for journal endpoints."""
    
    def test_create_journal_entry(self, client):
        """Test creating a journal entry via API."""
        entry_data = {
            "user_id": "test_user",
            "title": "Great trading day",
            "content": "Followed my plan perfectly.",
            "mood_rating": 8,
            "confidence_level": 9,
            "discipline_rating": 10,
            "entry_date": datetime.utcnow().isoformat()
        }
        
        response = client.post("/api/v1/journal", json=entry_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Great trading day"
        assert data["mood_rating"] == 8
    
    def test_get_journal_entries(self, client):
        """Test retrieving journal entries via API."""
        # Create an entry
        entry_data = {
            "user_id": "test_user",
            "title": "Test entry",
            "content": "Test content",
            "entry_date": datetime.utcnow().isoformat()
        }
        client.post("/api/v1/journal", json=entry_data)
        
        # Get entries
        response = client.get("/api/v1/journal", params={"user_id": "test_user"})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
    
    def test_search_journal_entries(self, client):
        """Test searching journal entries via API."""
        # Create entries with different content
        entries = [
            {"user_id": "test_user", "content": "Great AAPL trade", "entry_date": datetime.utcnow().isoformat()},
            {"user_id": "test_user", "content": "Lost on TSLA", "entry_date": datetime.utcnow().isoformat()},
            {"user_id": "test_user", "content": "Another AAPL winner", "entry_date": datetime.utcnow().isoformat()}
        ]
        
        for entry in entries:
            client.post("/api/v1/journal", json=entry)
        
        # Search for AAPL
        response = client.get(
            "/api/v1/journal/search",
            params={"user_id": "test_user", "query": "AAPL"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestAnalyticsEndpoints:
    """Integration tests for analytics endpoints."""
    
    def test_get_performance_analytics(self, client):
        """Test getting performance analytics via API."""
        # Create and close a trade
        trade_data = {
            "user_id": "test_user",
            "symbol": "AAPL",
            "direction": "LONG",
            "entry_date": datetime.utcnow().isoformat(),
            "entry_price": 150.00,
            "quantity": 100
        }
        create_response = client.post("/api/v1/trades", json=trade_data)
        trade_id = create_response.json()["id"]
        
        client.put(
            f"/api/v1/trades/{trade_id}/close",
            params={
                "exit_price": 155.00,
                "exit_date": datetime.utcnow().isoformat()
            }
        )
        
        # Get analytics
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = client.get(
            "/api/v1/analytics/performance",
            params={
                "user_id": "test_user",
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_trades" in data
        assert "win_rate" in data
        assert "net_pnl" in data
    
    def test_get_symbol_analytics(self, client):
        """Test getting analytics by symbol via API."""
        # Create multiple trades on different symbols
        for symbol in ["AAPL", "TSLA", "MSFT"]:
            for i in range(3):
                trade_data = {
                    "user_id": "test_user",
                    "symbol": symbol,
                    "direction": "LONG",
                    "entry_date": datetime.utcnow().isoformat(),
                    "entry_price": 150.00 + i,
                    "quantity": 100
                }
                create_response = client.post("/api/v1/trades", json=trade_data)
                trade_id = create_response.json()["id"]
                
                # Close trade
                client.put(
                    f"/api/v1/trades/{trade_id}/close",
                    params={
                        "exit_price": 155.00 + i,
                        "exit_date": datetime.utcnow().isoformat()
                    }
                )
        
        # Get symbol analytics
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = client.get(
            "/api/v1/analytics/by-symbol",
            params={
                "user_id": "test_user",
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "by_symbol" in data
        assert "AAPL" in data["by_symbol"]
        assert "TSLA" in data["by_symbol"]
    
    def test_get_equity_curve(self, client):
        """Test getting equity curve via API."""
        # Create multiple closed trades
        for i in range(5):
            trade_data = {
                "user_id": "test_user",
                "symbol": "AAPL",
                "direction": "LONG",
                "entry_date": datetime.utcnow().isoformat(),
                "entry_price": 150.00,
                "quantity": 100
            }
            create_response = client.post("/api/v1/trades", json=trade_data)
            trade_id = create_response.json()["id"]
            
            client.put(
                f"/api/v1/trades/{trade_id}/close",
                params={
                    "exit_price": 155.00 if i % 2 == 0 else 145.00,
                    "exit_date": datetime.utcnow().isoformat()
                }
            )
        
        # Get equity curve
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = client.get(
            "/api/v1/analytics/equity-curve",
            params={
                "user_id": "test_user",
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "equity_curve" in data
        assert len(data["equity_curve"]) == 5


class TestPatternEndpoints:
    """Integration tests for pattern analysis endpoints."""
    
    def test_detect_behavioral_patterns(self, client):
        """Test detecting behavioral patterns via API."""
        # Create some trades
        for i in range(5):
            trade_data = {
                "user_id": "test_user",
                "symbol": "AAPL",
                "direction": "LONG",
                "entry_date": datetime.utcnow().isoformat(),
                "entry_price": 150.00,
                "quantity": 100
            }
            create_response = client.post("/api/v1/trades", json=trade_data)
            trade_id = create_response.json()["id"]
            
            client.put(
                f"/api/v1/trades/{trade_id}/close",
                params={
                    "exit_price": 155.00,
                    "exit_date": datetime.utcnow().isoformat()
                }
            )
        
        response = client.get(
            "/api/v1/patterns/behavioral",
            params={"user_id": "test_user", "lookback_days": 30}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "patterns" in data
        assert "warnings" in data


class TestHealthCheck:
    """Integration tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "trading-journal-ai"
