import pytest
from sqlalchemy import select
from datetime import datetime, timezone

from app.models import Alert, ConversationMessage, ConversationSession, User
from app.security import hash_password
from app.enums import UserRole


@pytest.mark.asyncio
async def test_users_crud_and_gdpr_erasure(client, admin_token, db_sessionmaker):
    headers = {'Authorization': f'Bearer {admin_token}'}

    created = await client.post(
        '/users',
        headers=headers,
        json={
            'email': 'care@example.com',
            'password': 'secure',
            'full_name': 'Care Giver',
            'role': UserRole.caregiver,
            'preferences': {'assigned_user_ids': []},
        },
    )
    assert created.status_code == 200
    user_id = created.json()['id']

    consent = await client.post(f'/users/{user_id}/consent', headers=headers, json={'consent_given': True})
    assert consent.status_code == 200
    assert consent.json()['consent_given'] is True

    async with db_sessionmaker() as db:
        now = datetime.now(timezone.utc)
        session = ConversationSession(user_id=user_id, started_at=now, message_count=1)
        db.add(session)
        await db.flush()
        db.add(ConversationMessage(session_id=session.id, role='user', content='secret', timestamp=now))
        db.add(Alert(user_id=user_id, alert_type='emotion', severity='high', status='resolved', triggered_at=now, metadata_json={'email': 'x@y.com'}))
        await db.commit()

    erased = await client.delete(f'/users/{user_id}/data', headers=headers)
    assert erased.status_code == 200

    async with db_sessionmaker() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        assert user.full_name == '[deleted]'

        msg = (await db.execute(select(ConversationMessage))).scalars().first()
        assert msg.content == '[deleted]'

        alert = (await db.execute(select(Alert).where(Alert.user_id == user_id))).scalars().first()
        assert 'email' not in (alert.metadata_json or {})


@pytest.mark.asyncio
async def test_dashboard_remains_read_only_without_consent(client, db_sessionmaker):
    async with db_sessionmaker() as db:
        user = User(
            email='noconsent@example.com',
            hashed_password=hash_password('noconsent'),
            full_name='No Consent',
            role=UserRole.elderly,
            consent_given=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    login = await client.post('/auth/login', json={'email': 'noconsent@example.com', 'password': 'noconsent'})
    assert login.status_code == 200
    token = login.json()['access_token']

    overview = await client.get('/dashboard/overview', headers={'Authorization': f'Bearer {token}'})
    assert overview.status_code == 200

    patch = await client.patch(
        f'/users/{user.id}',
        headers={'Authorization': f'Bearer {token}'},
        json={'full_name': 'Changed Name'},
    )
    assert patch.status_code == 403
