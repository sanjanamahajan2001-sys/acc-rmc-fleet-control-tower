"""
Phase 2 Database Migration & Seeding Script: Granular Section Permissions Matrix
Idempotent script to:
1. Seed the 28 atomic section permissions (section:<key>:view, section:<key>:edit).
2. Seed canonical roles (Administrator, Operator) and link corresponding permissions in role_permissions.
3. Backfill/initialize existing users' user_preferences with section_permissions:
   - Superusers: Full edit on all 14 sections.
   - Non-superusers: Safe operator default (view operational sections, none for settings/user_management).
4. Ensure existing users have appropriate role bindings.
"""

import asyncio
import os
import sys
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.modules.auth.models import User, Role, Permission, UserPreference, role_permissions, user_roles
from app.modules.auth.schemas import (
    PLATFORM_SECTIONS,
    PLATFORM_SECTION_LABELS,
    get_full_admin_permissions,
    get_default_operator_permissions,
)


async def run_phase2_seeding(db_uri: str = None) -> None:
    uri = db_uri or settings.ASYNC_DATABASE_URI
    print(f"Connecting to database: {uri.split('@')[-1] if '@' in uri else uri}")

    engine = create_async_engine(uri, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_maker() as session:
        # -------------------------------------------------------------
        # 1. Seed 28 Atomic Permissions
        # -------------------------------------------------------------
        print("\n--- [Step 1] Seeding 28 Atomic Permissions ---")
        existing_perms_stmt = select(Permission)
        existing_perms = {p.code: p for p in (await session.execute(existing_perms_stmt)).scalars().all()}

        created_perms = 0
        all_perms: dict[str, Permission] = dict(existing_perms)

        for sec_key in PLATFORM_SECTIONS:
            sec_label = PLATFORM_SECTION_LABELS.get(sec_key, sec_key)

            # View permission
            view_code = f"section:{sec_key}:view"
            if view_code not in all_perms:
                p_view = Permission(
                    id=uuid.uuid4(),
                    code=view_code,
                    description=f"View access to {sec_label}",
                )
                session.add(p_view)
                all_perms[view_code] = p_view
                created_perms += 1

            # Edit permission
            edit_code = f"section:{sec_key}:edit"
            if edit_code not in all_perms:
                p_edit = Permission(
                    id=uuid.uuid4(),
                    code=edit_code,
                    description=f"Edit and execute access in {sec_label}",
                )
                session.add(p_edit)
                all_perms[edit_code] = p_edit
                created_perms += 1

        await session.commit()
        print(f"Permissions: {created_perms} new created, {len(all_perms)} total active.")

        # -------------------------------------------------------------
        # 2. Seed Roles (Administrator, Operator)
        # -------------------------------------------------------------
        print("\n--- [Step 2] Seeding Roles & Role Permissions ---")
        role_stmt = select(Role)
        existing_roles = {r.name: r for r in (await session.execute(role_stmt)).scalars().all()}

        admin_role = existing_roles.get("Administrator")
        if not admin_role:
            admin_role = Role(
                id=uuid.uuid4(),
                name="Administrator",
                description="System Administrator with full access across all platform sections",
            )
            session.add(admin_role)
            await session.commit()
            print("Created role: Administrator")
        else:
            print("Found existing role: Administrator")

        operator_role = existing_roles.get("Operator")
        if not operator_role:
            operator_role = Role(
                id=uuid.uuid4(),
                name="Operator",
                description="Operational user with view permissions on telemetry and control tower sections",
            )
            session.add(operator_role)
            await session.commit()
            print("Created role: Operator")
        else:
            print("Found existing role: Operator")

        # Map all permissions to Administrator
        admin_links_stmt = select(role_permissions.c.permission_id).where(role_permissions.c.role_id == admin_role.id)
        current_admin_perm_ids = set((await session.execute(admin_links_stmt)).scalars().all())

        new_admin_links = 0
        for p in all_perms.values():
            if p.id not in current_admin_perm_ids:
                await session.execute(
                    role_permissions.insert().values(role_id=admin_role.id, permission_id=p.id)
                )
                new_admin_links += 1

        # Map operational view permissions to Operator
        op_links_stmt = select(role_permissions.c.permission_id).where(role_permissions.c.role_id == operator_role.id)
        current_op_perm_ids = set((await session.execute(op_links_stmt)).scalars().all())

        op_defaults = get_default_operator_permissions()
        new_op_links = 0
        for sec_key, level in op_defaults.items():
            if level in ("view", "edit"):
                perm_code = f"section:{sec_key}:view"
                perm = all_perms.get(perm_code)
                if perm and perm.id not in current_op_perm_ids:
                    await session.execute(
                        role_permissions.insert().values(role_id=operator_role.id, permission_id=perm.id)
                    )
                    new_op_links += 1

        await session.commit()
        print(f"Role Permissions: Linked {new_admin_links} to Administrator, {new_op_links} to Operator.")

        # -------------------------------------------------------------
        # 3. Backfill & Initialize User Preferences
        # -------------------------------------------------------------
        print("\n--- [Step 3] Backfilling User Preferences with Section Permissions ---")
        users_stmt = select(User)
        all_users = (await session.execute(users_stmt)).scalars().all()

        updated_users = 0
        for user in all_users:
            pref_stmt = select(UserPreference).where(UserPreference.user_id == user.id)
            pref = (await session.execute(pref_stmt)).scalars().first()

            if not pref:
                pref = UserPreference(user_id=user.id, ui_settings={})
                session.add(pref)

            current_ui_settings = dict(pref.ui_settings or {})
            existing_matrix = current_ui_settings.get("section_permissions")

            if user.is_superuser:
                target_matrix = get_full_admin_permissions()
            else:
                target_matrix = existing_matrix if existing_matrix else get_default_operator_permissions()

            if existing_matrix != target_matrix:
                current_ui_settings["section_permissions"] = target_matrix
                pref.ui_settings = current_ui_settings
                updated_users += 1
                print(f"Updated section_permissions for user: '{user.username}' (superuser={user.is_superuser})")

            # Check user role mapping
            user_roles_stmt = select(user_roles.c.role_id).where(user_roles.c.user_id == user.id)
            user_role_ids = set((await session.execute(user_roles_stmt)).scalars().all())

            if user.is_superuser and admin_role.id not in user_role_ids:
                await session.execute(user_roles.insert().values(user_id=user.id, role_id=admin_role.id))
                print(f"Bound 'Administrator' role to user '{user.username}'")
            elif not user.is_superuser and not user_role_ids:
                await session.execute(user_roles.insert().values(user_id=user.id, role_id=operator_role.id))
                print(f"Bound default 'Operator' role to user '{user.username}'")

        await session.commit()
        print(f"User Preferences: {updated_users} user(s) updated, {len(all_users)} user(s) verified.")

    await engine.dispose()
    print("\n[SUCCESS] Phase 2 Seeding completed successfully.")


if __name__ == "__main__":
    target_uri = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(run_phase2_seeding(target_uri))
