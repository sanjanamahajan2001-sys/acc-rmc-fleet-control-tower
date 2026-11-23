#!/usr/bin/env bash
set -e

echo "=== Connecting to Linode Remote Production Database (192.46.210.48) ==="

ssh -i ~/.ssh/linode_prod -o StrictHostKeyChecking=no root@192.46.210.48 << 'REMOTESCRIPT'
set -e

echo -e "\n[1] Checking current remote permissions, roles, and users:"
sudo -u postgres psql -d fleet_control_tower_db -c "
SELECT count(*) as total_permissions FROM permissions;
SELECT count(*) as total_roles FROM roles;
SELECT id, username, email, is_superuser, is_active FROM users;
"

echo -e "\n[2] Executing Phase 2 Database Migration & Seeding:"
sudo -u postgres psql -d fleet_control_tower_db << 'SQL'
-- 1. Seed 28 atomic permissions
INSERT INTO permissions (id, code, description) VALUES
  (gen_random_uuid(), 'section:platform_home:view', 'View access to Platform Home'),
  (gen_random_uuid(), 'section:platform_home:edit', 'Edit and execute access in Platform Home'),
  (gen_random_uuid(), 'section:site_dashboard:view', 'View access to Site Dashboard'),
  (gen_random_uuid(), 'section:site_dashboard:edit', 'Edit and execute access in Site Dashboard'),
  (gen_random_uuid(), 'section:overall_dashboard:view', 'View access to Overall Dashboard'),
  (gen_random_uuid(), 'section:overall_dashboard:edit', 'Edit and execute access in Overall Dashboard'),
  (gen_random_uuid(), 'section:dispatch_analysis:view', 'View access to Dispatch Analysis'),
  (gen_random_uuid(), 'section:dispatch_analysis:edit', 'Edit and execute access in Dispatch Analysis'),
  (gen_random_uuid(), 'section:dispatch_optimization:view', 'View access to Dispatch Optimization'),
  (gen_random_uuid(), 'section:dispatch_optimization:edit', 'Edit and execute access in Dispatch Optimization'),
  (gen_random_uuid(), 'section:operational_intelligence:view', 'View access to Operational Intelligence'),
  (gen_random_uuid(), 'section:operational_intelligence:edit', 'Edit and execute access in Operational Intelligence'),
  (gen_random_uuid(), 'section:predictive_intelligence:view', 'View access to Predictive Intelligence'),
  (gen_random_uuid(), 'section:predictive_intelligence:edit', 'Edit and execute access in Predictive Intelligence'),
  (gen_random_uuid(), 'section:control_tower_actions:view', 'View access to Control Tower Actions'),
  (gen_random_uuid(), 'section:control_tower_actions:edit', 'Edit and execute access in Control Tower Actions'),
  (gen_random_uuid(), 'section:alerts:view', 'View access to Alert Center'),
  (gen_random_uuid(), 'section:alerts:edit', 'Edit and execute access in Alert Center'),
  (gen_random_uuid(), 'section:reports:view', 'View access to Reports & Exports'),
  (gen_random_uuid(), 'section:reports:edit', 'Edit and execute access in Reports & Exports'),
  (gen_random_uuid(), 'section:erp_import:view', 'View access to ERP Import'),
  (gen_random_uuid(), 'section:erp_import:edit', 'Edit and execute access in ERP Import'),
  (gen_random_uuid(), 'section:erp_explorer:view', 'View access to ERP Data Explorer'),
  (gen_random_uuid(), 'section:erp_explorer:edit', 'Edit and execute access in ERP Data Explorer'),
  (gen_random_uuid(), 'section:settings:view', 'View access to Settings Center'),
  (gen_random_uuid(), 'section:settings:edit', 'Edit and execute access in Settings Center'),
  (gen_random_uuid(), 'section:user_management:view', 'View access to User Management'),
  (gen_random_uuid(), 'section:user_management:edit', 'Edit and execute access in User Management')
