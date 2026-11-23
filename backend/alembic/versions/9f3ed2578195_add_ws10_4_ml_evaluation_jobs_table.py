"""add_ws10_3_ml_evaluation_jobs_table

Revision ID: 9f3ed2578195
Revises: 8e1fc1369183
Create Date: 2026-08-17 18:13:50.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f3ed2578195'
down_revision: Union[str, None] = '8e1fc1369183'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ml_evaluation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', sa.String(length=100), nullable=False),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=False, server_default='delay_regressor'),
        sa.Column('model_version', sa.String(length=50), nullable=False, server_default='v1.0'),
        sa.Column('trigger_id', sa.String(length=100), nullable=True),
        sa.Column('dataset_id', sa.String(length=100), nullable=False),
        sa.Column('model_family', sa.String(length=100), nullable=False, server_default='ALL_FAMILIES'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('evaluation_decision', sa.String(length=50), nullable=False, server_default='PENDING_EVALUATION'),
        sa.Column('metrics_holdout', sa.JSON(), nullable=True),
        sa.Column('threshold_rules', sa.JSON(), nullable=True),
        sa.Column('models_trained_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trained_model_versions', sa.JSON(), nullable=True),
        sa.Column('execution_duration_sec', sa.Float(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('error_metadata', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id', name='pk_ml_evaluation_jobs')
    )
    op.create_index('ix_ml_evaluation_jobs_job_id', 'ml_evaluation_jobs', ['job_id'], unique=True)
    op.create_index('ix_ml_evaluation_jobs_model_name', 'ml_evaluation_jobs', ['model_name'], unique=False)
    op.create_index('ix_ml_evaluation_jobs_model_version', 'ml_evaluation_jobs', ['model_version'], unique=False)
    op.create_index('ix_ml_evaluation_jobs_trigger_id', 'ml_evaluation_jobs', ['trigger_id'], unique=False)
    op.create_index('ix_ml_evaluation_jobs_dataset_id', 'ml_evaluation_jobs', ['dataset_id'], unique=False)
    op.create_index('ix_ml_evaluation_jobs_status', 'ml_evaluation_jobs', ['status'], unique=False)
    op.create_index('ix_ml_evaluation_jobs_created_at', 'ml_evaluation_jobs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ml_evaluation_jobs_created_at', table_name='ml_evaluation_jobs')
    op.drop_index('ix_ml_evaluation_jobs_status', table_name='ml_evaluation_jobs')
    op.drop_index('ix_ml_evaluation_jobs_dataset_id', table_name='ml_evaluation_jobs')
    op.drop_index('ix_ml_evaluation_jobs_trigger_id', table_name='ml_evaluation_jobs')
    op.drop_index('ix_ml_evaluation_jobs_job_id', table_name='ml_evaluation_jobs')
    op.drop_table('ml_evaluation_jobs')
