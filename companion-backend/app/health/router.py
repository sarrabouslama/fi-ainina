from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.enums import UserRole
from app.main_state import health_state
from app.models import User


router = APIRouter(tags=['health'])


@router.get('/health')
async def health():
    overall = 'healthy' if all(v == 'healthy' for v in health_state.status.values()) else 'degraded'
    return {'overall_status': overall, 'services': health_state.status, 'latency_ms': health_state.latency_ms}


@router.get('/internal/elderly-user-id')
async def get_elderly_user_id(db: AsyncSession = Depends(get_db)):
    """Internal endpoint for voice service to fetch the active elderly user's ID."""
    user = (await db.execute(
        select(User)
        .where(User.role == UserRole.elderly, User.is_active == True)
        .order_by(User.created_at.desc())
    )).scalars().first()
    if not user:
        return {'user_id': None, 'full_name': None}
    return {'user_id': user.id, 'full_name': user.full_name}
