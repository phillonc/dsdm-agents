"""
Unit tests for analytics engine.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Trade, TradeDirection, TradeStatus, SetupType
from src.analytics_engine import AnalyticsEngine


@pytest.fixture
def db_session():
    """Create in-memory database session for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def analytics_engine(db_session):
    """Create AnalyticsEngine instance."""
    return AnalyticsEngine(db_session)


@pytest.fixture
def sample_trades(db_session):
    """Create sample trades for testing."""
    trades = []
    base_date = datetime.utcnow() - timedelta(days=30)
    
    # Create winning and losing trades
    trade_configs = [
        {"symbol": "AAPL", "entry": 150, "exit": 155, "day": 0},
        {"symbol": "AAPL", "entry": 155, "exit": 160, "day": 1},
        {"symbol": "TSLA", "entry": 200, "exit": 195, "day": 2},
        {"symbol": "MSFT", "entry": 300, "exit": 310, "day": 3},
        {"symbol": "AAPL", "entry": 160, "exit": 165, "day": 4},
    ]
    
    for config in trade_configs:
        entry_date = base_date + timedelta(days=config["day"])
        exit_date = entry_date + timedelta(hours=2)
        
        pnl = (config["exit"] - config["entry"]) * 100
        
        trade = Trade(
            user_id="test_user",
            symbol=config["symbol"],
            direction=TradeDirection.LONG,
            status=TradeStatus.CLOSED,
            entry_date=entry_date,
            entry_price=config["entry"],
            exit_date=exit_date,
            exit_price=config["exit"],
            quantity=100,
            entry_commission=1.0,
            exit_commission=1.0,
            gross_pnl=pnl,
            net_pnl=pnl - 2.0
        )
        
        db_session.add(trade)
        trades.append(trade)
    
    db_session.commit()
    return trades


