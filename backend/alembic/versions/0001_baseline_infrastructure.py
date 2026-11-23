"""0001_baseline_infrastructure

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-08-05 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto for native gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    # Enable PostGIS for spatial geometries
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis";')


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "postgis";')
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto";')
