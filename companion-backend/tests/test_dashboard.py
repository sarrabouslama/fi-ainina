import pytest
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import Alert, User
from app.security import hash_password
from app.main_state import health_state
from app.enums import UserRole


@pytest.mark.asyncio
async def test_dashboard_overview_with_mocked_health(client, elder_token):
    health_state.status.update({'alerts': 'healthy', 'llm': 'healthy', 'voice_assistant': 'healthy'})
    resp = await client.get('/dashboard/overview', headers={'Authorization': f'Bearer {elder_token}'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['role'] == UserRole.elderly
    assert body['services_health']['llm'] == 'healthy'
    assert 'today_stats' in body


@pytest.mark.asyncio
async def test_dashboard_overview_is_scoped_by_role(client, admin_token, db_sessionmaker):
    now = datetime.now(timezone.utc)
    async with db_sessionmaker() as db:
        caregiver = User(
            email='caregiver@example.com',
            hashed_password=hash_password('x'),
            full_name='Care Giver',
            role=UserRole.caregiver,
            consent_given=True,
            preferences={'assigned_user_ids': ['elder-1']},
        )
        elder = User(
            id='elder-1',
            email='elder-1@example.com',
            hashed_password='x',
            full_name='Elder One',
            role=UserRole.elderly,
            consent_given=True,
        )
        db.add_all([caregiver, elder])
        await db.flush()
        db.add(Alert(user_id='elder-1', alert_type='fall', severity='high', status='pending', triggered_at=now))
        await db.commit()

    caregiver_login = await client.post('/auth/login', json={'email': 'caregiver@example.com', 'password': 'x'})
    assert caregiver_login.status_code == 200
    caregiver_token = caregiver_login.json()['access_token']

    caregiver_resp = await client.get('/dashboard/overview', headers={'Authorization': f'Bearer {caregiver_token}'})
    assert caregiver_resp.status_code == 200
    caregiver_body = caregiver_resp.json()
    assert caregiver_body['role'] == UserRole.caregiver
    assert caregiver_body['scope']['type'] == 'assigned'
    assert any(user['id'] == 'elder-1' for user in caregiver_body['users'])

    admin_resp = await client.get('/dashboard/overview', headers={'Authorization': f'Bearer {admin_token}'})
    assert admin_resp.status_code == 200
    admin_body = admin_resp.json()
    assert admin_body['role'] == UserRole.admin
    assert admin_body['scope']['type'] == 'global'
    assert 'user_stats' in admin_body
