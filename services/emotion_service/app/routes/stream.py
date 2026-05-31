"""WebSocket stream for live emotion state updates."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.routes.status import StatusResponse
from app.state import get_state_store

router = APIRouter(tags=["emotion"])


@router.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    """Push the latest state to connected clients once per second."""
    await websocket.accept()
    try:
        while True:
            snapshot = get_state_store().snapshot()
            response = StatusResponse(**snapshot.as_dict())
            await websocket.send_json(response.model_dump(mode="json"))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return