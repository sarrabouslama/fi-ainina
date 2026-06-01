from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.enums import UserRole
from app.events.manager import manager
from app.models import Alert, User


router = APIRouter(prefix='/alerts', tags=['alerts'])


class FallAlertPayload(BaseModel):
    event_type: str
    person_id: str | None = 'unknown'
    person_status: str
    action_required: str
    responded: bool = False
    response_text: str | None = None
    message_for_family: str | None = None


@router.post('/fall')
async def receive_fall_alert(payload: FallAlertPayload, db: AsyncSession = Depends(get_db)):
    """Called directly by the voice service when a fall is detected and processed."""
    now = datetime.now(timezone.utc)

    # Find the active elderly user to attach the alert to
    elderly = (await db.execute(
        select(User)
        .where(User.role == UserRole.elderly, User.is_active == True)
        .order_by(User.created_at.desc())
    )).scalars().first()

    severity = 'critical' if payload.action_required == 'emergency' else \
               'high' if payload.action_required == 'verify' else 'low'

    resident_name = elderly.full_name if elderly else 'Le résident'

    # Enrich message with the resident's real name
    enriched_message = payload.message_for_family or ''
    if elderly and 'La personne' in enriched_message:
        enriched_message = enriched_message.replace('La personne', resident_name)

    if elderly:
        alert = Alert(
            user_id=elderly.id,
            alert_type=payload.event_type,
            severity=severity,
            status='pending',
            triggered_at=now,
            metadata_json={
                'source': 'fall_detection',
                'person_status': payload.person_status,
                'response_text': payload.response_text,
                'message_for_family': enriched_message,
                'message': f'{resident_name} — chute détectée ({payload.person_status})',
            },
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        alert_id = alert.id
    else:
        alert_id = None

    # Broadcast immediately to all connected staff via WebSocket
    await manager.broadcast({
        'type': 'alert_escalated',
        'payload': {
            'event_type': payload.event_type,
            'person_status': payload.person_status,
            'full_name': resident_name,
            'action_required': payload.action_required,
            'severity': severity,
            'response_text': f'{resident_name} — {payload.response_text}' if payload.response_text else None,
            'message_for_family': enriched_message,
            '_ts': now.isoformat(),
            'alert_id': alert_id,
        }
    })
    return {'ok': True, 'alert_id': alert_id}


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
