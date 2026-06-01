from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models import ConversationMessage, ConversationSession, PersonWatcher, User
from app.security import hash_password
from app.users.schemas import ConsentUpdate, UserCreate, UserResponse, UserUpdate
from app.enums import UserRole


router = APIRouter(prefix='/users', tags=['users'])


def to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        consent_given=user.consent_given,
        consent_date=user.consent_date,
        preferences=user.preferences,
    )


@router.post('', response_model=UserResponse, dependencies=[Depends(require_role(UserRole.admin))])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail='Email exists')
    user = User(
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        preferences=payload.preferences,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return to_response(user)


@router.get('', response_model=list[UserResponse], dependencies=[Depends(require_role(UserRole.admin))])
async def list_users(db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(User))).scalars().all()
    return [to_response(u) for u in users]


@router.get('/{user_id}', response_model=UserResponse)
async def get_user(user_id: str, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current.role != UserRole.admin and current.id != user_id:
        raise HTTPException(status_code=403, detail='Forbidden')
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='Not found')
    return to_response(user)


@router.patch('/{user_id}', response_model=UserResponse)
async def patch_user(user_id: str, payload: UserUpdate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current.role != UserRole.admin and (current.id != user_id or not current.consent_given):
        raise HTTPException(status_code=403, detail='Forbidden')
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='Not found')

    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return to_response(user)


@router.get('/{user_id}/caregiver')
async def get_caregiver_for_user(user_id: str, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the caregiver assigned to an elderly user (via person_watchers or preferences fallback)."""
    # 1. Try person_watchers table first (canonical)
    row = (await db.execute(
        select(User).join(PersonWatcher, PersonWatcher.user_id == User.id)
        .where(PersonWatcher.person_id == user_id)
    )).scalar_one_or_none()
    if row:
        return {'id': row.id, 'full_name': row.full_name, 'phone': row.phone}

    # 2. Fallback: scan caregiver preferences for assigned_user_ids
    caregivers = (await db.execute(select(User).where(User.role == UserRole.caregiver))).scalars().all()
    for c in caregivers:
        if user_id in ((c.preferences or {}).get('assigned_user_ids') or []):
            return {'id': c.id, 'full_name': c.full_name, 'phone': c.phone}
    return None


@router.post('/{caregiver_id}/assign/{elderly_id}', dependencies=[Depends(require_role(UserRole.admin))])
async def assign_caregiver(caregiver_id: str, elderly_id: str, db: AsyncSession = Depends(get_db)):
    """Assign an elderly user to a caregiver (writes to person_watchers + preferences)."""
    caregiver = (await db.execute(select(User).where(User.id == caregiver_id))).scalar_one_or_none()
    elderly = (await db.execute(select(User).where(User.id == elderly_id))).scalar_one_or_none()
    if not caregiver or not elderly:
        raise HTTPException(status_code=404, detail='User not found')

    # Write to person_watchers
    existing = (await db.execute(
        select(PersonWatcher).where(PersonWatcher.user_id == caregiver_id, PersonWatcher.person_id == elderly_id)
    )).scalar_one_or_none()
    if not existing:
        db.add(PersonWatcher(user_id=caregiver_id, person_id=elderly_id))

    # Also keep preferences in sync
    prefs = dict(caregiver.preferences or {})
    assigned = list(prefs.get('assigned_user_ids') or [])
    if elderly_id not in assigned:
        assigned.append(elderly_id)
    prefs['assigned_user_ids'] = assigned
    caregiver.preferences = prefs

    await db.commit()
    return {'ok': True}


@router.delete('/{caregiver_id}/assign/{elderly_id}', dependencies=[Depends(require_role(UserRole.admin))])
async def unassign_caregiver(caregiver_id: str, elderly_id: str, db: AsyncSession = Depends(get_db)):
    """Remove the assignment between a caregiver and elderly user."""
    pw = (await db.execute(
        select(PersonWatcher).where(PersonWatcher.user_id == caregiver_id, PersonWatcher.person_id == elderly_id)
    )).scalar_one_or_none()
    if pw:
        await db.delete(pw)

    caregiver = (await db.execute(select(User).where(User.id == caregiver_id))).scalar_one_or_none()
    if caregiver:
        prefs = dict(caregiver.preferences or {})
        assigned = [i for i in (prefs.get('assigned_user_ids') or []) if i != elderly_id]
        prefs['assigned_user_ids'] = assigned
        caregiver.preferences = prefs

    await db.commit()
    return {'ok': True}


@router.delete('/{user_id}', dependencies=[Depends(require_role(UserRole.admin))])
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail='Not found')
    await db.delete(user)
    await db.commit()
    return {'ok': True}


@router.post('/{user_id}/consent', response_model=UserResponse)
async def update_consent(user_id: str, payload: ConsentUpdate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current.role != UserRole.admin and current.id != user_id:
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
async def gdpr_erase(user_id: str, current: User = Depends(require_role(UserRole.admin)), db: AsyncSession = Depends(get_db)):
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
