"""
API endpoints for pattern recognition
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
import pandas as pd

from ..models.pattern_models import (
    ChartPattern, OptionsActivity, VolumeAnomaly, SupportResistanceLevel
)
from ..services.pattern_recognition_service import PatternRecognitionService

router = APIRouter(prefix="/api/v1/patterns", tags=["patterns"])


# Dependency injection for service
def get_pattern_service() -> PatternRecognitionService:
    return PatternRecognitionService()


@router.post("/detect/chart", response_model=List[ChartPattern])
async def detect_chart_patterns(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: PatternRecognitionService = Depends(get_pattern_service)
):
    """
    Detect chart patterns in price data
    
    Args:
        symbol: Trading symbol
        start_date: Start date for analysis
        end_date: End date for analysis
        
    Returns:
        List of detected chart patterns
    """
    try:
        # In production, fetch real price data from data service
        # For now, create sample data
        price_data = _create_sample_price_data(symbol, start_date, end_date)
        volume_data = _create_sample_volume_data(symbol, start_date, end_date)
        
        patterns = await service.detect_chart_patterns(
            symbol=symbol,
            price_data=price_data,
            volume_data=volume_data
        )
        
        return patterns
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/support-resistance", response_model=List[SupportResistanceLevel])
async def detect_support_resistance(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: PatternRecognitionService = Depends(get_pattern_service)
):
    """
    Detect support and resistance levels
    
    Args:
        symbol: Trading symbol
        start_date: Start date for analysis
        end_date: End date for analysis
        
    Returns:
        List of support and resistance levels
    """
    try:
        price_data = _create_sample_price_data(symbol, start_date, end_date)
        volume_data = _create_sample_volume_data(symbol, start_date, end_date)
        
        levels = await service.detect_support_resistance(
            symbol=symbol,
            price_data=price_data,
            volume_data=volume_data
        )
        
        return levels
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/unusual-options", response_model=List[OptionsActivity])
async def detect_unusual_options(
    symbol: str,
    min_volume_multiple: float = Query(default=3.0, ge=1.0),
    service: PatternRecognitionService = Depends(get_pattern_service)
):
    """
    Detect unusual options activity
    
    Args:
        symbol: Trading symbol
        min_volume_multiple: Minimum volume multiple to flag as unusual
        
    Returns:
        List of unusual options activities
    """
    try:
        # In production, fetch real options data
        options_data = _create_sample_options_data(symbol)
        
        activities = await service.detect_unusual_options_activity(
            symbol=symbol,
            options_data=options_data
        )
        
        # Filter by minimum volume multiple
        filtered = [a for a in activities if a.volume_multiple >= min_volume_multiple]
        
        return filtered
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/volume-anomalies", response_model=List[VolumeAnomaly])
async def detect_volume_anomalies(
    symbol: str,
    timeframe: str = Query(default="1D", regex="^(1m|5m|15m|1H|4H|1D)$"),
    service: PatternRecognitionService = Depends(get_pattern_service)
):
    """
    Detect volume anomalies
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe for analysis
        
    Returns:
        List of volume anomalies
    """
    try:
        volume_data = _create_sample_volume_data(symbol)
        price_data = _create_sample_price_data(symbol)
        
        anomalies = await service.detect_volume_anomalies(
            symbol=symbol,
            volume_data=volume_data,
            price_data=price_data,
            timeframe=timeframe
        )
        
        return anomalies
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/{pattern_id}", response_model=ChartPattern)
async def get_pattern_details(
    pattern_id: str,
    service: PatternRecognitionService = Depends(get_pattern_service)
):
    """
    Get details of a specific pattern
    
    Args:
        pattern_id: Pattern identifier
        
    Returns:
        Pattern details
    """
    # In production, fetch from database
    raise HTTPException(status_code=404, detail="Pattern not found")


# Helper functions to create sample data
def _create_sample_price_data(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """Create sample price data for testing"""
    import numpy as np
    
    periods = 100
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    
    # Generate synthetic price data
    base_price = 100.0
    returns = np.random.normal(0.001, 0.02, periods)
    prices = base_price * (1 + returns).cumprod()
    
    df = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.005, periods)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, periods))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, periods))),
        'close': prices,
    }, index=dates)
    
    # Ensure high is highest and low is lowest
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


def _create_sample_volume_data(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """Create sample volume data for testing"""
    import numpy as np
    
    periods = 100
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='D')
    
    base_volume = 1000000
    volumes = base_volume * (1 + np.random.normal(0, 0.3, periods))
    volumes = np.abs(volumes).astype(int)
    
    df = pd.DataFrame({
        'volume': volumes
    }, index=dates)
    
    return df


def _create_sample_options_data(symbol: str) -> pd.DataFrame:
    """Create sample options data for testing"""
    import numpy as np
    from datetime import timedelta
    
    strikes = np.arange(95, 106, 1)
    expirations = [datetime.now() + timedelta(days=d) for d in [7, 14, 30, 60]]
    
    data = []
    for strike in strikes:
        for expiration in expirations:
            for option_type in ['call', 'put']:
                volume = np.random.randint(100, 10000)
                avg_volume = volume * np.random.uniform(0.3, 0.7)
                
                data.append({
                    'strike': strike,
                    'expiration': expiration,
                    'option_type': option_type,
                    'volume': volume,
                    'open_interest': np.random.randint(500, 5000),
                    'avg_volume': avg_volume,
                    'premium': np.random.uniform(0.5, 10.0),
                    'implied_volatility': np.random.uniform(0.2, 0.8),
                    'delta': np.random.uniform(0.1, 0.9) if option_type == 'call' else np.random.uniform(-0.9, -0.1)
                })
    
    return pd.DataFrame(data)
