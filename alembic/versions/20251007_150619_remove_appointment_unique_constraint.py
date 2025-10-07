"""remove appointment unique constraint to allow application level validation

Revision ID: remove_appt_constraint_001
Revises: df479f4dc33f
Create Date: $(date '+%Y-%m-%d %H:%M:%S.%6N')

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_appt_constraint_001'
down_revision: Union[str, None] = 'df479f4dc33f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove the unique constraint on appointments table to allow application-level validation"""
    # Drop the unique constraint
    op.drop_constraint('uq_appointments_user_id_starts_at', 'appointments', type_='unique')


def downgrade() -> None:
    """Re-add the unique constraint"""
    op.create_unique_constraint('uq_appointments_user_id_starts_at', 'appointments', ['user_id', 'starts_at'])