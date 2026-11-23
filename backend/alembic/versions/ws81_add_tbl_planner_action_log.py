"""
Alembic Database Migration: Phase 8 Workstream 1 Planner Action Log Table Creation.
Creates `tbl_planner_action_log` table supporting Phase 8 action lifecycle execution,
prediction snapshot lineage, idempotency keys, and optimistic concurrency locks.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ws81_add_planner_action"
down_revision = "ws63_batch_processing_cursors"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tbl_planner_action_log",
        sa.Column("action_id", sa.String(length=100), nullable=False, primary_key=True),
        sa.Column("recommendation_id", sa.String(length=100), nullable=False),
        sa.Column("prediction_snapshot_id", sa.String(length=100), nullable=True),
        sa.Column("model_family", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("dataset_id", sa.String(length=100), nullable=True),
        sa.Column("operation_date", sa.String(length=20), nullable=True),
        sa.Column("plant_code", sa.String(length=100), nullable=False),
        sa.Column("customer_code", sa.String(length=100), nullable=True),
        sa.Column("dispatch_id", sa.String(length=100), nullable=True),
        sa.Column("dispatch_code", sa.String(length=100), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("action_parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("predicted_risk_exposure_inr", sa.Float(), nullable=True),
        sa.Column("estimated_avoided_exposure_inr", sa.Float(), nullable=True),
        sa.Column("actual_avoided_loss_inr", sa.Float(), nullable=True),
        sa.Column("action_status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("dispatcher_id", sa.String(length=100), nullable=False, server_default="SYSTEM"),
        sa.Column("dispatcher_role", sa.String(length=50), nullable=False, server_default="DISPATCHER"),
        sa.Column("decision_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deferred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason_code", sa.String(length=100), nullable=True),
        sa.Column("dispatcher_notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("version_lock", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_tbl_planner_action_log_action_id", "tbl_planner_action_log", ["action_id"])
    op.create_index("ix_tbl_planner_action_log_recommendation_id", "tbl_planner_action_log", ["recommendation_id"])
    op.create_index("ix_tbl_planner_action_log_prediction_snapshot_id", "tbl_planner_action_log", ["prediction_snapshot_id"])
    op.create_index("ix_tbl_planner_action_log_plant_code", "tbl_planner_action_log", ["plant_code"])
    op.create_index("ix_tbl_planner_action_log_customer_code", "tbl_planner_action_log", ["customer_code"])
    op.create_index("ix_tbl_planner_action_log_action_status", "tbl_planner_action_log", ["action_status"])
    op.create_index("ix_tbl_planner_action_log_idempotency_key", "tbl_planner_action_log", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_table("tbl_planner_action_log")
