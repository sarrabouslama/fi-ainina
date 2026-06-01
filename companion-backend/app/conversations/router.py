from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.enums import UserRole
from app.models import ConversationMessage, ConversationSession, User


router = APIRouter(prefix='/conversations', tags=['conversations'])


class SaveTurnPayload(BaseModel):
    user_id: str
    user_message: str
    assistant_reply: str


@router.post('/save')
async def save_turn(payload: SaveTurnPayload, db: AsyncSession = Depends(get_db)):
    """Called internally by the LLM service to persist a conversation turn."""
    now = datetime.now(timezone.utc)
    session = (await db.execute(
        select(ConversationSession)
        .where(ConversationSession.user_id == payload.user_id,
               ConversationSession.ended_at == None)
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


@router.get('/sessions')
async def sessions(
    user_id: str | None = Query(default=None),
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ConversationSession)
    if current.role == UserRole.admin:
        # Admin can see all sessions, or filter by a specific user_id
        if user_id:
            query = query.where(ConversationSession.user_id == user_id)
    else:
        # Caregiver and elderly only see their own sessions
        query = query.where(ConversationSession.user_id == current.id)
    query = query.order_by(ConversationSession.started_at.desc())
    return (await db.execute(query)).scalars().all()


@router.get('/messages/{session_id}')
async def messages(
    session_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = (await db.execute(
        select(ConversationSession).where(ConversationSession.id == session_id)
    )).scalar_one_or_none()

    if session and current.role != UserRole.admin and session.user_id != current.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail='Forbidden')

    return (
        await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.timestamp.asc())
        )
    ).scalars().all()
