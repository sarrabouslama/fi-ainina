from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.enums import UserRole
from app.events.manager import manager
from app.main_state import health_state
from app.models import ConversationSession, User


router = APIRouter(tags=['health'])


@router.get('/health')
async def health():
    overall = 'healthy' if all(v == 'healthy' for v in health_state.status.values()) else 'degraded'
    return {'overall_status': overall, 'services': health_state.status, 'latency_ms': health_state.latency_ms}


@router.get('/internal/elderly-user-id')
async def get_elderly_user_id(db: AsyncSession = Depends(get_db)):
    """Return the currently connected elderly user, or the most recently active one."""
    # Priority 1: elderly user with an active WebSocket session right now
    async with manager._lock:
        connected = [ctx for ctx in manager._connections.values() if ctx.role == UserRole.elderly]
    if connected:
        ctx = connected[0]
        result = await db.execute(select(User).where(User.id == ctx.user_id))
        user = result.scalar_one_or_none()
        if user:
            return {'user_id': user.id, 'full_name': user.full_name}

    # Priority 2: elderly user with the most recent conversation
    result = await db.execute(
        select(User)
        .join(ConversationSession, ConversationSession.user_id == User.id)
        .where(User.role == UserRole.elderly, User.is_active == True)
        .order_by(ConversationSession.started_at.desc())
        .limit(1)
    )
    user = result.scalars().first()

    # Priority 3: oldest registered elderly (avoids picking newer test accounts)
    if not user:
        result = await db.execute(
            select(User)
            .where(User.role == UserRole.elderly, User.is_active == True)
            .order_by(User.created_at.asc())
        )
        user = result.scalars().first()

    if not user:
        return {'user_id': None, 'full_name': None}
    return {'user_id': user.id, 'full_name': user.full_name}
