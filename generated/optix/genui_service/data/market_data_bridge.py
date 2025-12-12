"""
Market Data Bridge

Provides the interface for injecting real-time market data into generated UIs.
"""

from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import asyncio
import random


class MarketDataBridge:
    """
    Bridge for connecting generated UIs to real-time market data.
    """

    def __init__(self):
        """Initialize the market data bridge."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._mock_mode = True  # Use mock data for demo

    async def request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request data from an endpoint.

        Args:
            endpoint: Data endpoint name
            params: Request parameters

        Returns:
            Data response
        """
        params = params or {}

        if endpoint == "quote":
            return await self._get_quote(params.get("symbol", "AAPL"))

        elif endpoint == "options_chain":
            return await self._get_options_chain(
                params.get("symbol", "AAPL"),
                params.get("expiration"),
            )

        elif endpoint == "options_expirations":
            return await self._get_expirations(params.get("symbol", "AAPL"))

        elif endpoint == "greeks":
            return await self._get_greeks(params.get("positions", []))

        elif endpoint == "portfolio":
            return await self._get_portfolio()

        elif endpoint == "flow":
            return await self._get_flow(params.get("symbol"))

        elif endpoint == "gex":
            return await self._get_gex(params.get("symbol", "SPY"))

        else:
            return {"error": f"Unknown endpoint: {endpoint}"}

    def subscribe(
        self,
        channel: str,
        callback: Callable[[Dict[str, Any]], None]
    ):
        """
        Subscribe to a data channel.

        Args:
            channel: Channel name (e.g., "quote:AAPL")
            callback: Function to call with updates
        """
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    def unsubscribe(
        self,
        channel: str,
        callback: Callable[[Dict[str, Any]], None]
    ):
        """
        Unsubscribe from a data channel.

        Args:
            channel: Channel name
            callback: Callback to remove
        """
        if channel in self._subscribers:
            if callback in self._subscribers[channel]:
                self._subscribers[channel].remove(callback)

    async def _publish(self, channel: str, data: Dict[str, Any]):
        """Publish data to subscribers."""
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    print(f"Error publishing to {channel}: {e}")

    # Mock data generators

    async def _get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get mock quote data."""
        base_prices = {
            "AAPL": 185.50,
            "MSFT": 378.25,
            "GOOGL": 141.80,
            "NVDA": 495.20,
            "SPY": 475.50,
            "QQQ": 405.30,
            "TSLA": 245.60,
        }
        base_price = base_prices.get(symbol, 100.0)
        change = random.uniform(-2, 2)

        return {
            "symbol": symbol,
            "price": round(base_price + change, 2),
            "open": round(base_price - 1, 2),
            "high": round(base_price + 3, 2),
            "low": round(base_price - 2, 2),
            "close": base_price,
            "volume": random.randint(10000000, 50000000),
            "change": round(change, 2),
            "change_percent": round((change / base_price) * 100, 2),
            "bid": round(base_price + change - 0.01, 2),
            "ask": round(base_price + change + 0.01, 2),
            "bid_size": random.randint(100, 500),
            "ask_size": random.randint(100, 500),
            "timestamp": datetime.utcnow().isoformat(),
            "market_status": "open",
        }

    async def _get_options_chain(
        self,
        symbol: str,
        expiration: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get mock options chain data."""
        quote = await self._get_quote(symbol)
        current_price = quote["price"]

        # Generate strikes around current price
        strike_start = int(current_price / 5) * 5 - 15
        strikes = []

        for i in range(7):
            strike = strike_start + (i * 5)
            itm_call = strike < current_price
            itm_put = strike > current_price

            call_delta = max(0.1, min(0.9, 0.5 + (current_price - strike) / 20))
            put_delta = call_delta - 1

            strikes.append({
                "strike": strike,
                "call": {
                    "symbol": f"{symbol}240119C{strike:08.0f}",
                    "bid": round(max(0.05, (current_price - strike) + 2 + random.uniform(-0.5, 0.5)), 2) if itm_call else round(random.uniform(0.1, 3), 2),
                    "ask": round(max(0.10, (current_price - strike) + 2.1 + random.uniform(-0.5, 0.5)), 2) if itm_call else round(random.uniform(0.15, 3.5), 2),
                    "last": round(max(0.08, (current_price - strike) + 2.05 + random.uniform(-0.5, 0.5)), 2) if itm_call else round(random.uniform(0.12, 3.2), 2),
                    "volume": random.randint(100, 5000),
                    "open_interest": random.randint(1000, 20000),
                    "delta": round(call_delta, 2),
                    "gamma": round(random.uniform(0.01, 0.05), 3),
                    "theta": round(random.uniform(-0.15, -0.02), 3),
                    "vega": round(random.uniform(0.1, 0.4), 3),
                    "iv": round(random.uniform(0.20, 0.50), 3),
                },
                "put": {
                    "symbol": f"{symbol}240119P{strike:08.0f}",
                    "bid": round(max(0.05, (strike - current_price) + 2 + random.uniform(-0.5, 0.5)), 2) if itm_put else round(random.uniform(0.1, 3), 2),
                    "ask": round(max(0.10, (strike - current_price) + 2.1 + random.uniform(-0.5, 0.5)), 2) if itm_put else round(random.uniform(0.15, 3.5), 2),
                    "last": round(max(0.08, (strike - current_price) + 2.05 + random.uniform(-0.5, 0.5)), 2) if itm_put else round(random.uniform(0.12, 3.2), 2),
                    "volume": random.randint(100, 5000),
                    "open_interest": random.randint(1000, 20000),
                    "delta": round(put_delta, 2),
                    "gamma": round(random.uniform(0.01, 0.05), 3),
                    "theta": round(random.uniform(-0.15, -0.02), 3),
                    "vega": round(random.uniform(0.1, 0.4), 3),
                    "iv": round(random.uniform(0.20, 0.50), 3),
                },
            })

        return {
            "symbol": symbol,
            "underlying_price": current_price,
            "expiration": expiration or "2024-01-19",
            "days_to_expiration": 38,
            "strikes": strikes,
        }

    async def _get_expirations(self, symbol: str) -> List[str]:
        """Get mock expirations."""
        return [
            "2024-01-19",
            "2024-01-26",
            "2024-02-02",
            "2024-02-16",
            "2024-03-15",
            "2024-06-21",
        ]

    async def _get_greeks(self, positions: List[Dict]) -> Dict[str, Any]:
        """Get aggregated Greeks for positions."""
        total_delta = sum(p.get("delta", 0) * p.get("quantity", 1) for p in positions)
        total_gamma = sum(p.get("gamma", 0) * p.get("quantity", 1) for p in positions)
        total_theta = sum(p.get("theta", 0) * p.get("quantity", 1) for p in positions)
        total_vega = sum(p.get("vega", 0) * p.get("quantity", 1) for p in positions)

        return {
            "delta": round(total_delta, 2),
            "gamma": round(total_gamma, 3),
            "theta": round(total_theta, 2),
            "vega": round(total_vega, 2),
        }

    async def _get_portfolio(self) -> Dict[str, Any]:
        """Get mock portfolio data."""
        return {
            "total_value": 125678.50,
            "cash_balance": 15000.00,
            "positions_value": 110678.50,
            "day_change": 1234.56,
            "day_change_percent": 0.99,
            "total_return": 15678.50,
            "total_return_percent": 14.25,
            "greeks": {
                "delta": 125.5,
                "gamma": 8.2,
                "theta": -45.3,
                "vega": 234.1,
            },
        }

    async def _get_flow(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """Get mock unusual flow data."""
        symbols = [symbol] if symbol else ["AAPL", "NVDA", "TSLA", "SPY"]
        flow = []

        for sym in symbols:
            flow.append({
                "symbol": sym,
                "strike": random.randint(150, 200),
                "expiration": "2024-01-19",
                "type": random.choice(["call", "put"]),
                "side": random.choice(["bid", "ask"]),
                "premium": random.randint(100000, 5000000),
                "size": random.randint(100, 5000),
                "classification": random.choice(["directional", "hedge", "spread"]),
                "timestamp": datetime.utcnow().isoformat(),
            })

        return flow

    async def _get_gex(self, symbol: str) -> Dict[str, Any]:
        """Get mock GEX data."""
        quote = await self._get_quote(symbol)
        spot = quote["price"]

        return {
            "symbol": symbol,
            "spot_price": spot,
            "total_gex": {
                "call_gex": 2500000000,
                "put_gex": -1800000000,
                "net_gex": 700000000,
            },
            "gamma_flip_level": round(spot - 3, 2),
            "current_regime": "positive_gamma",
            "calculation_time": datetime.utcnow().isoformat(),
        }


# Create singleton instance
market_data_bridge = MarketDataBridge()
