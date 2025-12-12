"""
Unit tests for pattern analyzer.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import (
    Base, Trade, TradeDirection, TradeStatus, 
    SetupType, MarketCondition, Sentiment
)
from src.pattern_analyzer import PatternAnalyzer


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
def pattern_analyzer(db_session):
    """Create PatternAnalyzer instance."""
    return PatternAnalyzer(db_session)


@pytest.fixture
def sample_trades(db_session):
    """Create sample trades for testing."""
    trades = []
    base_date = datetime.utcnow() - timedelta(days=30)
    
    # Create various trades with different characteristics
    trade_configs = [
        # Winning breakout trades
        {"symbol": "AAPL", "setup": SetupType.BREAKOUT, "entry": 150, "exit": 155, "hour": 10},
        {"symbol": "AAPL", "setup": SetupType.BREAKOUT, "entry": 155, "exit": 160, "hour": 10},
        {"symbol": "TSLA", "setup": SetupType.BREAKOUT, "entry": 200, "exit": 210, "hour": 11},
        
        # Losing pullback trades
        {"symbol": "AAPL", "setup": SetupType.PULLBACK, "entry": 160, "exit": 155, "hour": 14},
        {"symbol": "TSLA", "setup": SetupType.PULLBACK, "entry": 210, "exit": 205, "hour": 14},
        
        # Mixed momentum trades
        {"symbol": "MSFT", "setup": SetupType.MOMENTUM, "entry": 300, "exit": 310, "hour": 9},
        {"symbol": "MSFT", "setup": SetupType.MOMENTUM, "entry": 310, "exit": 305, "hour": 15},
    ]
    
    for i, config in enumerate(trade_configs):
        entry_date = base_date + timedelta(days=i)
        exit_date = entry_date + timedelta(hours=2)
        
        pnl = (config["exit"] - config["entry"]) * 100
        
        # Set entry hour
        entry_date = entry_date.replace(hour=config["hour"], minute=0, second=0)
        exit_date = exit_date.replace(hour=config["hour"]+2, minute=0, second=0)
        
        trade = Trade(
            user_id="test_user",
            symbol=config["symbol"],
            direction=TradeDirection.LONG,
            status=TradeStatus.CLOSED,
            setup_type=config["setup"],
            market_condition=MarketCondition.TRENDING_UP,
            entry_date=entry_date,
            entry_price=config["entry"],
            exit_date=exit_date,
            exit_price=config["exit"],
            quantity=100,
            gross_pnl=pnl,
            net_pnl=pnl - 2.0,  # Commission
            entry_commission=1.0,
            exit_commission=1.0
        )
        
        db_session.add(trade)
        trades.append(trade)
    
    db_session.commit()
    return trades


class TestPatternAnalyzer:
    """Tests for PatternAnalyzer."""
    
    def test_analyze_setup_performance(self, pattern_analyzer, sample_trades, db_session):
        """Test analyzing performance by setup type."""
        result = pattern_analyzer.analyze_setup_performance(
            user_id="test_user",
            min_trades=2
        )
        
        assert 'setup_performance' in result
        assert 'best_setup' in result
        assert 'worst_setup' in result
        
        # Check that breakout setup is identified (should have best performance)
        setup_perf = result['setup_performance']
        assert 'BREAKOUT' in setup_perf
        assert setup_perf['BREAKOUT']['total_trades'] == 3
        assert setup_perf['BREAKOUT']['winning_trades'] == 3
        assert setup_perf['BREAKOUT']['win_rate'] == 100.0
    
    def test_analyze_time_of_day_patterns(self, pattern_analyzer, sample_trades):
        """Test analyzing time of day patterns."""
        result = pattern_analyzer.analyze_time_of_day_patterns(
            user_id="test_user"
        )
        
        assert 'hourly_performance' in result
        assert 'best_trading_hours' in result
        assert 'worst_trading_hours' in result
        
        # Check that hour 10 and 11 show up (breakout trades)
        hourly = result['hourly_performance']
        assert '10:00' in hourly
        assert '11:00' in hourly
    
    def test_analyze_market_conditions(self, pattern_analyzer, sample_trades):
        """Test analyzing market condition performance."""
        result = pattern_analyzer.analyze_market_conditions(
            user_id="test_user"
        )
        
        assert 'market_condition_performance' in result
        assert 'best_condition' in result
        
        # All trades are TRENDING_UP
        cond_perf = result['market_condition_performance']
        assert 'TRENDING_UP' in cond_perf
        assert cond_perf['TRENDING_UP']['total_trades'] == 7
    
    def test_detect_behavioral_patterns_fomo(self, pattern_analyzer, db_session):
        """Test detecting FOMO trades."""
        base_date = datetime.utcnow()
        
        # Create big win followed by quick trade (FOMO pattern)
        trade1 = Trade(
            user_id="test_user",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            status=TradeStatus.CLOSED,
            sentiment=Sentiment.CONFIDENT,
            entry_date=base_date,
            entry_price=100,
            exit_date=base_date + timedelta(minutes=30),
            exit_price=110,
            quantity=100,
            net_pnl=1000  # Big win
        )
        
        # Quick follow-up trade within 30 minutes
        trade2 = Trade(
            user_id="test_user",
            symbol="TSLA",
            direction=TradeDirection.LONG,
            status=TradeStatus.CLOSED,
            sentiment=Sentiment.FOMO,
            entry_date=base_date + timedelta(minutes=35),
            entry_price=200,
            exit_date=base_date + timedelta(hours=1),
            exit_price=195,
            quantity=50,
            net_pnl=-250  # Loss
        )
        
        db_session.add_all([trade1, trade2])
        db_session.commit()
        
        result = pattern_analyzer.detect_behavioral_patterns(
            user_id="test_user",
            lookback_days=7
        )
        
        assert 'patterns' in result
        assert 'warnings' in result
        
        # Check if FOMO pattern detected
        patterns = result['patterns']
        fomo_pattern = next((p for p in patterns if p['type'] == 'FOMO'), None)
        assert fomo_pattern is not None
    
    def test_detect_behavioral_patterns_revenge(self, pattern_analyzer, db_session):
        """Test detecting revenge trades."""
        base_date = datetime.utcnow()
        
        # Create loss followed by quick revenge trade
        trade1 = Trade(
            user_id="test_user",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            status=TradeStatus.CLOSED,
            sentiment=Sentiment.DISCIPLINED,
            entry_date=base_date,
            entry_price=150,
            exit_date=base_date + timedelta(minutes=20),
            exit_price=145,
            quantity=100,
            net_pnl=-500  # Loss
        )
        
        # Quick revenge trade within 15 minutes
        trade2 = Trade(
            user_id="test_user",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            status=TradeStatus.CLOSED,
            sentiment=Sentiment.REVENGE,
            entry_date=base_date + timedelta(minutes=25),
            entry_price=145,
            exit_date=base_date + timedelta(minutes=45),
            exit_price=142,
            quantity=100,
            net_pnl=-300  # Another loss
        )
        
        db_session.add_all([trade1, trade2])
        db_session.commit()
        
        result = pattern_analyzer.detect_behavioral_patterns(
            user_id="test_user",
            lookback_days=7
        )
        
        patterns = result['patterns']
        revenge_pattern = next((p for p in patterns if p['type'] == 'REVENGE'), None)
        assert revenge_pattern is not None
    
    def test_detect_overtrading(self, pattern_analyzer, db_session):
        """Test detecting overtrading patterns."""
        base_date = datetime.utcnow()
        
        # Create 12 trades on the same day (overtrading threshold is 10)
        for i in range(12):
            trade = Trade(
                user_id="test_user",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                entry_date=base_date + timedelta(minutes=i*30),
                entry_price=150 + i,
                exit_date=base_date + timedelta(minutes=i*30 + 15),
                exit_price=151 + i,
                quantity=100,
                net_pnl=100
            )
            db_session.add(trade)
        
        db_session.commit()
        
        result = pattern_analyzer.detect_behavioral_patterns(
            user_id="test_user",
            lookback_days=7
        )
        
        patterns = result['patterns']
        overtrading_pattern = next((p for p in patterns if p['type'] == 'OVERTRADING'), None)
        assert overtrading_pattern is not None
    
    def test_get_best_performing_strategies(self, pattern_analyzer, sample_trades):
        """Test getting best performing strategies."""
        strategies = pattern_analyzer.get_best_performing_strategies(
            user_id="test_user",
            top_n=3,
            min_trades=2
        )
        
        assert len(strategies) > 0
        assert isinstance(strategies, list)
        
        # First strategy should be most profitable
        if len(strategies) > 1:
            assert strategies[0]['total_pnl'] >= strategies[1]['total_pnl']
    
    def test_analyze_setup_performance_min_trades_filter(self, pattern_analyzer, sample_trades):
        """Test that setups with insufficient trades are filtered out."""
        result = pattern_analyzer.analyze_setup_performance(
            user_id="test_user",
            min_trades=5  # High threshold
        )
        
        # Should filter out setups with < 5 trades
        setup_perf = result['setup_performance']
        for setup, stats in setup_perf.items():
            assert stats['total_trades'] >= 5
    
    def test_sentiment_performance_analysis(self, pattern_analyzer, db_session):
        """Test analyzing performance by sentiment."""
        base_date = datetime.utcnow()
        
        # Create trades with different sentiments
        sentiments = [
            (Sentiment.DISCIPLINED, 100, 110),  # Win
            (Sentiment.DISCIPLINED, 150, 155),  # Win
            (Sentiment.FOMO, 200, 195),  # Loss
            (Sentiment.REVENGE, 300, 295),  # Loss
        ]
        
        for i, (sentiment, entry, exit) in enumerate(sentiments):
            trade = Trade(
                user_id="test_user",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                sentiment=sentiment,
                entry_date=base_date + timedelta(days=i),
                entry_price=entry,
                exit_date=base_date + timedelta(days=i, hours=2),
                exit_price=exit,
                quantity=100,
                net_pnl=(exit - entry) * 100
            )
            db_session.add(trade)
        
        db_session.commit()
        
        result = pattern_analyzer.detect_behavioral_patterns(
            user_id="test_user",
            lookback_days=30
        )
        
        patterns = result['patterns']
        sentiment_pattern = next((p for p in patterns if p['type'] == 'SENTIMENT'), None)
        
        if sentiment_pattern:
            data = sentiment_pattern['data']
            # Disciplined should have better performance
            if 'DISCIPLINED' in data and 'FOMO' in data:
                assert data['DISCIPLINED']['win_rate'] > data['FOMO']['win_rate']
