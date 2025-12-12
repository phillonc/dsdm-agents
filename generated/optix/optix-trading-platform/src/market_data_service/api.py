"""
Market Data Service REST API
Real-time quotes, options chains, and market data endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket
from typing import List, Optional
from datetime import date, datetime, timedelta
from .models import Quote, OptionsChain, OptionsExpirations, HistoricalBar
from .provider import MarketDataProvider, MockMarketDataProvider
from .cache import MarketDataCache
import asyncio
import json


router = APIRouter(prefix="/api/v1", tags=["market-data"])


# Dependency injection
def get_market_data_provider() -> MarketDataProvider:
    """Get market data provider instance"""
    # In production, select provider based on config
    return MockMarketDataProvider()


def get_market_data_cache() -> MarketDataCache:
    """Get market data cache instance"""
    return MarketDataCache()


@router.get("/quotes/{symbol}", response_model=Quote)
async def get_quote(
    symbol: str,
    provider: MarketDataProvider = Depends(get_market_data_provider),
    cache: MarketDataCache = Depends(get_market_data_cache)
):
    """
    Get real-time quote for a symbol
    
    - **symbol**: Stock or ETF ticker symbol (e.g., AAPL, SPY)
    - Returns quote with bid/ask, volume, and price changes
    - Data cached for 1 second for performance
    """
    # Check cache first
    cached_quote = cache.get_quote(symbol)
    if cached_quote:
        return cached_quote
    
    # Fetch from provider
    quote = await provider.get_quote(symbol.upper())
    
    # Cache for 1 second
    cache.set_quote(symbol, quote, ttl=1)
    
    return quote


@router.get("/quotes", response_model=List[Quote])
async def get_quotes_batch(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    provider: MarketDataProvider = Depends(get_market_data_provider)
):
    """
    Get real-time quotes for multiple symbols
    
    - **symbols**: Comma-separated ticker symbols (e.g., AAPL,MSFT,GOOGL)
    - Maximum 50 symbols per request
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    if len(symbol_list) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 symbols allowed per request"
        )
    
    quotes = await provider.get_quotes_batch(symbol_list)
    return quotes


@router.get("/options/expirations/{symbol}", response_model=OptionsExpirations)
async def get_options_expirations(
    symbol: str,
    provider: MarketDataProvider = Depends(get_market_data_provider),
    cache: MarketDataCache = Depends(get_market_data_cache)
):
    """
    Get available option expiration dates for a symbol
    
    - **symbol**: Underlying stock symbol
    - Returns list of available expiration dates
    - Data cached for 1 hour
    """
    # Check cache
    cached = cache.get_expirations(symbol)
    if cached:
        return cached
    
    # Fetch from provider
    expirations = await provider.get_options_expirations(symbol.upper())
    
    # Cache for 1 hour
    cache.set_expirations(symbol, expirations, ttl=3600)
    
    return expirations


@router.get("/options/chain/{symbol}", response_model=OptionsChain)
async def get_options_chain(
    symbol: str,
    expiration: date = Query(..., description="Expiration date (YYYY-MM-DD)"),
    provider: MarketDataProvider = Depends(get_market_data_provider),
    cache: MarketDataCache = Depends(get_market_data_cache)
):
    """
    Get full options chain for a specific expiration
    
    - **symbol**: Underlying stock symbol
    - **expiration**: Expiration date in YYYY-MM-DD format
    - Returns calls and puts with Greeks, IV, volume, and OI
    - Data cached for 5 seconds during market hours
    
    **Performance**: p95 < 2 seconds (NFR requirement)
    """
    # Check cache
    cache_key = f"{symbol}:{expiration}"
    cached = cache.get_chain(cache_key)
    if cached:
        return cached
    
    # Fetch from provider
    chain = await provider.get_options_chain(symbol.upper(), expiration)
    
    # Cache for 5 seconds
    cache.set_chain(cache_key, chain, ttl=5)
    
    return chain


@router.get("/historical/{symbol}", response_model=List[HistoricalBar])
async def get_historical_data(
    symbol: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
    timeframe: str = Query("1D", description="Timeframe: 1m, 5m, 15m, 1H, 1D"),
    provider: MarketDataProvider = Depends(get_market_data_provider)
):
    """
    Get historical OHLCV data
    
    - **symbol**: Stock or ETF symbol
    - **start_date**: Start date for historical data
    - **end_date**: End date (optional, defaults to today)
    - **timeframe**: Bar timeframe (1m, 5m, 15m, 1H, 1D)
    - Maximum 2 years of data
    """
    if end_date is None:
        end_date = date.today()
    
    # Validate date range
    if (end_date - start_date).days > 730:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 2 years of historical data allowed"
        )
    
    # Convert to datetime
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    bars = await provider.get_historical_bars(
        symbol.upper(),
        start_dt,
        end_dt,
        timeframe
    )
    
    return bars


@router.websocket("/ws/quotes")
async def websocket_quotes(
    websocket: WebSocket,
    provider: MarketDataProvider = Depends(get_market_data_provider)
):
    """
    WebSocket endpoint for real-time quote streaming
    
    **Protocol:**
    1. Connect to /ws/quotes
    2. Send: {"action": "subscribe", "symbols": ["AAPL", "MSFT"]}
    3. Receive: Real-time quote updates as JSON
    4. Send: {"action": "unsubscribe", "symbols": ["AAPL"]}
    
    **Latency**: < 500ms from source (NFR-002)
    """
    await websocket.accept()
    
    subscribed_symbols = set()
    
    try:
        while True:
            # Receive subscription commands
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            symbols = message.get("symbols", [])
            
            if action == "subscribe":
                subscribed_symbols.update(s.upper() for s in symbols)
                await websocket.send_json({
                    "type": "subscribed",
                    "symbols": list(subscribed_symbols)
                })
                
                # Start streaming quotes
                asyncio.create_task(
                    stream_quotes(websocket, subscribed_symbols, provider)
                )
            
            elif action == "unsubscribe":
                subscribed_symbols.difference_update(s.upper() for s in symbols)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "symbols": symbols
                })
            
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


async def stream_quotes(
    websocket: WebSocket,
    symbols: set,
    provider: MarketDataProvider
):
    """Stream real-time quotes to WebSocket"""
    while True:
        try:
            if not symbols:
                await asyncio.sleep(1)
                continue
            
            # Fetch quotes for all subscribed symbols
            quotes = await provider.get_quotes_batch(list(symbols))
            
            # Send each quote
            for quote in quotes:
                await websocket.send_json({
                    "type": "quote",
                    "data": quote.dict()
                })
            
            # Rate limit: update every 100ms for real-time feel
            await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"Streaming error: {e}")
            break
