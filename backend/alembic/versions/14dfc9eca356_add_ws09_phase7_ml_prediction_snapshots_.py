"""add_ws09_phase7_ml_prediction_snapshots_table

Revision ID: 14dfc9eca356
Revises: 2d633e2d27aa
Create Date: 2026-08-17 06:22:04.024738

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '14dfc9eca356'
down_revision: Union[str, None] = '2d633e2d27aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ml_prediction_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True, nullable=False),
        sa.Column('prediction_snapshot_id', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('idempotency_key', sa.String(length=150), nullable=False, unique=True, index=True),
        sa.Column('prediction_timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('prediction_status', sa.String(length=50), nullable=False, server_default='NOT_CONFIGURED', index=True),
        
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_model_versions.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('model_name', sa.String(length=100), nullable=False, index=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('artifact_sha256', sa.String(length=64), nullable=False),
        sa.Column('feature_set_version', sa.String(length=50), nullable=False, server_default='FeatureSetV1'),
        
        sa.Column('dispatch_id', sa.String(length=100), nullable=False, index=True),
        sa.Column('dispatch_code', sa.String(length=100), nullable=False, index=True),
        sa.Column('plant_code', sa.String(length=50), nullable=False, index=True),
        sa.Column('customer_code', sa.String(length=50), nullable=False, index=True),
        sa.Column('vehicle_code', sa.String(length=50), nullable=False),
        
        sa.Column('input_features', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('prediction_outputs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('predicted_value', sa.Float(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('is_stale', sa.Boolean(), server_default=sa.text('false'), nullable=False, index=True),
        sa.Column('superseded_by_snapshot_id', sa.String(length=100), nullable=True),
        
        sa.Column('lineage_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('ml_prediction_snapshots')
