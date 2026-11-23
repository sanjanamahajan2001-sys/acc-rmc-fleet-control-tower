"""add ws54 model health metrics and sources tables

Revision ID: ws54_health_v2
Revises: 9f3ed2578195
Create Date: 2026-08-18 17:16:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ws54_health_v2'
down_revision = '9f3ed2578195'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create model_health_metrics table
    op.create_table(
        'model_health_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('health_record_id', sa.String(length=100), nullable=False, unique=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False, unique=True),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_family', sa.String(length=100), nullable=False, server_default='delay_regressor'),
        sa.Column('model_version_id', sa.String(length=100), nullable=False, server_default='v1.1.0-candidate-ds-fsv1-prom'),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('feature_set_version', sa.String(length=50), nullable=False, server_default='FeatureSetV1'),
        sa.Column('scope_type', sa.String(length=50), nullable=False, server_default='GLOBAL'),
        sa.Column('scope_id', sa.String(length=100), nullable=True),
        sa.Column('time_window_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('window_type', sa.String(length=20), nullable=False, server_default='30d'),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluation_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_prediction_error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('regression_sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('classification_sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('financial_sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_percentage_error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('zero_actual_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('mae', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('rmse', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('mape', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('mean_signed_error', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('median_absolute_error', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('max_absolute_error', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('accuracy', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('precision_score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('recall_score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('f1_score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('roc_auc', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('brier_score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('psi_score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('mean_financial_error_inr', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('mae_financial_error_inr', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_predicted_exposure_inr', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('total_realized_impact_inr', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('health_status', sa.String(length=50), nullable=False, server_default='INSUFFICIENT_DATA'),
        sa.Column('retraining_recommended', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('baseline_mae', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('baseline_f1', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('baseline_brier', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('baseline_provenance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('financial_health_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('health_calculation_version', sa.String(length=50), nullable=False, server_default='v1.0.0-phase54-health-engine'),
        sa.Column('formula_version', sa.String(length=50), nullable=False, server_default='WS54_HEALTH_STANDARD_V1'),
        sa.Column('source_error_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_superseded', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('superseded_by_health_id', sa.String(length=100), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index('idx_health_model_version_window', 'model_health_metrics', ['model_version_id', 'scope_type', 'window_type'])
    op.create_index('idx_health_model_name', 'model_health_metrics', ['model_name'])

    # 2. Create model_health_metric_sources table
    op.create_table(
        'model_health_metric_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('health_record_id', sa.String(length=100), sa.ForeignKey('model_health_metrics.health_record_id', ondelete='CASCADE'), nullable=False),
        sa.Column('prediction_error_record_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('health_record_id', 'prediction_error_record_id', name='uq_health_sources_health_error'),
    )
    op.create_index('idx_health_sources_error_ref', 'model_health_metric_sources', ['prediction_error_record_id'])


def downgrade():
    op.drop_table('model_health_metric_sources')
    op.drop_index('idx_health_model_name', table_name='model_health_metrics')
    op.drop_index('idx_health_model_version_window', table_name='model_health_metrics')
    op.drop_table('model_health_metrics')
