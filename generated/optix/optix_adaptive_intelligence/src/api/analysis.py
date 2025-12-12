"""
API endpoints for AI analysis
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
import pandas as pd

from ..models.analysis_models import (
    PredictionSignal, VolatilityForecast, SentimentAnalysis, MarketContext
)
from ..services.ai_analysis_service import AIAnalysisService
from ..api.patterns import _create_sample_price_data  # Reuse helper

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


def get_analysis_service() -> AIAnalysisService:
    return AIAnalysisService()


@router.post("/predict", response_model=List[PredictionSignal])
async def generate_price_predictions(
    symbol: str,
    time_horizon: str = Query(default="1D", regex="^(1D|1W|1M|3M)$"),
    service: AIAnalysisService = Depends(get_analysis_service)
):
    """
    Generate price prediction signals
    
    Args:
        symbol: Trading symbol
        time_horizon: Prediction time horizon
        
    Returns:
        List of prediction signals
    """
    try:
        price_data = _create_sample_price_data(symbol)
        
        signals = await service.generate_prediction_signals(
            symbol=symbol,
            price_data=price_data,
            time_horizon=time_horizon
        )
        
        return signals
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/volatility/forecast", response_model=VolatilityForecast)
async def forecast_volatility(
    symbol: str,
    forecast_horizon: str = Query(default="1W", regex="^(1D|1W|1M)$"),
    service: AIAnalysisService = Depends(get_analysis_service)
):
    """
    Forecast volatility
    
    Args:
        symbol: Trading symbol
        forecast_horizon: Forecast time horizon
        
    Returns:
        Volatility forecast
    """
    try:
        price_data = _create_sample_price_data(symbol)
        
        forecast = await service.forecast_volatility(
            symbol=symbol,
            price_data=price_data,
            forecast_horizon=forecast_horizon
        )
        
        return forecast
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentiment", response_model=SentimentAnalysis)
async def analyze_sentiment(
    symbol: str,
    include_news: bool = Query(default=False),
    include_options: bool = Query(default=True),
    service: AIAnalysisService = Depends(get_analysis_service)
):
    """
    Analyze market sentiment
    
    Args:
        symbol: Trading symbol
        include_news: Include news sentiment analysis
        include_options: Include options flow sentiment
        
    Returns:
        Sentiment analysis
    """
    try:
        # Prepare market data
        market_data = {
            'rsi': 55.0,
            'macd': 0.5,
            'breadth': {
                'advance_decline_ratio': 1.2,
                'new_highs_lows': 50
            }
        }
        
        # Get options flow if requested
        options_flow = None
        if include_options:
            from ..api.patterns import _create_sample_options_data
            options_flow = _create_sample_options_data(symbol)
        
        # Get news data if requested
        news_data = None
        if include_news:
            news_data = _create_sample_news_data(symbol)
        
        sentiment = await service.analyze_sentiment(
            symbol=symbol,
            market_data=market_data,
            options_flow=options_flow,
            news_data=news_data
        )
        
        return sentiment
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market-context", response_model=MarketContext)
async def analyze_market_context(
    symbol: str,
    service: AIAnalysisService = Depends(get_analysis_service)
):
    """
    Analyze overall market context
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Market context analysis
    """
    try:
        price_data = _create_sample_price_data(symbol)
        
        market_data = {
            'spy_correlation': 0.75,
            'beta': 1.2,
            'sector_performance': {
                'technology': 0.05,
                'finance': -0.02,
                'healthcare': 0.03
            },
            'ad_ratio': 1.5,
            'nh_nl': 100,
            'vix': 18.5
        }
        
        context = await service.analyze_market_context(
            symbol=symbol,
            price_data=price_data,
            market_data=market_data
        )
        
        return context
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/{signal_id}", response_model=PredictionSignal)
async def get_signal_details(
    signal_id: str,
    service: AIAnalysisService = Depends(get_analysis_service)
):
    """
    Get details of a specific signal
    
    Args:
        signal_id: Signal identifier
        
    Returns:
        Signal details
    """
    # In production, fetch from database
    raise HTTPException(status_code=404, detail="Signal not found")


def _create_sample_news_data(symbol: str) -> List[dict]:
    """Create sample news data for testing"""
    return [
        {
            'title': f'{symbol} Reports Strong Earnings',
            'summary': 'Company exceeds expectations with quarterly results',
            'published_at': datetime.now(),
            'source': 'Financial Times'
        },
        {
            'title': f'Analysts Upgrade {symbol}',
            'summary': 'Multiple analysts raise price targets',
            'published_at': datetime.now(),
            'source': 'Bloomberg'
        },
        {
            'title': f'{symbol} Announces New Product',
            'summary': 'Company unveils innovative product line',
            'published_at': datetime.now(),
            'source': 'Reuters'
        }
    ]
