import pytest
from sqlalchemy import select
from datetime import datetime, timezone
from uuid import uuid4

from app.models import Alert, ConversationMessage, ConversationSession, User
from app.security import hash_password
from app.enums import UserRole


@pytest.mark.asyncio
async def test_users_crud_and_gdpr_erasure(client, admin_token, db_sessionmaker):
    headers = {'Authorization': f'Bearer {admin_token}'}
    suffix = uuid4().hex[:8]

    standalone_caregiver = await client.post(
        '/users',
        headers=headers,
        json={
            'email': f'standalone-care-{suffix}@example.com',
            'password': 'secure',
            'full_name': 'Standalone Caregiver',
            'role': UserRole.caregiver,
        },
    )
    assert standalone_caregiver.status_code == 400

    elderly_created = await client.post(
        '/users',
        headers=headers,
        json={
            'email': f'elder-{suffix}@example.com',
            'password': 'secure',
            'full_name': 'Elder One',
            'role': UserRole.elderly,
        },
    )
    assert elderly_created.status_code == 200
    assert elderly_created.headers['Location'] == f"/users/{elderly_created.json()['id']}"
    elderly_id = elderly_created.json()['id']

    linked = await client.post(
        f'/users/{elderly_id}/caregivers',
        headers=headers,
        json={
            'email': f'care-{suffix}@example.com',
            'password': 'secure',
            'full_name': 'Care Giver',
            'preferences': {'note': 'primary caregiver'},
        },
    )
    assert linked.status_code == 200
    caregiver_id = linked.json()['id']

    caregivers = await client.get(f'/users/{elderly_id}/caregivers', headers=headers)
    assert caregivers.status_code == 200
    assert any(user['id'] == caregiver_id for user in caregivers.json())

    async with db_sessionmaker() as db:
        caregiver = (await db.execute(select(User).where(User.id == caregiver_id))).scalar_one()
        assert caregiver.preferences['assigned_user_ids'] == [elderly_id]

    consent = await client.post(f'/users/{caregiver_id}/consent', headers=headers, json={'consent_given': True})
    assert consent.status_code == 200
    assert consent.json()['consent_given'] is True

    async with db_sessionmaker() as db:
        now = datetime.now(timezone.utc)
        session = ConversationSession(user_id=caregiver_id, started_at=now, message_count=1)
        db.add(session)
        await db.flush()
        db.add(ConversationMessage(session_id=session.id, role='user', content='secret', timestamp=now))
        db.add(Alert(user_id=caregiver_id, alert_type='emotion', severity='high', status='resolved', triggered_at=now, metadata_json={'email': 'x@y.com'}))
        await db.commit()

    erased = await client.delete(f'/users/{caregiver_id}/data', headers=headers)
    assert erased.status_code == 200

    async with db_sessionmaker() as db:
        user = (await db.execute(select(User).where(User.id == caregiver_id))).scalar_one()
        assert user.full_name == '[deleted]'

        msg = (await db.execute(select(ConversationMessage))).scalars().first()
        assert msg.content == '[deleted]'

        alert = (await db.execute(select(Alert).where(Alert.user_id == caregiver_id))).scalars().first()
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
