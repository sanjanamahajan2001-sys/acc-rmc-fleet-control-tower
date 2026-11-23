"""
Alembic Database Migration: Phase 1 Workstream 11 Reporting Execution Audit Table Creation.
Creates tbl_report_execution_audit table supporting reporting metadata, effective scope,
scope fingerprints, execution statuses, and artifact storage references.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ws11_add_reporting_subsystem"
down_revision = "ws81_add_planner_action"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "tbl_report_execution_audit",
        sa.Column("execution_id", sa.String(length=100), nullable=False, primary_key=True),
        sa.Column("report_id", sa.String(length=100), nullable=False),
        sa.Column("report_type", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("requested_by", sa.String(length=100), nullable=False, server_default="SYSTEM"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("requested_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("effective_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scope_fingerprint", sa.String(length=100), nullable=False),
        sa.Column("scope_validation_status", sa.String(length=50), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dataset_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="QUEUED"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_tbl_report_execution_audit_report_id", "tbl_report_execution_audit", ["report_id"])
    op.create_index("ix_tbl_report_execution_audit_report_type", "tbl_report_execution_audit", ["report_type"])
    op.create_index("ix_tbl_report_execution_audit_scope_fingerprint", "tbl_report_execution_audit", ["scope_fingerprint"])
    op.create_index("ix_tbl_report_execution_audit_status", "tbl_report_execution_audit", ["status"])
    op.create_index("ix_tbl_report_execution_audit_requested_by", "tbl_report_execution_audit", ["requested_by"])
    op.create_index("ix_tbl_report_execution_audit_dataset_id", "tbl_report_execution_audit", ["dataset_id"])

def downgrade() -> None:
    op.drop_table("tbl_report_execution_audit")
