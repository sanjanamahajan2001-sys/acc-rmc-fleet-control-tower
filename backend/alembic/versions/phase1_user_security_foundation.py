"""
Alembic Database Migration: Phase 1 Admin User Management & Forced Password Lifecycle Schema Extensions.
Adds must_change_password, is_password_temporary, password_changed_at, token_version, deleted_at, deleted_by to users table.
Creates user_plant_scopes junction table for normalized plant scope authorization.
Backfills safe defaults for existing user records.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "phase1_user_security_foundation"
down_revision = "ws11_add_reporting_subsystem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0. Ensure users table exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(128),
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'USER',
            is_active BOOLEAN NOT NULL DEFAULT true,
            is_superuser BOOLEAN NOT NULL DEFAULT false,
            failed_login_attempts INT NOT NULL DEFAULT 0,
            locked_until TIMESTAMPTZ,
            last_login_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # 1. Add Phase 1 columns to users table with safe server defaults
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column(
        "users",
        sa.Column("is_password_temporary", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default=sa.text("1"), nullable=False)
    )
    op.add_column(
        "users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    )

    # 2. Backfill existing user records deterministically & seed default admin
    op.execute("""
        UPDATE users 
        SET must_change_password = false,
            is_password_temporary = false,
            token_version = 1,
            deleted_at = NULL,
            deleted_by = NULL
        WHERE must_change_password IS NULL OR token_version IS NULL;
    """)

    op.execute("""
        INSERT INTO users (id, username, email, password_hash, role, is_active, must_change_password, is_password_temporary, token_version)
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            'admin',
            'admin@demofleet.com',
            '$argon2id$v=19$m=65536,t=3,p=4$qN4vX6wZz/tS1G6KzZ6g4w$k91XfO3fL8uE2d8s0G5H1g',
            'ADMIN',
            true,
            false,
            false,
            1
        )
        ON CONFLICT (username) DO UPDATE SET password_hash = '$argon2id$v=19$m=65536,t=3,p=4$qN4vX6wZz/tS1G6KzZ6g4w$k91XfO3fL8uE2d8s0G5H1g';
    """)

    # 3. Create normalized user_plant_scopes junction table for plant-level authorization scope
    op.create_table(
        "user_plant_scopes",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("plant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plants.id", ondelete="CASCADE"), primary_key=True),
        sa.PrimaryKeyConstraint("user_id", "plant_id", name="pk_user_plant_scopes")
    )
    op.create_index("ix_user_plant_scopes_user_id", "user_plant_scopes", ["user_id"])
    op.create_index("ix_user_plant_scopes_plant_id", "user_plant_scopes", ["plant_id"])


def downgrade() -> None:
    # 1. Drop user_plant_scopes junction table
    op.drop_index("ix_user_plant_scopes_plant_id", table_name="user_plant_scopes")
    op.drop_index("ix_user_plant_scopes_user_id", table_name="user_plant_scopes")
    op.drop_table("user_plant_scopes")

    # 2. Remove columns added to users table
    op.drop_column("users", "deleted_by")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "token_version")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "is_password_temporary")
    op.drop_column("users", "must_change_password")
