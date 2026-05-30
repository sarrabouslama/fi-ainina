import asyncio
from dataclasses import dataclass

from fastapi import WebSocket


@dataclass
class WSContext:
    user_id: str
    role: str
    assigned_user_ids: set[str]


class ConnectionManager:
    def __init__(self):
        self._connections: dict[WebSocket, WSContext] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, context: WSContext):
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = context

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._connections.pop(websocket, None)

    async def broadcast(self, event: dict):
        stale: list[WebSocket] = []
        async with self._lock:
            items = list(self._connections.items())
        for ws, ctx in items:
            if not self._can_see(ctx, event):
                continue
            try:
                await ws.send_json(event)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(ws)

    def _can_see(self, ctx: WSContext, event: dict) -> bool:
        payload = event.get('payload', {})
        user_id = payload.get('user_id')
        if ctx.role == 'admin':
            return True
        if ctx.role == 'caregiver':
            return not user_id or user_id in ctx.assigned_user_ids
        return user_id == ctx.user_id


manager = ConnectionManager()