ON CONFLICT (code) DO NOTHING;

-- 2. Seed Administrator and Operator roles
INSERT INTO roles (id, name, description) VALUES
  (gen_random_uuid(), 'Administrator', 'System Administrator with full access across all platform sections'),
  (gen_random_uuid(), 'Operator', 'Operational user with view permissions on telemetry and control tower sections')
ON CONFLICT (name) DO NOTHING;

-- 3. Link Administrator role to all section permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'Administrator'
  AND p.code LIKE 'section:%'
ON CONFLICT DO NOTHING;

-- 4. Link Operator role to operational view permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'Operator'
  AND p.code LIKE 'section:%:view'
  AND p.code NOT IN ('section:settings:view', 'section:user_management:view')
ON CONFLICT DO NOTHING;

-- 5. Ensure all users have user_preferences row
INSERT INTO user_preferences (user_id, theme, default_dashboard, timezone, rows_per_page, collapsed_sidebar, ui_settings, updated_at)
SELECT u.id, 'dark', 'operational_overview', 'UTC', 20, false, '{}'::jsonb, now()
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM user_preferences up WHERE up.user_id = u.id
);

-- 6. Backfill section_permissions in user_preferences
UPDATE user_preferences up
SET ui_settings = jsonb_set(
    COALESCE(up.ui_settings, '{}'::jsonb),
    '{section_permissions}',
    '{"platform_home":"edit","site_dashboard":"edit","overall_dashboard":"edit","dispatch_analysis":"edit","dispatch_optimization":"edit","operational_intelligence":"edit","predictive_intelligence":"edit","control_tower_actions":"edit","alerts":"edit","reports":"edit","erp_import":"edit","erp_explorer":"edit","settings":"edit","user_management":"edit"}'::jsonb,
    true
)
FROM users u
WHERE up.user_id = u.id
  AND u.is_superuser = true;

UPDATE user_preferences up
SET ui_settings = jsonb_set(
    COALESCE(up.ui_settings, '{}'::jsonb),
    '{section_permissions}',
    '{"platform_home":"view","site_dashboard":"view","overall_dashboard":"view","dispatch_analysis":"view","dispatch_optimization":"view","operational_intelligence":"view","predictive_intelligence":"view","control_tower_actions":"view","alerts":"view","reports":"view","erp_import":"none","erp_explorer":"view","settings":"none","user_management":"none"}'::jsonb,
    true
)
FROM users u
WHERE up.user_id = u.id
  AND u.is_superuser = false
  AND (up.ui_settings->'section_permissions' IS NULL);

-- 7. Bind roles in user_roles
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
CROSS JOIN roles r
WHERE u.is_superuser = true
  AND r.name = 'Administrator'
ON CONFLICT DO NOTHING;

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

-- 8. Stamp alembic_version so future migrations stay aligned
UPDATE alembic_version
SET version_num = 'add_section_permissions_matrix'
WHERE version_num = 'add_google_api_usage_logs';
SQL

echo -e "\n[3] Verification of Remote Linode Database State:"
sudo -u postgres psql -d fleet_control_tower_db -c "
SELECT version_num as current_alembic_version FROM alembic_version;
SELECT count(*) as total_permissions FROM permissions;
SELECT name as role_name, count(rp.permission_id) as permissions_assigned 
FROM roles r 
LEFT JOIN role_permissions rp ON rp.role_id = r.id 
GROUP BY r.name;
SELECT u.username, u.is_superuser, up.ui_settings->'section_permissions'->>'platform_home' as platform_home_perm, up.ui_settings->'section_permissions'->>'erp_import' as erp_import_perm, up.ui_settings->'section_permissions'->>'settings' as settings_perm
FROM users u 
JOIN user_preferences up ON up.user_id = u.id;
"

echo -e "\n[SUCCESS] Remote Linode Database Migration & Seeding Verified!"
REMOTESCRIPT
