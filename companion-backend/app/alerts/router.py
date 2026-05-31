from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Alert


router = APIRouter(prefix='/alerts', tags=['alerts'])


@router.get('')
async def get_alerts(_: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Alert).order_by(Alert.triggered_at.desc()))).scalars().all()
