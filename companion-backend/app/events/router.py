from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.events.manager import WSContext, manager
from app.enums import UserRole
from app.security import decode_token


router = APIRouter(tags=['events'])


@router.websocket('/ws/events')
async def events_ws(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = decode_token(token)
        if payload.get('type') != 'access':
            raise ValueError('wrong token type')
    except Exception:
        # Must accept first before closing — closing without accept sends HTTP 403
        await websocket.accept()
        await websocket.close(code=4001)
        return

    context = WSContext(
        user_id=payload['sub'],
        role=UserRole(payload.get('role', UserRole.elderly.value)),
        assigned_user_ids=set(payload.get('assigned_user_ids', [])),
    )
    await manager.connect(websocket, context)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
