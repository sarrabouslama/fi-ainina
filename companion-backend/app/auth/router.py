from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, MeResponse, TokenResponse
from app.auth.service import blacklist_token, login, rotate_refresh_token
from app.database import get_db
from app.models import User
from app.security import hash_password
from app.users.schemas import UserCreate, UserResponse


router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=UserResponse, status_code=201)
async def register_route(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail='Email déjà utilisé')
    user = User(
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        consent_given=payload.consent_given,
        consent_date=datetime.now(timezone.utc) if payload.consent_given else None,
        preferences=payload.preferences,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    from app.users.router import to_response
    return to_response(user)


@router.post('/login', response_model=TokenResponse)
async def login_route(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    access, refresh = await login(db, payload.email, payload.password)
    response.set_cookie('refresh_token', refresh, httponly=True, samesite='lax', secure=False)
    return TokenResponse(access_token=access)


@router.post('/refresh', response_model=TokenResponse)
async def refresh_route(response: Response, refresh_token: str | None = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail='Missing refresh cookie')
    access, refresh, _ = await rotate_refresh_token(refresh_token)
    response.set_cookie('refresh_token', refresh, httponly=True, samesite='lax', secure=False)
    return TokenResponse(access_token=access)


@router.post('/logout')
async def logout_route(refresh_token: str | None = Cookie(default=None), user: User = Depends(get_current_user)):
    if refresh_token:
        await blacklist_token(refresh_token)
    return {'ok': True, 'user_id': user.id}


@router.get('/me', response_model=MeResponse)
async def me_route(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        consent_given=user.consent_given,
        consent_date=user.consent_date.isoformat() if user.consent_date else None,
    )
