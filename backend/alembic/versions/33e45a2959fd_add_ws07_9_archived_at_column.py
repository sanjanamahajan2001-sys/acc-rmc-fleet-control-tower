"""add_ws07_9_archived_at_column

Revision ID: 33e45a2959fd
Revises: e07a9b072001
Create Date: 2026-08-14 07:05:47.980092

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33e45a2959fd'
down_revision: Union[str, None] = 'e07a9b072001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'operational_alerts',
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('operational_alerts', 'archived_at')
