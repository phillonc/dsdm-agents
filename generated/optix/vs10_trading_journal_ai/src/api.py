"""
REST API for Trading Journal AI.

This module provides FastAPI endpoints for all trading journal functionality
including trade management, journal entries, analytics, and AI insights.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import (
    TradeCreate, TradeUpdate, TradeResponse,
    JournalEntryCreate, JournalEntryResponse,
    TagCreate, TagResponse,
    WeeklyReviewResponse,
    PerformanceAnalyticsRequest,
    PerformanceAnalyticsResponse,
    TradeStatus, SetupType, MarketCondition, Sentiment
)
from .trade_capture import TradeCapture, BrokerageIntegrationClient
from .pattern_analyzer import PatternAnalyzer
from .ai_reviewer import AIReviewer
from .journal_service import JournalService
from .analytics_engine import AnalyticsEngine
from .export_service import ExportService

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Trading Journal AI API",
    description="AI-powered trading journal for OPTIX Trading Platform",
    version="1.0.0"
)

# Database setup (configure based on environment)
DATABASE_URL = "sqlite:///./trading_journal.db"  # Configure for production
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "trading-journal-ai"}


# Trade endpoints
@app.post("/api/v1/trades", response_model=TradeResponse)
async def create_trade(
    trade_data: TradeCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new trade.
    
    Args:
        trade_data: Trade creation data
        db: Database session
        
    Returns:
        Created trade
    """
    try:
        trade_service = TradeCapture(db, None)
        trade = trade_service.create_trade(trade_data)
        return trade
    except Exception as e:
        logger.error(f"Error creating trade: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/trades", response_model=List[TradeResponse])
