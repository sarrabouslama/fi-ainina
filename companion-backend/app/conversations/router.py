from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.enums import UserRole
from app.models import ConversationMessage, ConversationSession, User


router = APIRouter(prefix='/conversations', tags=['conversations'])


# ── Pydantic response schemas ─────────────────────────────────────────────────

class SessionOut(BaseModel):
    id: int
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    message_count: int

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class SaveTurnPayload(BaseModel):
    user_id: str
    user_message: str
    assistant_reply: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post('/save')
async def save_turn(payload: SaveTurnPayload, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    session = (await db.execute(
        select(ConversationSession)
        .where(
            ConversationSession.user_id == payload.user_id,
            ConversationSession.ended_at.is_(None),
        )
        .order_by(ConversationSession.started_at.desc())
    )).scalar_one_or_none()

    if not session:
        session = ConversationSession(user_id=payload.user_id, started_at=now, message_count=0)
        db.add(session)
        await db.flush()

    db.add(ConversationMessage(session_id=session.id, role='user', content=payload.user_message, timestamp=now))
    db.add(ConversationMessage(session_id=session.id, role='assistant', content=payload.assistant_reply, timestamp=now))
    session.message_count = (session.message_count or 0) + 2
    await db.commit()
    return {'ok': True}


@router.get('/sessions', response_model=list[SessionOut])
async def sessions(
    user_id: str | None = Query(default=None),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ConversationSession)
    if current.role == UserRole.admin:
        if user_id:
            query = query.where(ConversationSession.user_id == user_id)
    else:
        query = query.where(ConversationSession.user_id == current.id)
    query = query.order_by(ConversationSession.started_at.desc())
    rows = (await db.execute(query)).scalars().all()
    return rows


@router.get('/messages/{session_id}', response_model=list[MessageOut])
async def messages(
    session_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = (await db.execute(
        select(ConversationSession).where(ConversationSession.id == session_id)
    )).scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    if current.role != UserRole.admin and session.user_id != current.id:
        raise HTTPException(status_code=403, detail='Forbidden')

    rows = (await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.timestamp.asc())
    )).scalars().all()
    return rows
