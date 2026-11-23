"""
Alembic migration: add_ws10_1_ml_lifecycle_triggers_table
Revision ID: 913ac8a4c82b
Revises: 14dfc9eca356
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '913ac8a4c82b'
down_revision: Union[str, None] = '14dfc9eca356'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ml_lifecycle_triggers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trigger_id', sa.String(length=100), nullable=False),
        sa.Column('import_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('job_number', sa.String(length=100), nullable=False),
        sa.Column('dataset_id', sa.String(length=100), nullable=False),
        sa.Column('model_family', sa.String(length=100), nullable=False, server_default='ALL_FAMILIES'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('new_dispatch_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cooldown_hours', sa.Float(), nullable=False, server_default='6.0'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('error_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ml_lifecycle_triggers_trigger_id', 'ml_lifecycle_triggers', ['trigger_id'], unique=True)
    op.create_index('ix_ml_lifecycle_triggers_import_job_id', 'ml_lifecycle_triggers', ['import_job_id'], unique=False)
    op.create_index('ix_ml_lifecycle_triggers_job_number', 'ml_lifecycle_triggers', ['job_number'], unique=False)
    op.create_index('ix_ml_lifecycle_triggers_dataset_id', 'ml_lifecycle_triggers', ['dataset_id'], unique=False)
    op.create_index('ix_ml_lifecycle_triggers_model_family', 'ml_lifecycle_triggers', ['model_family'], unique=False)
    op.create_index('ix_ml_lifecycle_triggers_status', 'ml_lifecycle_triggers', ['status'], unique=False)
    op.create_index('ix_ml_lifecycle_triggers_created_at', 'ml_lifecycle_triggers', ['created_at'], unique=False)
    op.create_index('ix_ml_lifecycle_triggers_status_family', 'ml_lifecycle_triggers', ['status', 'model_family'], unique=False)
    op.create_foreign_key('fk_ml_lifecycle_triggers_import_job_id', 'ml_lifecycle_triggers', 'import_jobs', ['import_job_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_ml_lifecycle_triggers_import_job_id', 'ml_lifecycle_triggers', type_='foreignkey')
    op.drop_index('ix_ml_lifecycle_triggers_status_family', table_name='ml_lifecycle_triggers')
    op.drop_index('ix_ml_lifecycle_triggers_created_at', table_name='ml_lifecycle_triggers')
    op.drop_index('ix_ml_lifecycle_triggers_status', table_name='ml_lifecycle_triggers')
    op.drop_index('ix_ml_lifecycle_triggers_model_family', table_name='ml_lifecycle_triggers')
    op.drop_index('ix_ml_lifecycle_triggers_dataset_id', table_name='ml_lifecycle_triggers')
    op.drop_index('ix_ml_lifecycle_triggers_job_number', table_name='ml_lifecycle_triggers')
    op.drop_index('ix_ml_lifecycle_triggers_import_job_id', table_name='ml_lifecycle_triggers')
    op.drop_index('ix_ml_lifecycle_triggers_trigger_id', table_name='ml_lifecycle_triggers')
    op.drop_table('ml_lifecycle_triggers')
