"""add_ws07_2_operational_alerts_table

Revision ID: e07a9b072001
Revises: 2d87eb1a46c6
Create Date: 2026-08-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e07a9b072001'
down_revision = '2d87eb1a46c6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'operational_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('alert_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('alert_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), server_default='OPEN', nullable=False),
        sa.Column('plant_id', sa.String(length=64), nullable=False),
        sa.Column('customer_id', sa.String(length=64), nullable=False),
        sa.Column('dispatch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vehicle_id', sa.String(length=32), nullable=True),
        sa.Column('dataset_id', sa.String(length=64), nullable=False),
        sa.Column('import_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metric_name', sa.String(length=64), nullable=False),
        sa.Column('actual_value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('threshold_value', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=16), nullable=False),
        sa.Column('business_impact', sa.String(length=255), nullable=False),
        sa.Column('evidence_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('recommended_action', sa.String(length=255), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=64), nullable=True),
        sa.Column('acknowledgement_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(length=64), nullable=True),
        sa.Column('resolution_reason', sa.String(length=255), nullable=True),
        sa.Column('rule_version', sa.String(length=32), server_default='v1.0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alert_fingerprint', 'dataset_id', name='uq_alerts_fingerprint_dataset')
    )
    op.create_index('idx_alerts_scope', 'operational_alerts', ['plant_id', 'customer_id', 'status'], unique=False)

def downgrade() -> None:
    op.drop_index('idx_alerts_scope', table_name='operational_alerts')
    op.drop_table('operational_alerts')
