"""
Unit tests for data models.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.models import (
    TradeCreate, TradeUpdate, JournalEntryCreate,
    TagCreate, TradeDirection, TradeStatus, SetupType,
    MarketCondition, Sentiment
)


class TestTradeCreate:
    """Tests for TradeCreate schema."""
    
    def test_valid_trade_create(self):
        """Test creating valid trade."""
        trade_data = TradeCreate(
            user_id="user123",
            symbol="AAPL",
            direction=TradeDirection.LONG,
            entry_date=datetime.utcnow(),
            entry_price=150.50,
            quantity=100
        )
        
        assert trade_data.user_id == "user123"
        assert trade_data.symbol == "AAPL"
        assert trade_data.direction == TradeDirection.LONG
        assert trade_data.entry_price == 150.50
        assert trade_data.quantity == 100
    
    def test_trade_create_with_optional_fields(self):
        """Test creating trade with optional fields."""
        trade_data = TradeCreate(
            user_id="user123",
            symbol="TSLA",
            direction=TradeDirection.SHORT,
            entry_date=datetime.utcnow(),
            entry_price=200.00,
            quantity=50,
            stop_loss=210.00,
            take_profit=180.00,
            setup_type=SetupType.BREAKOUT,
            market_condition=MarketCondition.TRENDING_UP,
            sentiment=Sentiment.CONFIDENT
        )
        
        assert trade_data.stop_loss == 210.00
        assert trade_data.take_profit == 180.00
        assert trade_data.setup_type == SetupType.BREAKOUT
        assert trade_data.market_condition == MarketCondition.TRENDING_UP
        assert trade_data.sentiment == Sentiment.CONFIDENT
    
    def test_trade_create_validates_positive_price(self):
        """Test that entry price must be positive."""
        with pytest.raises(ValueError, match="Must be positive"):
            TradeCreate(
                user_id="user123",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                entry_date=datetime.utcnow(),
                entry_price=-150.50,  # Invalid
                quantity=100
            )
    
    def test_trade_create_validates_positive_quantity(self):
        """Test that quantity must be positive."""
        with pytest.raises(ValueError, match="Must be positive"):
            TradeCreate(
                user_id="user123",
                symbol="AAPL",
                direction=TradeDirection.LONG,
                entry_date=datetime.utcnow(),
                entry_price=150.50,
                quantity=0  # Invalid
            )


class TestJournalEntryCreate:
    """Tests for JournalEntryCreate schema."""
    
    def test_valid_journal_entry_create(self):
        """Test creating valid journal entry."""
        entry_data = JournalEntryCreate(
            user_id="user123",
            title="Great trade day",
            content="Made excellent decisions today.",
            mood_rating=8,
            confidence_level=9,
            discipline_rating=10
        )
        
        assert entry_data.user_id == "user123"
        assert entry_data.title == "Great trade day"
        assert entry_data.mood_rating == 8
        assert entry_data.confidence_level == 9
        assert entry_data.discipline_rating == 10
    
    def test_journal_entry_with_trade_id(self):
        """Test journal entry linked to trade."""
        entry_data = JournalEntryCreate(
            user_id="user123",
            trade_id=42,
            notes="This trade followed my plan perfectly."
        )
        
        assert entry_data.trade_id == 42
        assert entry_data.notes is not None
    
    def test_journal_entry_mood_validation(self):
        """Test mood rating validation."""
        with pytest.raises(ValueError):
            JournalEntryCreate(
                user_id="user123",
                mood_rating=11  # Out of range
            )
        
        with pytest.raises(ValueError):
            JournalEntryCreate(
                user_id="user123",
                mood_rating=0  # Out of range
            )


class TestTagCreate:
    """Tests for TagCreate schema."""
    
    def test_valid_tag_create(self):
        """Test creating valid tag."""
        tag_data = TagCreate(
            user_id="user123",
            name="Morning Trade",
            category="timing",
            color="#FF5733"
        )
        
        assert tag_data.user_id == "user123"
        assert tag_data.name == "Morning Trade"
        assert tag_data.category == "timing"
        assert tag_data.color == "#FF5733"


class TestEnumerations:
    """Tests for enumeration types."""
    
    def test_trade_direction_enum(self):
        """Test TradeDirection enumeration."""
        assert TradeDirection.LONG.value == "LONG"
        assert TradeDirection.SHORT.value == "SHORT"
    
    def test_trade_status_enum(self):
        """Test TradeStatus enumeration."""
        assert TradeStatus.OPEN.value == "OPEN"
        assert TradeStatus.CLOSED.value == "CLOSED"
        assert TradeStatus.PARTIAL.value == "PARTIAL"
        assert TradeStatus.CANCELLED.value == "CANCELLED"
    
    def test_setup_type_enum(self):
        """Test SetupType enumeration."""
        assert SetupType.BREAKOUT.value == "BREAKOUT"
        assert SetupType.PULLBACK.value == "PULLBACK"
        assert SetupType.REVERSAL.value == "REVERSAL"
    
    def test_market_condition_enum(self):
        """Test MarketCondition enumeration."""
        assert MarketCondition.TRENDING_UP.value == "TRENDING_UP"
        assert MarketCondition.RANGING.value == "RANGING"
        assert MarketCondition.VOLATILE.value == "VOLATILE"
    
    def test_sentiment_enum(self):
        """Test Sentiment enumeration."""
        assert Sentiment.CONFIDENT.value == "CONFIDENT"
        assert Sentiment.FOMO.value == "FOMO"
        assert Sentiment.REVENGE.value == "REVENGE"
        assert Sentiment.DISCIPLINED.value == "DISCIPLINED"
