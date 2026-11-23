"""add ml_batch_processing_cursors table

Revision ID: ws63_add_ml_batch_processing_cursors
Revises: ws56_add_missing_is_stale
Create Date: 2026-08-19 12:58:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ws63_batch_processing_cursors'
down_revision = 'ws56_add_missing_is_stale'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS ml_batch_processing_cursors (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            batch_job_name VARCHAR(100) NOT NULL UNIQUE,
            last_processed_timestamp TIMESTAMP WITH TIME ZONE,
            last_processed_dispatch_id VARCHAR(100),
            total_dispatches_processed BIGINT NOT NULL DEFAULT 0,
            total_snapshots_generated BIGINT NOT NULL DEFAULT 0,
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            deleted_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_by UUID,
            updated_by UUID
        );
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_ml_batch_processing_cursors_batch_job_name ON ml_batch_processing_cursors (batch_job_name);
    """))


def downgrade():
    op.drop_table('ml_batch_processing_cursors')
