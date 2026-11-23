"""
Alembic Database Migration: Add CustomerDisplayOverride table.
Creates `customer_display_overrides` table for administrator display name overrides.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "add_customer_display_overrides"
down_revision = "phase1_user_security_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_display_overrides",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("override_name", sa.String(length=255), nullable=False),
        sa.Column("override_reason", sa.String(length=500), nullable=True),
        sa.Column("updated_by_name", sa.String(length=100), nullable=False, server_default="ADMIN"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("version_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_generated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("generation_reason", sa.String(length=255), nullable=True),
        sa.Column("source_lineage", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("customer_id", name="uq_customer_display_overrides_customer_id"),
    )


def downgrade() -> None:
    op.drop_table("customer_display_overrides")

