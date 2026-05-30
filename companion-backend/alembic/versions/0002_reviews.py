"""review threads and messages

Revision ID: 0002_reviews
Revises: 0001_initial
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa


revision = '0002_reviews'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_by_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('assigned_admin_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id'), nullable=True),
        sa.Column('review_type', sa.String(length=40), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'review_messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('review_id', sa.Integer(), sa.ForeignKey('reviews.id'), nullable=False),
        sa.Column('sender_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('sender_role', sa.String(length=20), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('review_messages')
    op.drop_table('reviews')