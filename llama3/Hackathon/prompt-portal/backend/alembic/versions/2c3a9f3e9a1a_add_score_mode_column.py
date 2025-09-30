"""Add mode column to scores

Revision ID: 2c3a9f3e9a1a
Revises: d158079d372d
Create Date: 2025-09-30 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c3a9f3e9a1a'
down_revision: Union[str, None] = 'd158079d372d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'mode' column to scores with default 'manual' for existing rows
    op.add_column('scores', sa.Column('mode', sa.String(length=10), nullable=False, server_default='manual'))
    # Optional index to speed up filtering by mode
    op.create_index('ix_scores_mode', 'scores', ['mode'], unique=False)


def downgrade() -> None:
    # Drop index and column
    op.drop_index('ix_scores_mode', table_name='scores')
    op.drop_column('scores', 'mode')
