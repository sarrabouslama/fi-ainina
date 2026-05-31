from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import ConversationMessage, ConversationSession


router = APIRouter(prefix='/conversations', tags=['conversations'])


@router.get('/sessions')
async def sessions(_: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(ConversationSession))).scalars().all()


@router.get('/messages/{session_id}')
async def messages(session_id: int, _: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return (
        await db.execute(select(ConversationMessage).where(ConversationMessage.session_id == session_id))
    ).scalars().all()
