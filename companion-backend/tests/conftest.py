import asyncio
import os
import sys
from collections import defaultdict

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

from app.enums import UserRole

class FakeRedis:
    def __init__(self):
        self._store = {}
        self._counters = defaultdict(int)

    async def get(self, key):
        return self._store.get(key)

    async def setex(self, key, ttl, value):
        self._store[key] = value

    async def incr(self, key):
        self._counters[key] += 1
        return self._counters[key]

    async def expire(self, key, ttl):
        return True

    async def delete(self, key):
        self._store.pop(key, None)
        self._counters.pop(key, None)


@pytest_asyncio.fixture
async def db_sessionmaker(monkeypatch):
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    fake_redis = FakeRedis()
    monkeypatch.setattr('app.database.redis_client', fake_redis)
    monkeypatch.setattr('app.auth.dependencies.redis_client', fake_redis)
    monkeypatch.setattr('app.auth.service.redis_client', fake_redis)

    app.router.on_startup.clear()
    app.router.on_shutdown.clear()

    async with session_maker() as session:
        admin = User(
            email='admin@example.com',
            hashed_password=hash_password('adminpass'),
            full_name='Admin',
            role=UserRole.admin,
            consent_given=True,
        )
        elder = User(
            email='elder@example.com',
            hashed_password=hash_password('elderpass'),
            full_name='Elder',
            role=UserRole.elderly,
            consent_given=True,
        )
        session.add_all([admin, elder])
        await session.commit()
        await session.refresh(admin)
        await session.refresh(elder)

    yield session_maker

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_sessionmaker):
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        yield c


@pytest_asyncio.fixture
async def admin_token(client):
    resp = await client.post('/auth/login', json={'email': 'admin@example.com', 'password': 'adminpass'})
    assert resp.status_code == 200
    return resp.json()['access_token']


@pytest_asyncio.fixture
async def elder_token(client):
    resp = await client.post('/auth/login', json={'email': 'elder@example.com', 'password': 'elderpass'})
    assert resp.status_code == 200
    return resp.json()['access_token']
