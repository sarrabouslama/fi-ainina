from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import redis_client
from app.models import User
from app.security import create_access_token, create_refresh_token, decode_token, verify_password


async def login(db: AsyncSession, email: str, password: str) -> tuple[str, str]:
    lock_key = f'lockout:{email}'
    fail_key = f'fails:{email}'

    if await redis_client.get(lock_key):
        raise HTTPException(status_code=429, detail='Account locked. Try later.')

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        fails = await redis_client.incr(fail_key)
        await redis_client.expire(fail_key, 15 * 60)
        if fails >= 5:
            await redis_client.setex(lock_key, 15 * 60, '1')
        raise HTTPException(status_code=401, detail='Invalid credentials')

    await redis_client.delete(fail_key)
    return create_access_token(user.id, user.role), create_refresh_token(user.id, user.role)


async def rotate_refresh_token(refresh_token: str) -> tuple[str, str, dict]:
    payload = decode_token(refresh_token)
    if payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail='Invalid refresh token')

    if await redis_client.get(f"blacklist:{payload['jti']}"):
        raise HTTPException(status_code=401, detail='Refresh token revoked')

    ttl = int(timedelta(days=settings.refresh_token_days).total_seconds())
    await redis_client.setex(f"blacklist:{payload['jti']}", ttl, '1')

    access = create_access_token(payload['sub'], payload['role'])
    refresh = create_refresh_token(payload['sub'], payload['role'])
    return access, refresh, payload


async def blacklist_token(token: str):
    payload = decode_token(token)
    exp = int(payload['exp'])
    import time

    ttl = max(exp - int(time.time()), 1)
    await redis_client.setex(f"blacklist:{payload['jti']}", ttl, '1')
