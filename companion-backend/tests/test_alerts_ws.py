from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.microservices.alerts_ws import _handle_event
from app.models import Alert, User
from app.security import hash_password


@pytest.mark.asyncio
async def test_incoming_ws_event_persists_and_broadcasts(db_sessionmaker, monkeypatch):
    mock_broadcast = AsyncMock()
    monkeypatch.setattr('app.microservices.alerts_ws.manager.broadcast', mock_broadcast)

    async with db_sessionmaker() as db:
        db.add(
            User(
                id='u-123',
                email='u123@example.com',
                hashed_password=hash_password('x'),
                full_name='User 123',
                role='elderly',
                consent_given=True,
            )
        )
        await db.commit()

    event = {
        'type': 'alert_escalated',
        'user_id': 'u-123',
        'alert_type': 'fall',
        'severity': 'high',
        'metadata': {'note': 'x'},
        'timestamp': '2026-01-01T00:00:00Z',
    }

    await _handle_event(event, db_sessionmaker)

    async with db_sessionmaker() as db:
        saved = (await db.execute(select(Alert).where(Alert.user_id == 'u-123'))).scalars().first()
        assert saved is not None
        assert saved.alert_type == 'fall'

    assert mock_broadcast.await_count == 1
