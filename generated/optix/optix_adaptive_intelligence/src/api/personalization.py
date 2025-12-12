"""
API endpoints for personalization
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from ..models.user_models import (
    UserProfile, TradingPattern, PersonalizedInsight, UserStatistics,
    TradingStyle, RiskTolerance
)
from ..services.personalization_service import PersonalizationService

router = APIRouter(prefix="/api/v1/personalization", tags=["personalization"])


def get_personalization_service() -> PersonalizationService:
    return PersonalizationService()


@router.get("/profile/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: str,
    service: PersonalizationService = Depends(get_personalization_service)
):
    """
    Get user profile
    
    Args:
        user_id: User identifier
        
    Returns:
        User profile
    """
    # In production, fetch from database
    # For now, return sample profile
    profile = UserProfile(
        user_id=user_id,
        trading_style=TradingStyle.SWING_TRADER,
        risk_tolerance=RiskTolerance.MODERATE,
        preferred_symbols=["AAPL", "MSFT", "GOOGL"],
        preferred_timeframes=["1D", "4H"],
        experience_level="intermediate"
    )
    return profile


@router.put("/profile/{user_id}", response_model=UserProfile)
async def update_user_profile(
    user_id: str,
    profile: UserProfile = Body(...),
    service: PersonalizationService = Depends(get_personalization_service)
):
    """
    Update user profile
    
    Args:
        user_id: User identifier
        profile: Updated profile data
        
    Returns:
        Updated user profile
    """
    try:
        # In production, save to database
        profile.updated_at = datetime.utcnow()
        return profile
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns/{user_id}/learn", response_model=List[TradingPattern])
async def learn_trading_patterns(
    user_id: str,
    days_back: int = Query(default=30, ge=1, le=365),
    service: PersonalizationService = Depends(get_personalization_service)
):
    """
    Learn trading patterns from user's history
    
    Args:
        user_id: User identifier
        days_back: Number of days of history to analyze
        
    Returns:
        List of identified trading patterns
    """
    try:
        # Get user profile
        profile = UserProfile(
            user_id=user_id,
            trading_style=TradingStyle.SWING_TRADER,
            risk_tolerance=RiskTolerance.MODERATE
        )
        
        # Create sample trade history
        trade_history = _create_sample_trade_history(user_id, days_back)
        
        patterns = await service.learn_trading_patterns(
            user_id=user_id,
            trade_history=trade_history,
            user_profile=profile
        )
        
        return patterns
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/{user_id}/generate", response_model=List[PersonalizedInsight])
async def generate_personalized_insights(
    user_id: str,
    max_insights: int = Query(default=10, ge=1, le=50),
    service: PersonalizationService = Depends(get_personalization_service)
):
    """
    Generate personalized insights for user
    
    Args:
        user_id: User identifier
        max_insights: Maximum number of insights to return
        
    Returns:
        List of personalized insights
    """
    try:
        # Get user profile
        profile = UserProfile(
            user_id=user_id,
            trading_style=TradingStyle.SWING_TRADER,
            risk_tolerance=RiskTolerance.MODERATE,
            preferred_symbols=["AAPL", "MSFT"]
        )
        
        # Get trading patterns
        trade_history = _create_sample_trade_history(user_id, 30)
        trading_patterns = await service.learn_trading_patterns(
            user_id=user_id,
            trade_history=trade_history,
            user_profile=profile
        )
        
        # Get current signals (mock)
        from ..models.analysis_models import (
            PredictionSignal, SignalType, SignalStrength
        )
        current_signals = [
            PredictionSignal(
                signal_id="sig_test",
                symbol="AAPL",
                signal_type=SignalType.BUY,
                signal_strength=SignalStrength.STRONG,
                confidence=0.85,
                current_price=178.50,
                predicted_price=185.00,
                time_horizon="1W",
                prediction_range={"min": 182.0, "max": 188.0, "std_dev": 2.5},
                model_name="RandomForest"
            )
        ]
        
        # Get detected patterns (mock)
        detected_patterns = []
        
        insights = await service.generate_personalized_insights(
            user_id=user_id,
            user_profile=profile,
            trading_patterns=trading_patterns,
            current_signals=current_signals,
            detected_patterns=detected_patterns
        )
        
        return insights[:max_insights]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/{user_id}", response_model=List[PersonalizedInsight])
async def get_user_insights(
    user_id: str,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    service: PersonalizationService = Depends(get_personalization_service)
):
    """
    Get user's insights
    
    Args:
        user_id: User identifier
        unread_only: Return only unread insights
        limit: Maximum number of insights
        
    Returns:
        List of insights
    """
    # In production, fetch from database
    raise HTTPException(status_code=501, detail="Not implemented - fetch from database")


@router.put("/insights/{insight_id}/read")
async def mark_insight_read(
    insight_id: str,
    service: PersonalizationService = Depends(get_personalization_service)
):
    """
    Mark insight as read
    
    Args:
        insight_id: Insight identifier
        
    Returns:
        Success message
    """
    # In production, update in database
    return {"status": "success", "message": "Insight marked as read"}


@router.get("/statistics/{user_id}", response_model=UserStatistics)
async def get_user_statistics(
    user_id: str,
    days_back: int = Query(default=30, ge=1, le=365),
    service: PersonalizationService = Depends(get_personalization_service)
):
    """
    Get user trading statistics
    
    Args:
        user_id: User identifier
        days_back: Number of days to analyze
        
    Returns:
        User trading statistics
    """
    try:
        trade_history = _create_sample_trade_history(user_id, days_back)
        
        # Calculate statistics
        total_trades = len(trade_history)
        winning_trades = len(trade_history[trade_history['profit'] > 0])
        losing_trades = total_trades - winning_trades
        
        statistics = UserStatistics(
            user_id=user_id,
            period_start=datetime.utcnow() - timedelta(days=days_back),
            period_end=datetime.utcnow(),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=winning_trades / total_trades if total_trades > 0 else 0.0,
            average_return=trade_history['profit'].mean(),
            total_return=trade_history['profit'].sum(),
            max_drawdown=trade_history['profit'].cumsum().min() / 10000,  # Normalize
            average_holding_period=24.0,  # Mock value
            most_traded_symbols=[
                {"symbol": symbol, "count": count}
                for symbol, count in trade_history['symbol'].value_counts().head(5).items()
            ],
            risk_metrics={
                'sharpe_ratio': 1.5,
                'sortino_ratio': 2.0,
                'max_consecutive_losses': 3
            }
        )
        
        return statistics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _create_sample_trade_history(user_id: str, days_back: int) -> pd.DataFrame:
    """Create sample trade history for testing"""
    num_trades = min(days_back * 2, 100)  # Roughly 2 trades per day
    
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    strategies = ["momentum", "mean_reversion", "breakout"]
    entry_conditions = ["rsi_oversold", "breakout_confirmed", "support_bounce"]
    exit_reasons = ["take_profit", "stop_loss", "time_exit"]
    
    trades = []
    for i in range(num_trades):
        entry_time = datetime.utcnow() - timedelta(days=np.random.randint(0, days_back))
        exit_time = entry_time + timedelta(hours=np.random.randint(1, 72))
        
        profit = np.random.normal(0.02, 0.05)  # 2% avg return, 5% std dev
        
        trades.append({
            'user_id': user_id,
            'symbol': np.random.choice(symbols),
            'strategy': np.random.choice(strategies),
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': 100.0,
            'exit_price': 100.0 * (1 + profit),
            'position_size': np.random.uniform(1000, 5000),
            'profit': profit * 100,  # Percent profit
            'entry_conditions': [np.random.choice(entry_conditions)],
            'exit_reason': np.random.choice(exit_reasons),
            'account_size': 50000
        })
    
    return pd.DataFrame(trades)