class TestAnalyticsEngine:
    """Tests for AnalyticsEngine."""
    
    def test_calculate_performance_metrics(self, analytics_engine, sample_trades):
        """Test calculating comprehensive performance metrics."""
        start_date = datetime.utcnow() - timedelta(days=31)
        end_date = datetime.utcnow()
        
        metrics = analytics_engine.calculate_performance_metrics(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        assert metrics['total_trades'] == 5
        assert metrics['winning_trades'] == 4
        assert metrics['losing_trades'] == 1
        assert metrics['win_rate'] == 80.0
        assert metrics['net_pnl'] > 0
    
    def test_empty_metrics(self, analytics_engine):
        """Test metrics for user with no trades."""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        metrics = analytics_engine.calculate_performance_metrics(
            user_id="nonexistent_user",
            start_date=start_date,
            end_date=end_date
        )
        
        assert metrics['total_trades'] == 0
        assert metrics['win_rate'] == 0.0
    
    def test_analyze_by_symbol(self, analytics_engine, sample_trades):
        """Test symbol analysis."""
        start_date = datetime.utcnow() - timedelta(days=31)
        end_date = datetime.utcnow()
        
        result = analytics_engine.analyze_by_symbol(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date,
            min_trades=2
        )
        
        assert 'by_symbol' in result
        assert 'AAPL' in result['by_symbol']
        assert result['by_symbol']['AAPL']['total_trades'] == 3
        assert result['most_profitable'] is not None
    
    def test_analyze_by_setup_type(self, analytics_engine, db_session):
        """Test setup type analysis."""
        base_date = datetime.utcnow() - timedelta(days=10)
        
        # Create trades with different setups
        for i, setup in enumerate([SetupType.BREAKOUT, SetupType.BREAKOUT, SetupType.PULLBACK]):
            trade = Trade(
                user_id="test_user",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                setup_type=setup,
                entry_date=base_date + timedelta(days=i),
                entry_price=150.0,
                exit_date=base_date + timedelta(days=i, hours=2),
                exit_price=155.0,
                quantity=100,
                net_pnl=500.0
            )
            db_session.add(trade)
        
        db_session.commit()
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        result = analytics_engine.analyze_by_setup_type(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        assert 'by_setup' in result
        assert 'BREAKOUT' in result['by_setup']
        assert result['by_setup']['BREAKOUT']['total_trades'] == 2
    
    def test_analyze_by_time_of_day(self, analytics_engine, sample_trades):
        """Test time of day analysis."""
        start_date = datetime.utcnow() - timedelta(days=31)
        end_date = datetime.utcnow()
        
        result = analytics_engine.analyze_by_time_of_day(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        assert 'by_hour' in result
        assert 'best_hours' in result
        assert 'worst_hours' in result
    
    def test_analyze_by_day_of_week(self, analytics_engine, sample_trades):
        """Test day of week analysis."""
        start_date = datetime.utcnow() - timedelta(days=31)
        end_date = datetime.utcnow()
        
        result = analytics_engine.analyze_by_day_of_week(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        assert 'by_day' in result
        assert isinstance(result['by_day'], dict)
    
    def test_generate_equity_curve(self, analytics_engine, sample_trades):
        """Test equity curve generation."""
        start_date = datetime.utcnow() - timedelta(days=31)
        end_date = datetime.utcnow()
        
        curve = analytics_engine.generate_equity_curve(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        assert isinstance(curve, list)
        assert len(curve) == 5
        assert 'cumulative_pnl' in curve[0]
        assert 'trade_pnl' in curve[0]
        
        # Check cumulative calculation
        for i in range(1, len(curve)):
            assert curve[i]['cumulative_pnl'] >= curve[i-1]['cumulative_pnl'] or curve[i]['trade_pnl'] < 0
    
    def test_calculate_monthly_performance(self, analytics_engine, db_session):
        """Test monthly performance calculation."""
        year = datetime.utcnow().year
        
        # Create trades across multiple months
        for month in [1, 2, 3]:
            for day in [1, 15]:
                trade = Trade(
                    user_id="test_user",
                    symbol="AAPL",
                    direction=TradeDirection.LONG,
                    status=TradeStatus.CLOSED,
                    entry_date=datetime(year, month, day, 10, 0),
                    entry_price=150.0,
                    exit_date=datetime(year, month, day, 12, 0),
                    exit_price=155.0,
                    quantity=100,
                    net_pnl=500.0
                )
                db_session.add(trade)
        
        db_session.commit()
        
        result = analytics_engine.calculate_monthly_performance(
            user_id="test_user",
            year=year
        )
        
        assert result['year'] == year
        assert 'monthly' in result
        assert 'yearly_total' in result
        assert result['monthly']['January']['total_trades'] == 2
    
    def test_max_drawdown_calculation(self, analytics_engine, db_session):
        """Test maximum drawdown calculation."""
        base_date = datetime.utcnow() - timedelta(days=10)
        
        # Create trades with varying P&L to create drawdown
        pnls = [1000, -500, -300, 500, 1000, -800]
        
        for i, pnl in enumerate(pnls):
            trade = Trade(
                user_id="test_user",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                entry_date=base_date + timedelta(days=i),
                entry_price=150.0,
                exit_date=base_date + timedelta(days=i, hours=2),
                exit_price=155.0 if pnl > 0 else 145.0,
                quantity=100,
                net_pnl=pnl
            )
            db_session.add(trade)
        
        db_session.commit()
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        metrics = analytics_engine.calculate_performance_metrics(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        assert metrics['max_drawdown'] > 0
    
    def test_streak_calculation(self, analytics_engine, db_session):
        """Test win/loss streak calculation."""
        base_date = datetime.utcnow() - timedelta(days=10)
        
        # Create alternating wins and losses with streaks
        pnls = [100, 200, 150, -50, -100, 300, 250, 200]
        
        for i, pnl in enumerate(pnls):
            trade = Trade(
                user_id="test_user",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                entry_date=base_date + timedelta(days=i),
                entry_price=150.0,
                exit_date=base_date + timedelta(days=i, hours=1),
                exit_price=155.0 if pnl > 0 else 145.0,
                quantity=100,
                net_pnl=pnl
            )
            db_session.add(trade)
        
        db_session.commit()
        
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        metrics = analytics_engine.calculate_performance_metrics(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        assert metrics['max_win_streak'] == 3  # First 3 wins
        assert metrics['max_loss_streak'] == 2  # 2 losses in middle
    
    def test_performance_with_filters(self, analytics_engine, sample_trades):
        """Test performance metrics with filters."""
        start_date = datetime.utcnow() - timedelta(days=31)
        end_date = datetime.utcnow()
        
        # Filter by symbol
        metrics = analytics_engine.calculate_performance_metrics(
            user_id="test_user",
            start_date=start_date,
            end_date=end_date,
            filters={'symbol': 'AAPL'}
        )
        
        assert metrics['total_trades'] == 3  # Only AAPL trades
    
    def test_save_performance_metric(self, analytics_engine):
        """Test saving calculated metrics to database."""
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        metrics_data = {
            'total_trades': 10,
            'winning_trades': 6,
            'losing_trades': 4,
            'win_rate': 60.0,
            'net_pnl': 1000.0,
            'average_pnl': 100.0,
            'largest_win': 500.0,
            'largest_loss': -200.0,
            'profit_factor': 2.5,
            'expectancy': 100.0
        }
        
        saved_metric = analytics_engine.save_performance_metric(
            user_id="test_user",
            metric_type="by_symbol",
            metric_key="AAPL",
            period_start=start_date,
            period_end=end_date,
            metrics_data=metrics_data
        )
        
        assert saved_metric.id is not None
        assert saved_metric.metric_type == "by_symbol"
        assert saved_metric.metric_key == "AAPL"
        assert saved_metric.win_rate == 60.0
