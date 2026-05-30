import asyncio
import json
from datetime import datetime

import websockets
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.events.manager import manager
from app.logging_utils import logger
from app.models import Alert


async def run_alerts_ws_bridge(alerts_ws_url: str, session_factory: async_sessionmaker[AsyncSession]):
    backoff = 1
    while True:
        try:
            async with websockets.connect(alerts_ws_url) as ws:
                logger.info('Connected to alerts WS bridge')
                backoff = 1
                async for message in ws:
                    event = json.loads(message)
                    await _handle_event(event, session_factory)
        except Exception as exc:
            logger.warning('alerts ws disconnected: %s', exc)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


async def _handle_event(event: dict, session_factory: async_sessionmaker[AsyncSession]):
    async with session_factory() as db:
        alert = Alert(
            user_id=event['user_id'],
            alert_type=event['alert_type'],
            severity=event['severity'],
            status='escalated',
            triggered_at=datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')),
            escalated_at=datetime.utcnow(),
            metadata_json=event.get('metadata') or {},
            notified_contacts={},
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

    outbound = {
        'type': 'alert_escalated',
        'payload': {
            'alert_id': alert.id,
            'user_id': alert.user_id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
        },
    }
    await manager.broadcast(outbound)
