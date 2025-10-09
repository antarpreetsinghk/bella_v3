"""add appointment management fields for edit and cancel features

Revision ID: 20251007_212300
Revises: df479f4dc33f
Create Date: 2025-10-07 21:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251007_212300'
down_revision: Union[str, None] = 'df479f4dc33f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add appointment management fields"""

    # Add new columns for appointment lifecycle
    op.add_column('appointments',
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))

    op.add_column('appointments',
        sa.Column('modified_at', sa.DateTime(timezone=True), nullable=True))

    op.add_column('appointments',
        sa.Column('modification_count', sa.Integer, nullable=False, server_default='0'))

    op.add_column('appointments',
        sa.Column('google_event_id', sa.String(255), nullable=True))

    # Add index for Google Calendar event lookup
    op.create_index('ix_appointments_google_event_id', 'appointments', ['google_event_id'])

    # Update status column to support more states (this assumes current status is String)
    # Note: In production, you might need to handle existing data
    # For now, we'll keep the existing status column as-is and add validation in the model


def downgrade() -> None:
    """Remove appointment management fields"""

    # Drop index first
    op.drop_index('ix_appointments_google_event_id', table_name='appointments')

    # Drop columns
    op.drop_column('appointments', 'google_event_id')
    op.drop_column('appointments', 'modification_count')
    op.drop_column('appointments', 'modified_at')
    op.drop_column('appointments', 'cancelled_at')