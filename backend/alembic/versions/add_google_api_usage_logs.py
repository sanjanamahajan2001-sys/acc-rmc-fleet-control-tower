"""
Alembic Database Migration: Add GoogleApiUsageLog table.
Creates `google_api_usage_logs` table for tracking billable outgoing Google Maps & Routes API calls.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_google_api_usage_logs"
down_revision = "ws_rout_4_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_api_usage_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("api_service", sa.String(length=50), nullable=False),
        sa.Column("endpoint", sa.String(length=150), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("is_cached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        
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

    op.create_index("ix_google_api_usage_logs_api_service", "google_api_usage_logs", ["api_service"])
    op.create_index("ix_google_api_usage_logs_created_at", "google_api_usage_logs", ["created_at"])
    op.create_index("idx_google_api_usage_service_date", "google_api_usage_logs", ["api_service", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_google_api_usage_service_date", table_name="google_api_usage_logs")
    op.drop_index("ix_google_api_usage_logs_created_at", table_name="google_api_usage_logs")
    op.drop_index("ix_google_api_usage_logs_api_service", table_name="google_api_usage_logs")
    op.drop_table("google_api_usage_logs")
