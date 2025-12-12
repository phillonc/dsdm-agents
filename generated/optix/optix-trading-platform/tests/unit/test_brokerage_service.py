"""
Unit Tests for Brokerage Service
Tests brokerage connections and portfolio sync
"""
import pytest
from datetime import datetime
from decimal import Decimal
import uuid
from src.brokerage_service.models import (
    BrokerageConnection, Position, Transaction, Portfolio,
    BrokerageProvider, PositionType, ConnectionStatus, AccountType
)
from src.brokerage_service.repository import BrokerageRepository
from src.brokerage_service.sync_service import PortfolioSyncService


class TestBrokerageRepository:
    """Test brokerage repository"""
    
    @pytest.fixture
    def repo(self):
        return BrokerageRepository()
    
    @pytest.fixture
    def test_connection(self):
        return BrokerageConnection(
            user_id=uuid.uuid4(),
            provider=BrokerageProvider.SCHWAB,
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            account_id="12345678",
            account_name="Test Account",
            account_type=AccountType.MARGIN
        )
    
    def test_create_connection(self, repo, test_connection):
        """Test creating brokerage connection"""
        created = repo.create_connection(test_connection)
        
        assert created.id == test_connection.id
        assert created.provider == BrokerageProvider.SCHWAB
        assert created.status == ConnectionStatus.CONNECTED
    
    def test_get_connection(self, repo, test_connection):
        """Test getting connection by ID"""
        created = repo.create_connection(test_connection)
        retrieved = repo.get_connection(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
    
    def test_get_user_connections(self, repo, test_connection):
        """Test getting all user connections"""
        created = repo.create_connection(test_connection)
        connections = repo.get_user_connections(test_connection.user_id)
        
        assert len(connections) == 1
        assert connections[0].id == created.id
    
    def test_update_connection(self, repo, test_connection):
        """Test updating connection"""
        created = repo.create_connection(test_connection)
        
        updates = {
            "status": ConnectionStatus.ERROR,
            "sync_error": "Test error"
        }
        updated = repo.update_connection(created.id, updates)
        
        assert updated.status == ConnectionStatus.ERROR
        assert updated.sync_error == "Test error"
    
    def test_delete_connection(self, repo, test_connection):
        """Test deleting connection"""
        created = repo.create_connection(test_connection)
        
        result = repo.delete_connection(created.id)
        assert result is True
        
        retrieved = repo.get_connection(created.id)
        assert retrieved is None


class TestPortfolioSyncService:
    """Test portfolio sync service"""
    
    @pytest.fixture
    def sync_service(self):
        return PortfolioSyncService()
    
    @pytest.fixture
    def test_user_id(self):
        return uuid.uuid4()
    
    @pytest.fixture
    def sample_positions(self, test_user_id):
        connection_id = uuid.uuid4()
        return [
            Position(
                connection_id=connection_id,
                user_id=test_user_id,
                symbol="AAPL",
                position_type=PositionType.STOCK,
                quantity=Decimal("100"),
                average_price=Decimal("150.00"),
                cost_basis=Decimal("15000.00"),
                current_price=Decimal("155.00"),
                market_value=Decimal("15500.00"),
                unrealized_pl=Decimal("500.00"),
                unrealized_pl_percent=Decimal("3.33")
            ),
            Position(
                connection_id=connection_id,
                user_id=test_user_id,
                symbol="SPY",
                position_type=PositionType.OPTION,
                quantity=Decimal("10"),
                average_price=Decimal("5.00"),
                cost_basis=Decimal("5000.00"),
                current_price=Decimal("5.50"),
                market_value=Decimal("5500.00"),
                unrealized_pl=Decimal("500.00"),
                unrealized_pl_percent=Decimal("10.00"),
                option_symbol="SPY250117C00450000",
                strike=Decimal("450.00"),
                option_type="call",
                delta=Decimal("0.55"),
                gamma=Decimal("0.05"),
                theta=Decimal("-0.10"),
                vega=Decimal("0.15")
            )
        ]
    
    @pytest.mark.asyncio
    async def test_get_unified_portfolio(self, sync_service, test_user_id, sample_positions):
        """Test generating unified portfolio"""
        # Save positions
        sync_service.repo.save_positions(sample_positions)
        
        portfolio = await sync_service.get_unified_portfolio(test_user_id)
        
        assert portfolio.user_id == test_user_id
        assert portfolio.total_value == Decimal("21000.00")  # 15500 + 5500
        assert portfolio.total_unrealized_pl == Decimal("1000.00")
        assert len(portfolio.positions) == 2
    
    @pytest.mark.asyncio
    async def test_portfolio_greeks_aggregation(self, sync_service, test_user_id, sample_positions):
        """Test Greeks aggregation across positions"""
        sync_service.repo.save_positions(sample_positions)
        
        portfolio = await sync_service.get_unified_portfolio(test_user_id)
        
        # Greeks should be sum of (greeks * quantity) for options
        assert portfolio.total_delta == Decimal("5.50")  # 0.55 * 10
        assert portfolio.total_gamma == Decimal("0.50")  # 0.05 * 10
        assert portfolio.total_theta == Decimal("-1.00")  # -0.10 * 10
        assert portfolio.total_vega == Decimal("1.50")  # 0.15 * 10


class TestBrokerageModels:
    """Test brokerage models"""
    
    def test_brokerage_connection_model(self):
        """Test BrokerageConnection model"""
        connection = BrokerageConnection(
            user_id=uuid.uuid4(),
            provider=BrokerageProvider.SCHWAB,
            access_token="test_token",
            account_id="12345678"
        )
        
        assert connection.provider == BrokerageProvider.SCHWAB
        assert connection.status == ConnectionStatus.CONNECTED
        assert isinstance(connection.connected_at, datetime)
    
    def test_position_model(self):
        """Test Position model"""
        position = Position(
            connection_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            symbol="AAPL",
            position_type=PositionType.STOCK,
            quantity=Decimal("100"),
            average_price=Decimal("150.00"),
            cost_basis=Decimal("15000.00"),
            current_price=Decimal("155.00"),
            market_value=Decimal("15500.00"),
            unrealized_pl=Decimal("500.00"),
            unrealized_pl_percent=Decimal("3.33")
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        assert position.unrealized_pl == Decimal("500.00")
    
    def test_transaction_model(self):
        """Test Transaction model"""
        transaction = Transaction(
            connection_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            symbol="AAPL",
            transaction_type="buy",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("15000.00"),
            fees=Decimal("1.00"),
            transaction_date=datetime.utcnow()
        )
        
        assert transaction.symbol == "AAPL"
        assert transaction.transaction_type == "buy"
        assert transaction.fees == Decimal("1.00")
    
    def test_portfolio_model(self):
        """Test Portfolio model"""
        portfolio = Portfolio(
            user_id=uuid.uuid4(),
            total_value=Decimal("50000.00"),
            total_cash=Decimal("10000.00"),
            total_stocks_value=Decimal("30000.00"),
            total_options_value=Decimal("10000.00"),
            total_unrealized_pl=Decimal("5000.00"),
            total_unrealized_pl_percent=Decimal("11.11"),
            total_realized_pl=Decimal("2000.00"),
            day_pl=Decimal("500.00"),
            day_pl_percent=Decimal("1.00")
        )
        
        assert portfolio.total_value == Decimal("50000.00")
        assert portfolio.total_unrealized_pl == Decimal("5000.00")
        assert portfolio.risk_level == "moderate"
