from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.enums import UserRole
from app.main_state import health_state
from app.models import Alert, ConversationSession, Review, ReviewMessage, User


router = APIRouter(prefix='/dashboard', tags=['dashboard'])


@router.get('/overview')
async def overview(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    scope_user_ids = await _resolve_scope_user_ids(current, db)
    current_user_ids = scope_user_ids or [current.id]
    today = datetime.utcnow().date()

    overview_filters = [Alert.user_id.in_(current_user_ids)] if current.role != UserRole.admin else []

    active_alerts = await _count_alerts(db, overview_filters, ['pending', 'escalated'])
    alerts_today = await _count_alerts(db, overview_filters, triggered_on=today)
    false_pos = await _count_alerts(db, overview_filters, ['false_positive'])
    conv_count = await _count_conversations(db, current_user_ids if current.role != UserRole.admin else None)
    open_reviews = await _count_reviews(db, current, current_user_ids)

    response = {
        'role': current.role,
        'scope': {
            'type': 'global' if current.role == UserRole.admin else ('assigned' if current.role == UserRole.caregiver else 'self'),
            'user_ids': scope_user_ids if current.role != UserRole.admin else None,
        },
        'services_health': dict(health_state.status),
        'active_alerts': active_alerts,
        'today_stats': {
            'conversations': conv_count,
            'alerts_triggered': alerts_today,
            'false_positives': false_pos,
            'open_reviews': open_reviews,
        },
    }

    if current.role == UserRole.admin:
        user_count = (await db.execute(select(func.count(User.id)).where(User.role.in_([UserRole.elderly, UserRole.caregiver])))).scalar_one()
        response['user_stats'] = {'monitored_users': user_count}
        response['review_stats'] = {
            'total_reviews': await _count_reviews(db, current, None, all_reviews=True),
            'open_reviews': open_reviews,
        }
        response['users'] = await _build_user_summaries(db, None)
    elif current.role == UserRole.caregiver:
        response['review_stats'] = {'open_reviews': open_reviews}
        response['users'] = await _build_user_summaries(db, scope_user_ids)
    else:
        response['review_stats'] = {'open_reviews': open_reviews}
        response['users'] = await _build_user_summaries(db, [current.id])

    return response


async def _resolve_scope_user_ids(current: User, db: AsyncSession) -> list[str]:
    if current.role == UserRole.admin:
        return []
    if current.role == UserRole.elderly:
        return [current.id]
    preferences = current.preferences or {}
    assigned = preferences.get('assigned_user_ids') or []
    if assigned:
        return list(assigned)
    return [current.id]


async def _count_alerts(
    db: AsyncSession,
    filters: list,
    statuses: list[str] | None = None,
    triggered_on: date | None = None,
) -> int:
    query = select(func.count(Alert.id))
    if filters:
        for clause in filters:
            query = query.where(clause)
    if statuses is not None:
        query = query.where(Alert.status.in_(statuses))
    if triggered_on is not None:
        query = query.where(func.date(Alert.triggered_at) == triggered_on)
    return (await db.execute(query)).scalar_one()


async def _count_conversations(db: AsyncSession, user_ids: list[str] | None = None) -> int:
    query = select(func.count(ConversationSession.id))
    if user_ids:
        query = query.where(ConversationSession.user_id.in_(user_ids))
    return (await db.execute(query)).scalar_one()


async def _count_reviews(
    db: AsyncSession,
    current: User,
    user_ids: list[str] | None,
    all_reviews: bool = False,
) -> int:
    query = select(func.count(Review.id)).where(Review.status == 'open')
    if not all_reviews and current.role != UserRole.admin:
        if user_ids:
            query = query.where(Review.created_by_user_id.in_(user_ids))
        else:
            query = query.where(Review.created_by_user_id == current.id)
    return (await db.execute(query)).scalar_one()


async def _build_user_summaries(db: AsyncSession, user_ids: list[str] | None):
    query = select(User)
    if user_ids:
        query = query.where(User.id.in_(user_ids))
    users = (await db.execute(query)).scalars().all()

    summaries = []
    for user in users:
        active_alerts = await _count_alerts(db, [Alert.user_id == user.id], ['pending', 'escalated'])
        open_reviews = await _count_reviews(db, user, [user.id])
        latest_alert = (
            await db.execute(
                select(Alert)
                .where(Alert.user_id == user.id)
                .order_by(Alert.triggered_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        summaries.append(
            {
                'id': user.id,
                'full_name': user.full_name,
                'role': user.role,
                'consent_given': user.consent_given,
                'active_alerts': active_alerts,
                'open_reviews': open_reviews,
                'latest_alert': None
                if not latest_alert
                else {
                    'alert_type': latest_alert.alert_type,
                    'severity': latest_alert.severity,
                    'status': latest_alert.status,
                    'triggered_at': latest_alert.triggered_at,
                },
            }
        )

    return summaries


@router.get('/alerts')
async def list_alerts(
    status: str | None = Query(default=None),
    type: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None, alias='from'),
    to_ts: datetime | None = Query(default=None, alias='to'),
    page: int = 1,
    limit: int = 20,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert)
    if status:
        query = query.where(Alert.status == status)
    if type:
        query = query.where(Alert.alert_type == type)
    if from_ts:
        query = query.where(Alert.triggered_at >= from_ts)
    if to_ts:
        query = query.where(Alert.triggered_at <= to_ts)
    query = query.offset((page - 1) * limit).limit(limit)

    rows = (await db.execute(query)).scalars().all()
    return rows


@router.get('/conversations')
async def list_conversations(
    from_ts: datetime | None = Query(default=None, alias='from'),
    to_ts: datetime | None = Query(default=None, alias='to'),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ConversationSession)
    if from_ts:
        query = query.where(ConversationSession.started_at >= from_ts)
    if to_ts:
        query = query.where(ConversationSession.started_at <= to_ts)
    return (await db.execute(query)).scalars().all()
