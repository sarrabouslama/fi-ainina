from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.enums import UserRole
from app.events.manager import manager
from app.models import Alert, User


router = APIRouter(prefix='/alerts', tags=['alerts'])


@router.get('')
async def get_alerts(_: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Alert).order_by(Alert.triggered_at.desc()))).scalars().all()


@router.patch('/{alert_id}/resolve')
async def resolve_alert(
    alert_id: int,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current.role not in (UserRole.admin, UserRole.caregiver):
        raise HTTPException(status_code=403, detail='Forbidden')
    alert = (await db.execute(select(Alert).where(Alert.id == alert_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail='Alert not found')
    alert.status = 'resolved'
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {'ok': True}


@router.post('/emergency')
async def trigger_emergency(
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Elderly user triggers a manual emergency alert."""
    now = datetime.now(timezone.utc)

    alert = Alert(
        user_id=current.id,
        alert_type='manual_emergency',
        severity='critical',
        status='pending',
        triggered_at=now,
        metadata_json={
            'source': 'emergency_button',
            'message': f'{current.full_name} a appuyé sur le bouton d\'urgence',
        },
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    # Broadcast via WebSocket so admin/caregiver sees it instantly
    await manager.broadcast({
        'type': 'alert_escalated',
        'payload': {
            'event_type': 'fall_detected',
            'person_status': 'needs_help',
            'action_required': 'emergency',
            'user_id': current.id,
            'full_name': current.full_name,
            'severity': 'critical',
            'response_text': f'{current.full_name} a besoin d\'aide — urgence déclenchée manuellement.',
            'message_for_family': 'Le résident a appuyé sur le bouton d\'urgence. Intervention immédiate requise.',
            '_ts': now.isoformat(),
            'alert_id': alert.id,
        }
    })

    return {'ok': True, 'alert_id': alert.id}
