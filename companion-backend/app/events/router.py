from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.events.manager import WSContext, manager
from app.security import decode_token


router = APIRouter(tags=['events'])


@router.websocket('/ws/events')
async def events_ws(websocket: WebSocket, token: str = Query(...)):
    try:
        payload = decode_token(token)
        if payload.get('type') != 'access':
            raise ValueError('wrong token')
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid token')

    context = WSContext(
        user_id=payload['sub'],
        role=payload.get('role', 'elderly'),
        assigned_user_ids=set(payload.get('assigned_user_ids', [])),
    )
    await manager.connect(websocket, context)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
