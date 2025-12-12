"""Historical data API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request

from src.services import StorageService
from src.models.schemas import HistoricalGEX

router = APIRouter()


def get_storage(request: Request) -> StorageService:
    """Get storage service from app state."""
    return request.app.state.storage


@router.get("/{symbol}", response_model=List[HistoricalGEX])
async def get_historical_gex(
    symbol: str,
    days: int = 30,
    storage: StorageService = Depends(get_storage)
) -> List[HistoricalGEX]:
    """
    Get historical GEX data for a symbol.
    
    Args:
        symbol: Underlying symbol
        days: Number of days to retrieve (default 30)
        storage: Storage service (injected)
        
    Returns:
        List of historical GEX data points
    """
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400,
                detail="Days parameter must be between 1 and 365"
            )
        
        historical_data = await storage.get_historical_gex(symbol=symbol, days=days)
        
        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data found for symbol {symbol}"
            )
        
        return historical_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve historical data: {str(e)}"
        )


@router.get("/{symbol}/summary")
async def get_historical_summary(
    symbol: str,
    days: int = 30,
    storage: StorageService = Depends(get_storage)
) -> dict:
    """
    Get statistical summary of historical GEX data.
    
    Args:
        symbol: Underlying symbol
        days: Number of days to analyze (default 30)
        storage: Storage service (injected)
        
    Returns:
        Statistical summary of historical data
    """
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400,
                detail="Days parameter must be between 1 and 365"
            )
        
        historical_data = await storage.get_historical_gex(symbol=symbol, days=days)
        
        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data found for symbol {symbol}"
            )
        
        # Calculate statistics
        total_gex_values = [h.total_gex for h in historical_data]
        call_gex_values = [h.call_gex for h in historical_data]
        put_gex_values = [h.put_gex for h in historical_data]
        
        import statistics
        
        return {
            "symbol": symbol,
            "period_days": days,
            "data_points": len(historical_data),
            "total_gex": {
                "current": total_gex_values[0] if total_gex_values else None,
                "average": statistics.mean(total_gex_values),
                "median": statistics.median(total_gex_values),
                "min": min(total_gex_values),
                "max": max(total_gex_values),
                "std_dev": statistics.stdev(total_gex_values) if len(total_gex_values) > 1 else 0
            },
            "call_gex": {
                "average": statistics.mean(call_gex_values),
                "min": min(call_gex_values),
                "max": max(call_gex_values)
            },
            "put_gex": {
                "average": statistics.mean(put_gex_values),
                "min": min(put_gex_values),
                "max": max(put_gex_values)
            },
            "regime_distribution": _calculate_regime_distribution(historical_data),
            "latest_timestamp": historical_data[0].timestamp.isoformat() if historical_data else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate historical summary: {str(e)}"
        )


@router.get("/{symbol}/chart")
async def get_chart_data(
    symbol: str,
    days: int = 30,
    storage: StorageService = Depends(get_storage)
) -> dict:
    """
    Get historical data formatted for charting.
    
    Args:
        symbol: Underlying symbol
        days: Number of days to retrieve (default 30)
        storage: Storage service (injected)
        
    Returns:
        Chart-ready data structure
    """
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400,
                detail="Days parameter must be between 1 and 365"
            )
        
        historical_data = await storage.get_historical_gex(symbol=symbol, days=days)
        
        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data found for symbol {symbol}"
            )
        
        # Reverse to get chronological order
        historical_data = list(reversed(historical_data))
        
        return {
            "symbol": symbol,
            "period_days": days,
            "timestamps": [h.timestamp.isoformat() for h in historical_data],
            "spot_prices": [float(h.spot_price) for h in historical_data],
            "total_gex": [h.total_gex for h in historical_data],
            "call_gex": [h.call_gex for h in historical_data],
            "put_gex": [h.put_gex for h in historical_data],
            "gamma_flip_levels": [
                float(h.gamma_flip_level) if h.gamma_flip_level else None
                for h in historical_data
            ],
            "market_regimes": [h.market_regime for h in historical_data]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chart data: {str(e)}"
        )


def _calculate_regime_distribution(historical_data: List[HistoricalGEX]) -> dict:
    """
    Calculate distribution of market regimes.
    
    Args:
        historical_data: List of historical GEX data
        
    Returns:
        Regime distribution dictionary
    """
    regime_counts = {
        "positive_gamma": 0,
        "negative_gamma": 0,
        "near_flip": 0,
        "neutral": 0
    }
    
    for data in historical_data:
        regime = data.market_regime
        if regime in regime_counts:
            regime_counts[regime] += 1
    
    total = len(historical_data)
    
    return {
        "counts": regime_counts,
        "percentages": {
            regime: (count / total * 100) if total > 0 else 0
            for regime, count in regime_counts.items()
        }
    }
