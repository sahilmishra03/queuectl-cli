"""add bonus fields

Revision ID: a1b2c3d4e5f6
Revises: 6764f8c8a8b8
Create Date: 2026-07-17 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6764f8c8a8b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns
    op.add_column('jobs', sa.Column('priority', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('jobs', sa.Column('timeout', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('run_at', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('stdout', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('stderr', sa.Text(), nullable=True))
    op.add_column('jobs', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('completed_at', sa.DateTime(), nullable=True))
    op.add_column('jobs', sa.Column('duration_ms', sa.Integer(), nullable=True))

    # Add timed_out to jobstate enum
    op.execute("ALTER TYPE jobstate ADD VALUE IF NOT EXISTS 'timed_out'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jobs', 'duration_ms')
    op.drop_column('jobs', 'completed_at')
    op.drop_column('jobs', 'started_at')
    op.drop_column('jobs', 'stderr')
    op.drop_column('jobs', 'stdout')
    op.drop_column('jobs', 'run_at')
    op.drop_column('jobs', 'timeout')
    op.drop_column('jobs', 'priority')
