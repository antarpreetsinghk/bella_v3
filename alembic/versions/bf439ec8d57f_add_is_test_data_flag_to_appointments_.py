"""add is_test_data flag to appointments for safe production testing

Revision ID: bf439ec8d57f
Revises: 20251007_212300
Create Date: 2025-10-09 17:40:23.139936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf439ec8d57f'
down_revision: Union[str, Sequence[str], None] = '20251007_212300'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_test_data column to appointments table
    op.add_column(
        'appointments',
        sa.Column(
            'is_test_data',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='Flag to identify test appointments for safe cleanup'
        )
    )

    # Create index for fast test data queries
    op.create_index(
        'ix_appointments_is_test_data',
        'appointments',
        ['is_test_data'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index('ix_appointments_is_test_data', table_name='appointments')

    # Drop column
    op.drop_column('appointments', 'is_test_data')
