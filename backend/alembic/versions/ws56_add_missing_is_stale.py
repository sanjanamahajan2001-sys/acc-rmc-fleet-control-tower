"""add missing is_stale and superseded_by_snapshot_id columns to ml_prediction_snapshots

Revision ID: ws56_add_missing_is_stale
Revises: ws55_dataset_v1
Create Date: 2026-08-18 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ws56_add_missing_is_stale'
down_revision = 'ws55_dataset_v1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE ml_prediction_snapshots ADD COLUMN IF NOT EXISTS is_stale BOOLEAN NOT NULL DEFAULT FALSE;"))
    conn.execute(sa.text("ALTER TABLE ml_prediction_snapshots ADD COLUMN IF NOT EXISTS superseded_by_snapshot_id VARCHAR(100);"))
    conn.execute(sa.text("ALTER TABLE ml_prediction_snapshots ALTER COLUMN superseded_by_snapshot_id TYPE VARCHAR(100) USING superseded_by_snapshot_id::text;"))


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE ml_prediction_snapshots 
        DROP COLUMN IF EXISTS is_stale,
        DROP COLUMN IF EXISTS superseded_by_snapshot_id;
    """))
