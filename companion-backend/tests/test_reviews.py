from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.models import Review, ReviewMessage, User
from app.security import hash_password
from app.enums import UserRole


@pytest.mark.asyncio
async def test_caregiver_review_admin_reply_and_push_notification(client, admin_token, db_sessionmaker, monkeypatch):
    push = AsyncMock()
    monkeypatch.setattr('app.reviews.router.manager.broadcast', push)

    async with db_sessionmaker() as db:
        db.add(
            User(
                email='caregiver@example.com',
                hashed_password=hash_password('carepass'),
                full_name='Care Giver',
                role=UserRole.caregiver,
                consent_given=True,
                preferences={'assigned_user_ids': ['elder-1']},
            )
        )
        await db.commit()

    caregiver_login = await client.post('/auth/login', json={'email': 'caregiver@example.com', 'password': 'carepass'})
    caregiver_token = caregiver_login.json()['access_token']

    created = await client.post(
        '/reviews',
        headers={'Authorization': f'Bearer {caregiver_token}'},
        json={
            'review_type': 'false_positive',
            'subject': 'Fall alert was false positive',
            'content': 'The fall alert was triggered by a chair moving.',
            'alert_id': None,
        },
    )
    assert created.status_code == 200
    review_id = created.json()['id']

    reply = await client.post(
        f'/reviews/{review_id}/reply',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'content': ''},
    )
    assert reply.status_code == 200
    assert reply.json()['messages'][-1]['content'] == 'We will get back to you.'

    async with db_sessionmaker() as db:
        review = (await db.execute(select(Review).where(Review.id == review_id))).scalar_one()
        messages = (await db.execute(select(ReviewMessage).where(ReviewMessage.review_id == review_id))).scalars().all()
        assert review.status == 'replied'
        assert len(messages) == 2

    assert push.await_count >= 2