async def get_trades(
    user_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[TradeStatus] = None,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get trades for a user with optional filters.
    
    Args:
        user_id: User identifier
        start_date: Optional start date filter
        end_date: Optional end date filter
        status: Optional status filter
        symbol: Optional symbol filter
        db: Database session
        
    Returns:
        List of trades
    """
    try:
        trade_service = TradeCapture(db, None)
        trades = trade_service.get_user_trades(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            symbol=symbol
        )
        return trades
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/v1/trades/{trade_id}/close", response_model=TradeResponse)
async def close_trade(
    trade_id: int,
    exit_price: float,
    exit_date: datetime,
    exit_commission: float = 0.0,
    db: Session = Depends(get_db)
):
    """
    Close a trade with exit information.
    
    Args:
        trade_id: Trade identifier
        exit_price: Exit price
        exit_date: Exit date/time
        exit_commission: Exit commission
        db: Database session
        
    Returns:
        Updated trade
    """
    try:
        trade_service = TradeCapture(db, None)
        trade = trade_service.update_trade_exit(
            trade_id=trade_id,
            exit_price=exit_price,
            exit_date=exit_date,
            exit_commission=exit_commission
        )
        return trade
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/trades/sync")
async def sync_trades(
    user_id: str,
    broker_id: str,
    vs7_api_url: str,
    vs7_api_key: str,
    lookback_days: int = 30,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Synchronize trades from brokerage via VS-7.
    
    Args:
        user_id: User identifier
        broker_id: Broker identifier
        vs7_api_url: VS-7 API URL
        vs7_api_key: VS-7 API key
        lookback_days: Number of days to sync
        background_tasks: Background tasks handler
        db: Database session
        
    Returns:
        Sync summary
    """
    try:
        async with BrokerageIntegrationClient(vs7_api_url, vs7_api_key) as client:
            trade_service = TradeCapture(db, client)
            stats = await trade_service.sync_trades(
                user_id=user_id,
                broker_id=broker_id,
                lookback_days=lookback_days
            )
            return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Error syncing trades: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Journal endpoints
@app.post("/api/v1/journal", response_model=JournalEntryResponse)
async def create_journal_entry(
    entry_data: JournalEntryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new journal entry.
    
    Args:
        entry_data: Journal entry data
        db: Database session
        
    Returns:
        Created journal entry
    """
    try:
        journal_service = JournalService(db)
        entry = journal_service.create_journal_entry(entry_data)
        return entry
    except Exception as e:
        logger.error(f"Error creating journal entry: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/journal", response_model=List[JournalEntryResponse])
async def get_journal_entries(
    user_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    trade_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get journal entries for a user.
    
    Args:
        user_id: User identifier
        start_date: Optional start date
        end_date: Optional end date
        trade_id: Optional trade filter
        limit: Maximum results
        offset: Results offset
        db: Database session
        
    Returns:
        List of journal entries
    """
    try:
        journal_service = JournalService(db)
        entries = journal_service.get_user_journal_entries(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            trade_id=trade_id,
            limit=limit,
            offset=offset
        )
        return entries
    except Exception as e:
        logger.error(f"Error fetching journal entries: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/journal/search", response_model=List[JournalEntryResponse])
async def search_journal_entries(
    user_id: str,
    query: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Search journal entries.
    
    Args:
        user_id: User identifier
        query: Search query
        limit: Maximum results
        db: Database session
        
    Returns:
        Matching journal entries
    """
    try:
        journal_service = JournalService(db)
        entries = journal_service.search_journal_entries(
            user_id=user_id,
            search_query=query,
            limit=limit
        )
        return entries
    except Exception as e:
        logger.error(f"Error searching journal entries: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Tag endpoints
@app.post("/api/v1/tags", response_model=TagResponse)
async def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new tag.
    
    Args:
        tag_data: Tag creation data
        db: Database session
        
    Returns:
        Created tag
    """
    try:
        journal_service = JournalService(db)
        tag = journal_service.create_tag(tag_data)
        return tag
    except Exception as e:
        logger.error(f"Error creating tag: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/tags", response_model=List[TagResponse])
async def get_tags(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all tags for a user.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        List of tags
    """
    try:
        journal_service = JournalService(db)
        tags = journal_service.get_user_tags(user_id)
        return tags
    except Exception as e:
        logger.error(f"Error fetching tags: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/trades/{trade_id}/tags/{tag_id}")
async def add_tag_to_trade(
    trade_id: int,
    tag_id: int,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Add a tag to a trade.
    
    Args:
        trade_id: Trade identifier
        tag_id: Tag identifier
        user_id: User identifier
        db: Database session
        
    Returns:
        Success message
    """
    try:
        journal_service = JournalService(db)
        journal_service.add_tag_to_trade(trade_id, tag_id, user_id)
        return {"status": "success", "message": "Tag added to trade"}
    except Exception as e:
        logger.error(f"Error adding tag to trade: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Analytics endpoints
@app.get("/api/v1/analytics/performance")
async def get_performance_analytics(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    symbol: Optional[str] = None,
    setup_type: Optional[SetupType] = None,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive performance analytics.
    
    Args:
        user_id: User identifier
        start_date: Start date
        end_date: End date
        symbol: Optional symbol filter
        setup_type: Optional setup type filter
        db: Database session
        
    Returns:
        Performance metrics
    """
    try:
        analytics = AnalyticsEngine(db)
        filters = {}
        if symbol:
            filters['symbol'] = symbol
        if setup_type:
            filters['setup_type'] = setup_type
        
        metrics = analytics.calculate_performance_metrics(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            filters=filters
        )
        return metrics
    except Exception as e:
        logger.error(f"Error calculating analytics: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/analytics/by-symbol")
async def get_symbol_analytics(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    min_trades: int = 3,
    db: Session = Depends(get_db)
):
    """
    Get performance analytics by symbol.
    
    Args:
        user_id: User identifier
        start_date: Start date
        end_date: End date
        min_trades: Minimum trades per symbol
        db: Database session
        
    Returns:
        Symbol performance breakdown
    """
    try:
        analytics = AnalyticsEngine(db)
        results = analytics.analyze_by_symbol(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            min_trades=min_trades
        )
        return results
    except Exception as e:
        logger.error(f"Error analyzing by symbol: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/analytics/by-setup")
async def get_setup_analytics(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """
    Get performance analytics by setup type.
    
    Args:
        user_id: User identifier
        start_date: Start date
        end_date: End date
        db: Database session
        
    Returns:
        Setup type performance breakdown
    """
    try:
        analytics = AnalyticsEngine(db)
        results = analytics.analyze_by_setup_type(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        return results
    except Exception as e:
        logger.error(f"Error analyzing by setup: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/analytics/equity-curve")
async def get_equity_curve(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """
    Get equity curve data.
    
    Args:
        user_id: User identifier
        start_date: Start date
        end_date: End date
        db: Database session
        
    Returns:
        Equity curve data points
    """
    try:
        analytics = AnalyticsEngine(db)
        curve = analytics.generate_equity_curve(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        return {"equity_curve": curve}
    except Exception as e:
        logger.error(f"Error generating equity curve: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Pattern analysis endpoints
@app.get("/api/v1/patterns/behavioral")
async def detect_behavioral_patterns(
    user_id: str,
    lookback_days: int = 90,
    db: Session = Depends(get_db)
):
    """
    Detect behavioral patterns (FOMO, revenge trading, etc.).
    
    Args:
        user_id: User identifier
        lookback_days: Days to analyze
        db: Database session
        
    Returns:
        Behavioral pattern analysis
    """
    try:
        analyzer = PatternAnalyzer(db)
        patterns = analyzer.detect_behavioral_patterns(
            user_id=user_id,
            lookback_days=lookback_days
        )
        return patterns
    except Exception as e:
        logger.error(f"Error detecting patterns: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/patterns/best-strategies")
async def get_best_strategies(
    user_id: str,
    top_n: int = 5,
    min_trades: int = 5,
    db: Session = Depends(get_db)
):
    """
    Get best performing strategies.
    
    Args:
        user_id: User identifier
        top_n: Number of strategies to return
        min_trades: Minimum trades required
        db: Database session
        
    Returns:
        Best performing strategies
    """
    try:
        analyzer = PatternAnalyzer(db)
        strategies = analyzer.get_best_performing_strategies(
            user_id=user_id,
            top_n=top_n,
            min_trades=min_trades
        )
        return {"strategies": strategies}
    except Exception as e:
        logger.error(f"Error getting best strategies: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# AI Review endpoints
@app.post("/api/v1/reviews/weekly", response_model=WeeklyReviewResponse)
async def generate_weekly_review(
    user_id: str,
    week_start: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Generate AI-powered weekly review.
    
    Args:
        user_id: User identifier
        week_start: Optional week start date
        db: Database session
        
    Returns:
        Weekly review with insights and tips
    """
    try:
        reviewer = AIReviewer(db)
        review = reviewer.generate_weekly_review(
            user_id=user_id,
            week_start=week_start
        )
        return review
    except Exception as e:
        logger.error(f"Error generating weekly review: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/reviews/weekly", response_model=List[WeeklyReviewResponse])
async def get_weekly_reviews(
    user_id: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get recent weekly reviews.
    
    Args:
        user_id: User identifier
        limit: Maximum number of reviews
        db: Database session
        
    Returns:
        List of weekly reviews
    """
    try:
        reviewer = AIReviewer(db)
        reviews = reviewer.get_weekly_reviews(user_id=user_id, limit=limit)
        return reviews
    except Exception as e:
        logger.error(f"Error fetching weekly reviews: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Export endpoints
@app.get("/api/v1/export/csv")
async def export_csv(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """
    Export trades to CSV.
    
    Args:
        user_id: User identifier
        start_date: Start date
        end_date: End date
        db: Database session
        
    Returns:
        CSV file
    """
    try:
        export_service = ExportService(db)
        file_path = export_service.export_trades_csv(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        return FileResponse(
            file_path,
            media_type='text/csv',
            filename=f'trades_{user_id}_{start_date.date()}_to_{end_date.date()}.csv'
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/export/pdf")
async def export_pdf(
    user_id: str,
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db)
):
    """
    Export performance report as PDF.
    
    Args:
        user_id: User identifier
        start_date: Start date
        end_date: End date
        db: Database session
        
    Returns:
        PDF file
    """
    try:
        export_service = ExportService(db)
        file_path = export_service.export_performance_pdf(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        return FileResponse(
            file_path,
            media_type='application/pdf',
            filename=f'performance_report_{user_id}_{start_date.date()}_to_{end_date.date()}.pdf'
        )
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
