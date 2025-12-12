"""
Unit tests for AI reviewer.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import (
    Base, Trade, WeeklyReview, TradeDirection, 
    TradeStatus, SetupType
)
from src.ai_reviewer import AIReviewer


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
def ai_reviewer(db_session):
    """Create AIReviewer instance."""
    return AIReviewer(db_session)


@pytest.fixture
def weekly_trades(db_session):
    """Create sample trades for a week."""
    trades = []
    week_start = datetime.utcnow() - timedelta(days=7)
    
    # Create 10 trades: 6 wins, 4 losses
    for i in range(10):
        entry_date = week_start + timedelta(days=i % 5, hours=10)
        is_win = i < 6
        
        trade = Trade(
            user_id="test_user",
            symbol="AAPL" if i % 2 == 0 else "TSLA",
            direction=TradeDirection.LONG,
            status=TradeStatus.CLOSED,
            setup_type=SetupType.BREAKOUT if i < 5 else SetupType.PULLBACK,
            entry_date=entry_date,
            entry_price=150.0 + i,
            exit_date=entry_date + timedelta(hours=2),
            exit_price=155.0 + i if is_win else 145.0 + i,
            quantity=100,
            entry_commission=1.0,
            exit_commission=1.0
        )
        
        # Calculate P&L
        price_diff = trade.exit_price - trade.entry_price
        trade.gross_pnl = price_diff * trade.quantity
        trade.net_pnl = trade.gross_pnl - 2.0
        
        db_session.add(trade)
        trades.append(trade)
    
    db_session.commit()
    return trades


class TestAIReviewer:
    """Tests for AIReviewer."""
    
    def test_generate_weekly_review(self, ai_reviewer, weekly_trades):
        """Test generating a weekly review."""
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        assert review.id is not None
        assert review.user_id == "test_user"
        assert review.total_trades == 10
        assert review.winning_trades == 6
        assert review.losing_trades == 4
        assert review.win_rate == 60.0
        assert review.net_pnl is not None
        assert review.summary_text is not None
    
    def test_weekly_review_metrics_calculation(self, ai_reviewer, weekly_trades):
        """Test that metrics are calculated correctly."""
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        # Check basic metrics
        assert review.total_trades == 10
        assert review.winning_trades == 6
        assert review.losing_trades == 4
        
        # Check P&L metrics
        assert review.gross_pnl is not None
        assert review.net_pnl is not None
        assert review.average_win > 0
        assert review.average_loss < 0
        
        # Check profit factor
        assert review.profit_factor > 0
    
    def test_weekly_review_setup_analysis(self, ai_reviewer, weekly_trades):
        """Test setup type analysis in weekly review."""
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        assert review.top_performing_setups is not None
        assert isinstance(review.top_performing_setups, dict)
        
        # Should have BREAKOUT in top setups (5 breakout trades)
        assert len(review.top_performing_setups) > 0
    
    def test_weekly_review_insights_generation(self, ai_reviewer, weekly_trades):
        """Test that insights are generated."""
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        assert review.key_insights is not None
        assert isinstance(review.key_insights, list)
        assert len(review.key_insights) > 0
        
        # Insights should mention win rate
        insights_text = " ".join(review.key_insights)
        assert "win rate" in insights_text.lower() or "60" in insights_text
    
    def test_weekly_review_improvement_tips(self, ai_reviewer, weekly_trades):
        """Test that improvement tips are generated."""
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        assert review.improvement_tips is not None
        assert isinstance(review.improvement_tips, list)
        assert len(review.improvement_tips) > 0
    
    def test_weekly_review_behavioral_analysis(self, ai_reviewer, weekly_trades):
        """Test behavioral analysis in weekly review."""
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        assert review.behavioral_analysis is not None
        assert isinstance(review.behavioral_analysis, dict)
    
    def test_weekly_review_summary_text(self, ai_reviewer, weekly_trades):
        """Test that summary text is generated."""
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        assert review.summary_text is not None
        assert len(review.summary_text) > 0
        
        # Should mention key metrics
        summary = review.summary_text.lower()
        assert "trades" in summary
        assert "win rate" in summary or "60" in summary
    
    def test_get_weekly_reviews(self, ai_reviewer, weekly_trades):
        """Test retrieving weekly reviews."""
        # Generate a review first
        review1 = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        # Get reviews
        reviews = ai_reviewer.get_weekly_reviews(user_id="test_user", limit=10)
        
        assert len(reviews) == 1
        assert reviews[0].id == review1.id
    
    def test_get_review_by_date(self, ai_reviewer, weekly_trades):
        """Test getting review by specific date."""
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        # Get review for a date within the week
        date_in_week = review.week_start + timedelta(days=3)
        found_review = ai_reviewer.get_review_by_date(
            user_id="test_user",
            date=date_in_week
        )
        
        assert found_review is not None
        assert found_review.id == review.id
    
    def test_insights_for_high_win_rate(self, ai_reviewer, db_session):
        """Test insights generation for high win rate."""
        week_start = datetime.utcnow() - timedelta(days=7)
        
        # Create 9 winning trades, 1 losing
        for i in range(10):
            is_win = i < 9
            
            trade = Trade(
                user_id="test_user",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                entry_date=week_start + timedelta(hours=i),
                entry_price=150.0,
                exit_date=week_start + timedelta(hours=i+1),
                exit_price=155.0 if is_win else 145.0,
                quantity=100,
                net_pnl=500.0 if is_win else -500.0
            )
            db_session.add(trade)
        
        db_session.commit()
        
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        # Should have positive insights for 90% win rate
        insights_text = " ".join(review.key_insights).lower()
        assert "excellent" in insights_text or "great" in insights_text or "strong" in insights_text
    
    def test_insights_for_low_win_rate(self, ai_reviewer, db_session):
        """Test insights generation for low win rate."""
        week_start = datetime.utcnow() - timedelta(days=7)
        
        # Create 3 winning trades, 7 losing
        for i in range(10):
            is_win = i < 3
            
            trade = Trade(
                user_id="test_user",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                entry_date=week_start + timedelta(hours=i),
                entry_price=150.0,
                exit_date=week_start + timedelta(hours=i+1),
                exit_price=155.0 if is_win else 145.0,
                quantity=100,
                net_pnl=500.0 if is_win else -500.0
            )
            db_session.add(trade)
        
        db_session.commit()
        
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        # Should have improvement suggestions
        insights_text = " ".join(review.key_insights).lower()
        assert "improvement" in insights_text or "review" in insights_text or "focus" in insights_text
    
    def test_tips_for_overtrading(self, ai_reviewer, db_session):
        """Test tips generation for overtrading."""
        week_start = datetime.utcnow() - timedelta(days=7)
        
        # Create 100 trades (overtrading)
        for i in range(100):
            trade = Trade(
                user_id="test_user",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                entry_date=week_start + timedelta(hours=i % 24, days=i // 24),
                entry_price=150.0,
                exit_date=week_start + timedelta(hours=(i % 24) + 1, days=i // 24),
                exit_price=151.0,
                quantity=100,
                net_pnl=100.0
            )
            db_session.add(trade)
        
        db_session.commit()
        
        review = ai_reviewer.generate_weekly_review(user_id="test_user")
        
        # Should warn about overtrading
        tips_text = " ".join(review.improvement_tips).lower()
        assert "quality" in tips_text or "overtrading" in tips_text or "quantity" in tips_text
