"""add ws55 historical training dataset and rows tables

Revision ID: ws55_dataset_v1
Revises: ws54_health_v2
Create Date: 2026-08-18 17:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ws55_dataset_v1'
down_revision = 'ws54_health_v2'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create historical_training_datasets table
    op.create_table(
        'historical_training_datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('dataset_id', sa.String(length=100), nullable=False, unique=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False, unique=True),
        sa.Column('dataset_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
        sa.Column('model_family', sa.String(length=100), nullable=False),
        sa.Column('feature_set_version', sa.String(length=50), nullable=False, server_default='FeatureSetV1'),
        sa.Column('scope_type', sa.String(length=50), nullable=False, server_default='GLOBAL'),
        sa.Column('scope_id', sa.String(length=100), nullable=True),
        sa.Column('source_time_range_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_time_range_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('generation_timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('evaluation_cutoff', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_outcome_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('source_snapshot_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('validation_policy_version', sa.String(length=50), nullable=False, server_default='WS55_QUALITY_GATE_V1'),
        sa.Column('leakage_policy_version', sa.String(length=50), nullable=False, server_default='FEATURE_SET_V1_STRICT_NO_LEAKAGE'),
        sa.Column('code_version', sa.String(length=50), nullable=False, server_default='v1.0.0-phase55-dataset-builder'),
        sa.Column('dataset_content_hash', sa.String(length=64), nullable=False),
        sa.Column('dataset_status', sa.String(length=50), nullable=False, server_default='GENERATED'),
        sa.Column('quality_gate_passed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('rejection_reason', sa.String(length=500), nullable=True),
        sa.Column('quality_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_record_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_superseded', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('superseded_by_dataset_id', sa.String(length=100), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('model_family', 'feature_set_version', 'scope_type', 'scope_id', 'dataset_version', 'source_time_range_start', 'source_time_range_end', 'dataset_content_hash', name='uq_training_dataset_identity'),
    )
    op.create_index('idx_dataset_family_status', 'historical_training_datasets', ['model_family', 'dataset_status'])

    # 2. Create historical_training_dataset_rows table
    op.create_table(
        'historical_training_dataset_rows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('dataset_id', sa.String(length=100), sa.ForeignKey('historical_training_datasets.dataset_id', ondelete='CASCADE'), nullable=False),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('outcome_id', sa.String(length=100), nullable=False),
        sa.Column('prediction_error_record_id', sa.String(length=100), nullable=True),
        sa.Column('prediction_snapshot_id', sa.String(length=100), nullable=True),
        sa.Column('model_version_id', sa.String(length=100), nullable=False),
        sa.Column('dispatch_id', sa.String(length=100), nullable=True),
        sa.Column('features_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('label_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('label_numeric', sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column('label_class', sa.Integer(), nullable=True),
        sa.Column('realized_financial_impact_inr', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('dataset_id', 'row_index', name='uq_dataset_row_index'),
    )
    op.create_index('idx_dataset_row_outcome', 'historical_training_dataset_rows', ['dataset_id', 'outcome_id'])


def downgrade():
    op.drop_table('historical_training_dataset_rows')
    op.drop_index('idx_dataset_family_status', table_name='historical_training_datasets')
    op.drop_table('historical_training_datasets')
