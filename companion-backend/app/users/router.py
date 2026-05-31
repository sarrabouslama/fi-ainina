from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models import ConversationMessage, ConversationSession, User
from app.security import hash_password
from app.users.schemas import ConsentUpdate, UserCreate, UserResponse, UserUpdate


router = APIRouter(prefix='/users', tags=['users'])


def to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        consent_given=user.consent_given,
        consent_date=user.consent_date,
        preferences=user.preferences,
    )


@router.post('', response_model=UserResponse, dependencies=[Depends(require_role('admin'))])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail='Email exists')
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        preferences=payload.preferences,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return to_response(user)


@router.get('', response_model=list[UserResponse], dependencies=[Depends(require_role('admin'))])
async def list_users(db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(User))).scalars().all()
    return [to_response(u) for u in users]


@router.get('/{user_id}', response_model=UserResponse)
async def get_user(user_id: str, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current.role != 'admin' and current.id != user_id:
        raise HTTPException(status_code=403, detail='Forbidden')
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='Not found')
    return to_response(user)


@router.patch('/{user_id}', response_model=UserResponse)
async def patch_user(user_id: str, payload: UserUpdate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current.role != 'admin' and current.id != user_id:
        raise HTTPException(status_code=403, detail='Forbidden')
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='Not found')

    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return to_response(user)


@router.delete('/{user_id}', dependencies=[Depends(require_role('admin'))])
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='Not found')
    await db.delete(user)
    await db.commit()
    return {'ok': True}


@router.post('/{user_id}/consent', response_model=UserResponse)
async def update_consent(user_id: str, payload: ConsentUpdate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current.role != 'admin' and current.id != user_id:
        raise HTTPException(status_code=403, detail='Forbidden')
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='Not found')
    user.consent_given = payload.consent_given
    user.consent_date = datetime.utcnow() if payload.consent_given else None
    await db.commit()
    await db.refresh(user)
    return to_response(user)


@router.delete('/{user_id}/data')
async def gdpr_erase(user_id: str, current: User = Depends(require_role('admin')), db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='Not found')

    user.email = f'deleted-{user.id}@example.invalid'
    user.full_name = '[deleted]'
    user.preferences = None
    user.is_active = False

    messages = (
        await db.execute(
            select(ConversationMessage)
            .join(ConversationSession, ConversationSession.id == ConversationMessage.session_id)
            .where(ConversationSession.user_id == user_id)
        )
    ).scalars().all()
    for msg in messages:
        msg.content = '[deleted]'

    from app.models import Alert

    alerts = (await db.execute(select(Alert).where(Alert.user_id == user_id))).scalars().all()
    for alert in alerts:
        if alert.metadata_json:
            scrubbed = dict(alert.metadata_json)
            for pii in ('name', 'email', 'phone', 'address'):
                scrubbed.pop(pii, None)
            alert.metadata_json = scrubbed

    await db.commit()
    return {'ok': True, 'user_id': user_id}
