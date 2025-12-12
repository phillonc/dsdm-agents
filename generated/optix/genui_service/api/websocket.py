"""
WebSocket endpoint for real-time data updates in generated UIs.
"""

import asyncio
import json
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException
from ..models.schemas import WSConnectionResponse, WSDataUpdate


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        # Map of generation_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of generation_id -> set of subscribed channels
        self.subscriptions: Dict[str, Set[str]] = {}
        # Mock data update tasks
        self._update_tasks: Dict[str, asyncio.Task] = {}

    async def connect(
        self,
        websocket: WebSocket,
        generation_id: str,
        channels: list[str],
    ):
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            generation_id: Generation ID being subscribed to
            channels: Initial channels to subscribe
        """
        await websocket.accept()

        if generation_id not in self.active_connections:
            self.active_connections[generation_id] = set()
            self.subscriptions[generation_id] = set()

        self.active_connections[generation_id].add(websocket)
        self.subscriptions[generation_id].update(channels)

        # Send connection confirmation
        response = WSConnectionResponse(
            type="connected",
            generation_id=generation_id,
            subscriptions=list(self.subscriptions[generation_id]),
        )
        await websocket.send_json(response.model_dump())

        # Start mock data updates for demo
        if generation_id not in self._update_tasks:
            self._update_tasks[generation_id] = asyncio.create_task(
                self._send_mock_updates(generation_id)
            )

    async def disconnect(self, websocket: WebSocket, generation_id: str):
        """
        Handle WebSocket disconnection.

        Args:
            websocket: The WebSocket connection
            generation_id: Generation ID
        """
        if generation_id in self.active_connections:
            self.active_connections[generation_id].discard(websocket)

            # Clean up if no more connections
            if not self.active_connections[generation_id]:
                del self.active_connections[generation_id]
                if generation_id in self.subscriptions:
                    del self.subscriptions[generation_id]
                if generation_id in self._update_tasks:
                    self._update_tasks[generation_id].cancel()
                    del self._update_tasks[generation_id]

    async def subscribe(
        self,
        generation_id: str,
        channel: str,
        websocket: WebSocket,
    ):
        """
        Subscribe to a data channel.

        Args:
            generation_id: Generation ID
            channel: Channel to subscribe to
            websocket: The WebSocket connection
        """
        if generation_id in self.subscriptions:
            self.subscriptions[generation_id].add(channel)
            await websocket.send_json({
                "type": "subscribed",
                "channel": channel,
            })

    async def unsubscribe(
        self,
        generation_id: str,
        channel: str,
        websocket: WebSocket,
    ):
        """
        Unsubscribe from a data channel.

        Args:
            generation_id: Generation ID
            channel: Channel to unsubscribe from
            websocket: The WebSocket connection
        """
        if generation_id in self.subscriptions:
            self.subscriptions[generation_id].discard(channel)
            await websocket.send_json({
                "type": "unsubscribed",
                "channel": channel,
            })

    async def broadcast(
        self,
        generation_id: str,
        channel: str,
        data: dict,
    ):
        """
        Broadcast data update to all connections for a generation.

        Args:
            generation_id: Generation ID
            channel: Data channel
            data: Data to broadcast
        """
        if generation_id not in self.active_connections:
            return

        if generation_id in self.subscriptions:
            if channel not in self.subscriptions[generation_id]:
                return

        message = WSDataUpdate(
            type="data_update",
            channel=channel,
            data=data,
            timestamp=datetime.utcnow(),
        )

        disconnected = set()
        for websocket in self.active_connections[generation_id]:
            try:
                await websocket.send_json(message.model_dump(mode='json'))
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws, generation_id)

    async def _send_mock_updates(self, generation_id: str):
        """Send mock data updates for demo purposes."""
        import random

        base_price = 185.50
        try:
            while generation_id in self.active_connections:
                # Simulate price updates
                for channel in list(self.subscriptions.get(generation_id, [])):
                    if channel.startswith("quote:"):
                        symbol = channel.split(":")[1]
                        change = random.uniform(-0.50, 0.50)
                        price = base_price + change

                        await self.broadcast(
                            generation_id,
                            channel,
                            {
                                "symbol": symbol,
                                "price": round(price, 2),
                                "change": round(change, 2),
                                "change_percent": round((change / base_price) * 100, 2),
                                "volume": random.randint(1000000, 5000000),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                await asyncio.sleep(1)  # Update every second

        except asyncio.CancelledError:
            pass


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(
    websocket: WebSocket,
    generation_id: str,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time data updates.

    URL: /ws/genui/{generation_id}?token={token}
    """
    # Validate token (mock validation for demo)
    if not token or token == "invalid":
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Get initial subscriptions from stored generation metadata
    # For demo, use mock channels based on generation_id
    initial_channels = [f"quote:AAPL"]

    try:
        await manager.connect(websocket, generation_id, initial_channels)

        while True:
            try:
                # Receive and process client messages
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "subscribe":
                    channel = data.get("channel")
                    if channel:
                        await manager.subscribe(generation_id, channel, websocket)

                elif action == "unsubscribe":
                    channel = data.get("channel")
                    if channel:
                        await manager.unsubscribe(generation_id, channel, websocket)

                elif action == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "invalid_json",
                    "message": "Invalid JSON message",
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, generation_id)
