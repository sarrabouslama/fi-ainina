from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, redis_client
from app.models import User
from app.security import decode_token


bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = None
    if creds:
        token = creds.credentials
    if not token:
        raise HTTPException(status_code=401, detail='Missing token')
    payload = decode_token(token)
    if payload.get('type') != 'access':
        raise HTTPException(status_code=401, detail='Invalid token type')
    if await redis_client.get(f"blacklist:{payload['jti']}"):
        raise HTTPException(status_code=401, detail='Token revoked')
    user = (await db.execute(select(User).where(User.id == payload['sub']))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail='User inactive')
    request.state.user = user
    return user


def require_role(*roles: str):
    async def _inner(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail='Forbidden')
        return user

    return _inner
