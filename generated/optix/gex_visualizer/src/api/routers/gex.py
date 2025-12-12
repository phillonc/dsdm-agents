"""GEX calculation API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from decimal import Decimal

from src.models.schemas import (
    GEXCalculationRequest,
    GEXCalculationResponse,
    OptionContract,
)
from src.services import GEXService, StorageService, OptionsDataService

router = APIRouter()


def get_storage(request: Request) -> StorageService:
    """Get storage service from app state."""
    return request.app.state.storage


def get_gex_service(storage: StorageService = Depends(get_storage)) -> GEXService:
    """Get GEX service."""
    return GEXService(storage_service=storage)


def get_options_service() -> OptionsDataService:
    """Get options data service."""
    return OptionsDataService()


@router.post("/calculate", response_model=GEXCalculationResponse)
async def calculate_gex(
    request: GEXCalculationRequest,
    gex_service: GEXService = Depends(get_gex_service)
) -> GEXCalculationResponse:
    """
    Calculate gamma exposure (GEX) for options chain.
    
    Performs comprehensive GEX analysis including:
    - Gamma exposure calculations by strike
    - Heatmap visualization data
    - Gamma flip level detection
    - Market maker positioning analysis
    - Pin risk analysis (if requested)
    - Alert generation
    
    Args:
        request: GEX calculation request with options chain data
        gex_service: GEX service (injected)
        
    Returns:
        Complete GEX analysis response
    """
    try:
        response = await gex_service.calculate_gex(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GEX calculation failed: {str(e)}")


@router.get("/calculate/{symbol}", response_model=GEXCalculationResponse)
async def calculate_gex_for_symbol(
    symbol: str,
    spot_price: Decimal,
    calculate_pin_risk: bool = True,
    include_historical: bool = False,
    gex_service: GEXService = Depends(get_gex_service),
    options_service: OptionsDataService = Depends(get_options_service)
) -> GEXCalculationResponse:
    """
    Calculate GEX for a symbol by fetching options chain data.
    
    Automatically fetches the latest options chain data and performs
    comprehensive GEX analysis.
    
    Args:
        symbol: Underlying symbol (e.g., 'SPY', 'QQQ')
        spot_price: Current spot price
        calculate_pin_risk: Include pin risk analysis
        include_historical: Include historical context
        gex_service: GEX service (injected)
        options_service: Options data service (injected)
        
    Returns:
        Complete GEX analysis response
    """
    try:
        # Fetch options chain
        options_chain = await options_service.fetch_options_chain(symbol)
        
        if not options_chain:
            raise HTTPException(
                status_code=404,
                detail=f"No options data found for symbol {symbol}"
            )
        
        # Create calculation request
        request = GEXCalculationRequest(
            symbol=symbol,
            spot_price=spot_price,
            options_chain=options_chain,
            calculate_pin_risk=calculate_pin_risk,
            include_historical=include_historical
        )
        
        # Calculate GEX
        response = await gex_service.calculate_gex(request)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate GEX for {symbol}: {str(e)}"
        )


@router.get("/heatmap/{symbol}")
async def get_gex_heatmap(
    symbol: str,
    gex_service: GEXService = Depends(get_gex_service)
) -> dict:
    """
    Get latest GEX heatmap data for a symbol.
    
    Retrieves the most recent GEX snapshot and formats it for
    visualization.
    
    Args:
        symbol: Underlying symbol
        gex_service: GEX service (injected)
        
    Returns:
        Heatmap visualization data
    """
    try:
        snapshot = await gex_service.storage.get_latest_snapshot(symbol)
        
        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail=f"No GEX data found for symbol {symbol}"
            )
        
        return {
            "symbol": snapshot.symbol,
            "timestamp": snapshot.timestamp.isoformat(),
            "spot_price": str(snapshot.spot_price),
            "strike_data": snapshot.strike_gex_data,
            "total_call_gex": snapshot.total_call_gex,
            "total_put_gex": snapshot.total_put_gex,
            "total_net_gex": snapshot.total_net_gex,
            "gamma_flip_strike": str(snapshot.gamma_flip_strike) if snapshot.gamma_flip_strike else None,
            "market_regime": snapshot.market_regime
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve heatmap for {symbol}: {str(e)}"
        )


@router.get("/gamma-flip/{symbol}")
async def get_gamma_flip_level(
    symbol: str,
    gex_service: GEXService = Depends(get_gex_service)
) -> dict:
    """
    Get current gamma flip level for a symbol.
    
    Args:
        symbol: Underlying symbol
        gex_service: GEX service (injected)
        
    Returns:
        Gamma flip level information
    """
    try:
        snapshot = await gex_service.storage.get_latest_snapshot(symbol)
        
        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail=f"No GEX data found for symbol {symbol}"
            )
        
        return {
            "symbol": snapshot.symbol,
            "timestamp": snapshot.timestamp.isoformat(),
            "spot_price": str(snapshot.spot_price),
            "gamma_flip_strike": str(snapshot.gamma_flip_strike) if snapshot.gamma_flip_strike else None,
            "distance_pct": snapshot.gamma_flip_distance_pct,
            "market_regime": snapshot.market_regime,
            "is_near_flip": abs(snapshot.gamma_flip_distance_pct or 100) <= 5.0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve gamma flip for {symbol}: {str(e)}"
        )


@router.get("/market-maker/{symbol}")
async def get_market_maker_position(
    symbol: str,
    gex_service: GEXService = Depends(get_gex_service)
) -> dict:
    """
    Get market maker positioning for a symbol.
    
    Args:
        symbol: Underlying symbol
        gex_service: GEX service (injected)
        
    Returns:
        Market maker positioning information
    """
    try:
        snapshot = await gex_service.storage.get_latest_snapshot(symbol)
        
        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail=f"No GEX data found for symbol {symbol}"
            )
        
        return {
            "symbol": snapshot.symbol,
            "timestamp": snapshot.timestamp.isoformat(),
            "dealer_gamma_exposure": snapshot.dealer_gamma_exposure,
            "dealer_position": snapshot.dealer_position,
            "hedging_pressure": snapshot.hedging_pressure,
            "is_destabilizing": snapshot.dealer_position == "short_gamma"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve market maker position for {symbol}: {str(e)}"
        )
