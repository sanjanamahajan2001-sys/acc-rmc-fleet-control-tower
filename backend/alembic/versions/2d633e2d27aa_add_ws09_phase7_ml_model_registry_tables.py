"""add_ws09_phase7_ml_model_registry_tables

Revision ID: 2d633e2d27aa
Revises: 33e45a2959fd
Create Date: 2026-08-17 06:07:04.024738

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2d633e2d27aa'
down_revision: Union[str, None] = '33e45a2959fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create ml_model_versions table
    op.create_table(
        'ml_model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True, nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False, index=True),
        sa.Column('model_category', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('algorithm', sa.String(length=100), nullable=False),
        sa.Column('target_name', sa.String(length=100), nullable=False),
        sa.Column('feature_set_version', sa.String(length=50), nullable=False),
        sa.Column('training_dataset_id', sa.String(length=100), nullable=False),
        sa.Column('validation_dataset_id', sa.String(length=100), nullable=True),
        sa.Column('holdout_dataset_id', sa.String(length=100), nullable=True),
        sa.Column('artifact_path', sa.String(length=500), nullable=False),
        sa.Column('artifact_sha256', sa.String(length=64), nullable=False, index=True),
        sa.Column('artifact_size_bytes', sa.Integer(), nullable=False),
        sa.Column('training_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluation_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('promotion_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retirement_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lifecycle_status', sa.String(length=50), nullable=False, server_default='TRAINED_CANDIDATE', index=True),
        sa.Column('evaluation_decision', sa.String(length=50), nullable=False, server_default='PENDING_EVALUATION'),
        sa.Column('rejection_reasons', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('hyperparameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('random_seed', sa.Integer(), nullable=False, server_default='42'),
        sa.Column('row_counts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evaluation_provenance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint('model_name', 'model_version', name='uq_ml_model_versions_name_version'),
        sa.UniqueConstraint('model_name', 'feature_set_version', 'target_name', 'model_version', name='uq_ml_model_versions_identity'),
    )

    # Partial unique index for active promoted model per model_name
    op.create_index(
        'uq_active_promoted_model_per_name',
        'ml_model_versions',
        ['model_name'],
        unique=True,
        postgresql_where=sa.text("lifecycle_status = 'PROMOTED' AND is_deleted = false")
    )

    # 2. Create ml_model_audit_events table
    op.create_table(
        'ml_model_audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True, nullable=False),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_model_versions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('model_name', sa.String(length=100), nullable=False, index=True),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False, index=True),
        sa.Column('previous_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('artifact_sha256', sa.String(length=64), nullable=False),
        sa.Column('decision_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


    # 3. Create ml_training_runs table
    op.create_table(
        'ml_training_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True, nullable=False),
        sa.Column('training_run_id', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('dataset_id', sa.String(length=100), nullable=False),
        sa.Column('dataset_version', sa.String(length=50), nullable=False),
        sa.Column('dataset_content_hash', sa.String(length=64), nullable=False),
        sa.Column('model_family', sa.String(length=100), nullable=False, index=True),
        sa.Column('feature_set_version', sa.String(length=50), nullable=False),
        sa.Column('target_name', sa.String(length=100), nullable=False),
        sa.Column('total_dataset_rows', sa.Integer(), nullable=False),
        sa.Column('train_row_count', sa.Integer(), nullable=False),
        sa.Column('validation_row_count', sa.Integer(), nullable=False),
        sa.Column('holdout_row_count', sa.Integer(), nullable=False),
        sa.Column('split_strategy', sa.String(length=50), nullable=False),
        sa.Column('split_boundaries', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('algorithm', sa.String(length=100), nullable=False),
        sa.Column('hyperparameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('random_seed', sa.Integer(), nullable=False, server_default='42'),
        sa.Column('config_hash', sa.String(length=64), nullable=False, index=True),
        sa.Column('framework_versions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('python_version', sa.String(length=50), nullable=True),
        sa.Column('training_engine_version', sa.String(length=50), nullable=True),
        sa.Column('run_status', sa.String(length=50), nullable=False, server_default='COMPLETED', index=True),
        sa.Column('failure_reason', sa.String(length=500), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('candidate_model_version_id', sa.String(length=100), nullable=True, index=True),
        sa.Column('artifact_path', sa.String(length=500), nullable=True),
        sa.Column('artifact_sha256', sa.String(length=64), nullable=True),
        sa.Column('artifact_size_bytes', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('ml_model_audit_events')
    op.drop_index('uq_active_promoted_model_per_name', table_name='ml_model_versions')
    op.drop_table('ml_model_versions')
