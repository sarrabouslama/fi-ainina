"""
WebSocket Handler : manage real-time alert notifications to frontend.

Architecture:
- ConnectionManager: track active WebSocket connections
- broadcast(): send alert to all connected clients
- Server endpoint: @app.websocket("/ws")
"""

import logging
import json
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from app.models import WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections (broadcast to all clients)."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove disconnected client."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: WebSocketMessage):
        """
        Broadcast alert to all connected clients.
        
        Note: All clients receive all alerts. Frontend can filter by user_id/severity as needed.
        """
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return

        message_json = message.model_dump_json()
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

        if len(self.active_connections) > 0:
            logger.debug(f"Broadcast sent to {len(self.active_connections)} WebSocket clients")

    async def send_personal(self, websocket: WebSocket, message: WebSocketMessage):
        """Send message to specific client (for testing)."""
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)


# Global connection manager instance
manager = ConnectionManager()
