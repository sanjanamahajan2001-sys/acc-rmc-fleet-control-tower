"""add_ws10_2_ml_datasets_table

Revision ID: a5f240fa5f01
Revises: 913ac8a4c82b
Create Date: 2026-08-17 18:09:56.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a5f240fa5f01'
down_revision: Union[str, None] = '913ac8a4c82b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ml_datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_id', sa.String(length=100), nullable=False),
        sa.Column('feature_set_version', sa.String(length=50), nullable=False, server_default='FeatureSetV1'),
        sa.Column('trigger_id', sa.String(length=100), nullable=True),
        sa.Column('import_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_erp_job_number', sa.String(length=100), nullable=True),
        sa.Column('total_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('train_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('val_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('holdout_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('excluded_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sha256_checksum', sa.String(length=64), nullable=False),
        sa.Column('operation_date_min', sa.DateTime(timezone=True), nullable=True),
        sa.Column('operation_date_max', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lineage_metadata', sa.JSON(), nullable=False),
        sa.Column('exclusion_stats', sa.JSON(), nullable=False),
        sa.Column('target_availability', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['import_job_id'], ['import_jobs.id'], name='fk_ml_datasets_import_job_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_ml_datasets')
    )
    op.create_index('ix_ml_datasets_dataset_id', 'ml_datasets', ['dataset_id'], unique=True)
    op.create_index('ix_ml_datasets_feature_set_version', 'ml_datasets', ['feature_set_version'], unique=False)
    op.create_index('ix_ml_datasets_trigger_id', 'ml_datasets', ['trigger_id'], unique=False)
    op.create_index('ix_ml_datasets_created_at', 'ml_datasets', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ml_datasets_created_at', table_name='ml_datasets')
    op.drop_index('ix_ml_datasets_trigger_id', table_name='ml_datasets')
    op.drop_index('ix_ml_datasets_feature_set_version', table_name='ml_datasets')
    op.drop_index('ix_ml_datasets_dataset_id', table_name='ml_datasets')
    op.drop_table('ml_datasets')
