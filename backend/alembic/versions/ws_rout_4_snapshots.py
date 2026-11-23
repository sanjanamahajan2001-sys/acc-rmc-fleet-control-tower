"""
Alembic Database Migration: Add RouteAnalysisSnapshot table with PostgreSQL Immutability Trigger.
Creates `route_analysis_snapshots` table and enforces database-level immutability.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ws_rout_4_snapshots"
down_revision = "add_customer_display_overrides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create table
    op.create_table(
        "route_analysis_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "current_source_plant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recommended_plant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recommendation_status", sa.String(length=50), nullable=False),
        sa.Column("failure_reason_code", sa.String(length=100), nullable=True),
        sa.Column("analysis_mode", sa.String(length=30), nullable=False, server_default="NOW"),
        sa.Column("planned_departure_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engine_version", sa.String(length=50), nullable=False, server_default="v1.2.1"),
        sa.Column("policy_version", sa.String(length=50), nullable=False, server_default="ROUTE_POLICY_v1.2.1"),
        sa.Column("decision_reason_summary", sa.Text(), nullable=False),
        sa.Column("analysis_context", sa.String(length=100), nullable=True),
        sa.Column("operator_notes", sa.Text(), nullable=True),
        sa.Column("erp_import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("historical_evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("google_evidence_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("candidate_comparison_matrix", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("google_queried_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_freshness_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_cached_result", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("queried_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        
        # BaseEntity & VersionedEntity standard columns
        sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_generated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("generation_reason", sa.String(length=255), nullable=True),
        sa.Column("source_lineage", sa.JSON(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 2. Indexes
    op.create_index("ix_route_analysis_snapshots_customer_id", "route_analysis_snapshots", ["customer_id"])
    op.create_index("ix_route_analysis_snapshots_site_id", "route_analysis_snapshots", ["site_id"])
    op.create_index("ix_route_analysis_snapshots_recommendation_status", "route_analysis_snapshots", ["recommendation_status"])
    op.create_index("ix_route_analysis_snapshots_erp_import_batch_id", "route_analysis_snapshots", ["erp_import_batch_id"])
    op.create_index("idx_route_snapshots_site_date", "route_analysis_snapshots", ["site_id", "queried_at"])
    op.create_index("idx_route_snapshots_status", "route_analysis_snapshots", ["recommendation_status"])

    # 3. PostgreSQL Database-Level Immutability Enforcement Trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_route_snapshot_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'DATABASE IMMUTABILITY VIOLATION: route_analysis_snapshots records are append-only and cannot be updated or deleted.';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_prevent_route_snapshot_mutation
        BEFORE UPDATE OR DELETE ON route_analysis_snapshots
        FOR EACH ROW EXECUTE FUNCTION prevent_route_snapshot_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_route_snapshot_mutation ON route_analysis_snapshots;")
    op.execute("DROP FUNCTION IF EXISTS prevent_route_snapshot_mutation();")
    op.drop_table("route_analysis_snapshots")
