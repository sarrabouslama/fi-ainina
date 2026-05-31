from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.events.manager import manager
from app.enums import UserRole
from app.models import Review, ReviewMessage, User
from app.reviews.schemas import ReviewCreate, ReviewReply, ReviewMessageResponse, ReviewResponse


router = APIRouter(prefix='/reviews', tags=['reviews'])

AUTO_REPLY = 'We will get back to you.'


def _serialize_message(message: ReviewMessage) -> ReviewMessageResponse:
    return ReviewMessageResponse(
        id=message.id,
        review_id=message.review_id,
        sender_user_id=message.sender_user_id,
        sender_role=message.sender_role,
        message_type=message.message_type,
        content=message.content,
        timestamp=message.timestamp,
    )


async def _load_messages(db: AsyncSession, review_id: int) -> list[ReviewMessageResponse]:
    rows = (await db.execute(select(ReviewMessage).where(ReviewMessage.review_id == review_id).order_by(ReviewMessage.timestamp.asc()))).scalars().all()
    return [_serialize_message(message) for message in rows]


async def _broadcast_review_event(event_type: str, review: Review, message: ReviewMessage):
    await manager.broadcast(
        {
            'type': event_type,
            'payload': {
                'review_id': review.id,
                'alert_id': review.alert_id,
                'review_type': review.review_type,
                'subject': review.subject,
                'status': review.status,
                'sender_role': message.sender_role,
                'message_type': message.message_type,
                'content_preview': message.content[:200],
                'timestamp': message.timestamp.isoformat(),
            },
        }
    )


def _build_response(review: Review, messages: list[ReviewMessageResponse]) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        created_by_user_id=review.created_by_user_id,
        assigned_admin_id=review.assigned_admin_id,
        alert_id=review.alert_id,
        review_type=review.review_type,
        subject=review.subject,
        status=review.status,
        created_at=review.created_at,
        updated_at=review.updated_at,
        messages=messages,
    )


@router.post('', response_model=ReviewResponse)
async def create_review(payload: ReviewCreate, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current.role not in {UserRole.caregiver, UserRole.admin}:
        raise HTTPException(status_code=403, detail='Only caregivers and admins can create reviews')

    review = Review(
        created_by_user_id=current.id,
        assigned_admin_id=payload.assigned_admin_id,
        alert_id=payload.alert_id,
        review_type=payload.review_type,
        subject=payload.subject,
        status='open',
    )
    db.add(review)
    await db.flush()

    message = ReviewMessage(
        review_id=review.id,
        sender_user_id=current.id,
        sender_role=current.role,
        message_type='message',
        content=payload.content,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(message)
    await db.commit()
    await db.refresh(review)
    await db.refresh(message)

    await _broadcast_review_event('review_message_created', review, message)
    return _build_response(review, [_serialize_message(message)])


@router.post('/{review_id}/reply', response_model=ReviewResponse)
async def reply_review(
    review_id: int,
    payload: ReviewReply,
    current: User = Depends(require_role('admin')),
    db: AsyncSession = Depends(get_db),
):
    review = (await db.execute(select(Review).where(Review.id == review_id))).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail='Review not found')

    content = (payload.content or '').strip() or AUTO_REPLY
    message = ReviewMessage(
        review_id=review.id,
        sender_user_id=current.id,
        sender_role=UserRole.admin,
        message_type='reply',
        content=content,
        timestamp=datetime.now(timezone.utc),
    )
    review.status = 'replied'
    db.add(message)
    await db.commit()
    await db.refresh(review)
    await db.refresh(message)

    await _broadcast_review_event('review_message_created', review, message)
    return _build_response(review, await _load_messages(db, review.id))


@router.get('', response_model=list[ReviewResponse])
async def list_reviews(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Review)
    if current.role == UserRole.caregiver:
        query = query.where(Review.created_by_user_id == current.id)
    elif current.role != UserRole.admin:
        raise HTTPException(status_code=403, detail='Forbidden')

    reviews = (await db.execute(query.order_by(Review.created_at.desc()))).scalars().all()
    payload = []
    for review in reviews:
        payload.append(_build_response(review, await _load_messages(db, review.id)))
    return payload


@router.get('/{review_id}', response_model=ReviewResponse)
async def get_review(review_id: int, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    review = (await db.execute(select(Review).where(Review.id == review_id))).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail='Review not found')
    if current.role != UserRole.admin and review.created_by_user_id != current.id:
        raise HTTPException(status_code=403, detail='Forbidden')
    return _build_response(review, await _load_messages(db, review.id))