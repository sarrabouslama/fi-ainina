"""shared alert service tables

Revision ID: 0003_alert_sharing
Revises: 0002_reviews
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa


revision = '0003_alert_sharing'
down_revision = '0002_reviews'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'person_watchers',
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('person_id', sa.String(length=36), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'alert_log',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('event_id', sa.String(length=36), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='sent'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('alert_log')
    op.drop_table('person_watchers')