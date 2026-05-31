import pytest

from app.models import User
from app.security import hash_password
from app.enums import UserRole


@pytest.mark.asyncio
async def test_login_refresh_logout_and_me(client):
    login = await client.post('/auth/login', json={'email': 'admin@example.com', 'password': 'adminpass'})
    assert login.status_code == 200
    access = login.json()['access_token']

    me = await client.get('/auth/me', headers={'Authorization': f'Bearer {access}'})
    assert me.status_code == 200
    assert me.json()['role'] == UserRole.admin
    assert me.json()['consent_given'] is True

    refresh = await client.post('/auth/refresh')
    assert refresh.status_code == 200

    logout = await client.post('/auth/logout', headers={'Authorization': f'Bearer {access}'})
    assert logout.status_code == 200


@pytest.mark.asyncio
async def test_login_lockout_after_failed_attempts(client):
    for _ in range(5):
        r = await client.post('/auth/login', json={'email': 'admin@example.com', 'password': 'wrong'})
        assert r.status_code == 401

    locked = await client.post('/auth/login', json={'email': 'admin@example.com', 'password': 'adminpass'})
    assert locked.status_code == 429


@pytest.mark.asyncio
async def test_auth_me_returns_false_when_consent_not_given(client, db_sessionmaker):
    async with db_sessionmaker() as db:
        db.add(
            User(
                email='noconsent@example.com',
                hashed_password=hash_password('noconsentpass'),
                full_name='No Consent',
                role=UserRole.elderly,
                consent_given=False,
            )
        )
        await db.commit()

    login = await client.post('/auth/login', json={'email': 'noconsent@example.com', 'password': 'noconsentpass'})
    assert login.status_code == 200
    access = login.json()['access_token']

    me = await client.get('/auth/me', headers={'Authorization': f'Bearer {access}'})
    assert me.status_code == 200
    assert me.json()['consent_given'] is False
