"""
Alembic Database Migration: Granular Section-Based Permission Matrix.
Revision ID: add_section_permissions_matrix
Revises: add_google_api_usage_logs
Creates and seeds the 28 atomic permissions, standard roles (Administrator, Operator),
role_permissions associations, and backfills section_permissions in user_preferences.
"""

from alembic import op

revision = "add_section_permissions_matrix"
down_revision = "add_google_api_usage_logs"
branch_labels = None
depends_on = None

PLATFORM_SECTIONS = [
    ("platform_home", "Platform Home"),
    ("site_dashboard", "Site Dashboard"),
    ("overall_dashboard", "Overall Dashboard"),
    ("dispatch_analysis", "Dispatch Analysis"),
    ("dispatch_optimization", "Dispatch Optimization"),
    ("operational_intelligence", "Operational Intelligence"),
    ("predictive_intelligence", "Predictive Intelligence"),
    ("control_tower_actions", "Control Tower Actions"),
    ("alerts", "Alert Center"),
    ("reports", "Reports & Exports"),
    ("erp_import", "ERP Import"),
    ("erp_explorer", "ERP Data Explorer"),
    ("settings", "Settings Center"),
    ("user_management", "User Management"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Seed 28 atomic permissions
    for sec_key, sec_label in PLATFORM_SECTIONS:
        view_code = f"section:{sec_key}:view"
        edit_code = f"section:{sec_key}:edit"
        view_desc = f"View access to {sec_label}"
        edit_desc = f"Edit and execute access in {sec_label}"

        conn.exec_driver_sql(f"""
            INSERT INTO permissions (id, code, description)
            VALUES (gen_random_uuid(), '{view_code}', '{view_desc}')
            ON CONFLICT (code) DO NOTHING;
        """)
        conn.exec_driver_sql(f"""
            INSERT INTO permissions (id, code, description)
            VALUES (gen_random_uuid(), '{edit_code}', '{edit_desc}')
            ON CONFLICT (code) DO NOTHING;
        """)

    # 2. Seed Administrator and Operator roles
    conn.exec_driver_sql("""
        INSERT INTO roles (id, name, description)
        VALUES (
            gen_random_uuid(),
            'Administrator',
            'System Administrator with full access across all platform sections'
        )
        ON CONFLICT (name) DO NOTHING;
    """)
    conn.exec_driver_sql("""
        INSERT INTO roles (id, name, description)
        VALUES (
            gen_random_uuid(),
            'Operator',
            'Operational user with view permissions on telemetry and control tower sections'
        )
        ON CONFLICT (name) DO NOTHING;
    """)

    # 3. Associate all 28 permissions to Administrator role
    conn.exec_driver_sql("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Administrator'
          AND p.code LIKE 'section:%'
        ON CONFLICT DO NOTHING;
    """)

    # 4. Associate operational view permissions to Operator role
    conn.exec_driver_sql("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Operator'
          AND p.code LIKE 'section:%:view'
          AND p.code NOT IN ('section:settings:view', 'section:user_management:view')
        ON CONFLICT DO NOTHING;
    """)

    # 5. Ensure all existing users have a user_preferences row
    conn.exec_driver_sql("""
        INSERT INTO user_preferences (user_id, theme, default_dashboard, timezone, rows_per_page, collapsed_sidebar, ui_settings, updated_at)
        SELECT u.id, 'dark', 'operational_overview', 'UTC', 20, false, '{}'::jsonb, now()
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM user_preferences up WHERE up.user_id = u.id
        );
    """)

    # 6. Backfill section_permissions in user_preferences:
    admin_json = '{"platform_home":"edit","site_dashboard":"edit","overall_dashboard":"edit","dispatch_analysis":"edit","dispatch_optimization":"edit","operational_intelligence":"edit","predictive_intelligence":"edit","control_tower_actions":"edit","alerts":"edit","reports":"edit","erp_import":"edit","erp_explorer":"edit","settings":"edit","user_management":"edit"}'
    operator_json = '{"platform_home":"view","site_dashboard":"view","overall_dashboard":"view","dispatch_analysis":"view","dispatch_optimization":"view","operational_intelligence":"view","predictive_intelligence":"view","control_tower_actions":"view","alerts":"view","reports":"view","erp_import":"none","erp_explorer":"view","settings":"none","user_management":"none"}'

    conn.exec_driver_sql(f"""
        UPDATE user_preferences up
        SET ui_settings = jsonb_set(
            COALESCE(up.ui_settings, '{{}}'::jsonb),
            '{{section_permissions}}',
            '{admin_json}'::jsonb,
            true
        )
        FROM users u
        WHERE up.user_id = u.id
          AND u.is_superuser = true;
    """)

    conn.exec_driver_sql(f"""
        UPDATE user_preferences up
        SET ui_settings = jsonb_set(
            COALESCE(up.ui_settings, '{{}}'::jsonb),
            '{{section_permissions}}',
            '{operator_json}'::jsonb,
            true
        )
        FROM users u
        WHERE up.user_id = u.id
          AND u.is_superuser = false
          AND (up.ui_settings->'section_permissions' IS NULL);
    """)

    # 7. Map Administrator role to superusers in user_roles
    conn.exec_driver_sql("""
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE u.is_superuser = true
          AND r.name = 'Administrator'
        ON CONFLICT DO NOTHING;
    """)

    # 8. Map Operator role to regular users having no role
    conn.exec_driver_sql("""
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        CROSS JOIN roles r
        WHERE u.is_superuser = false
          AND r.name = 'Operator'
          AND NOT EXISTS (
              SELECT 1 FROM user_roles ur WHERE ur.user_id = u.id
          )
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE code LIKE 'section:%'
        );
    """)
    conn.exec_driver_sql("""
        DELETE FROM permissions
        WHERE code LIKE 'section:%';
    """)
